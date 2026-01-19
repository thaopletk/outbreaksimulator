import sys
import os
import random
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from shapely.geometry import Point
import csv
import math
import pickle
import matplotlib.pyplot as plt
import simulator.spatial_setup as spatial_setup
import simulator.management as management
import simulator.premises as premises
import simulator.SEIR as SEIR
import simulator.output as output
import simulator.fixed_spatial_setup as fixed_spatial_setup
import simulator.animal_movement as animal_movement
from iteround import saferound
from shapely.ops import transform, unary_union
from simulator.spatial_functions import quick_distance_haversine
import time
from FMD_modelling.class_definitions import Animal


def seed_HPAI_infection(
    xrange_bounds,
    yrange_bounds,
    properties,
    time=0,
    xlims=[],
    ylims=[],
    folder_path="",
    unique_output="",
    latent_period=7,
    disease_parameters=None,
):
    """Seeds an infection at a property within the bounds specified"""
    seed_property = 0  # default

    viable_properties = []
    for i, property in enumerate(properties):
        coords = property.coordinates
        if (
            coords[0] <= xrange_bounds[1]
            and coords[0] >= xrange_bounds[0]
            and coords[1] <= yrange_bounds[1]
            and coords[1] >= yrange_bounds[0]
        ) and property.type not in ["egg processing", "abbatoir"]:
            viable_properties.append(i)

    # seed this property
    # randomly pick a property to see:
    seed_property = random.choice(viable_properties)

    p = properties[seed_property]
    # TODO technically, to encapsulate this better, there should a function that allows you to infect a specific animal(s), and that will then update infection_status, prop_infections, cumulative_infections, and exposure_date, and anything else that may need to be updated
    p.infection_status = 1
    if latent_period != None:
        p.exposure_date = premises.convert_time_to_date(time - latent_period)
    else:  # the version with multiple animals
        latent_period = disease_parameters[p.animal_type]["latent_period"]
        p.exposure_date = premises.convert_time_to_date(time - latent_period)

    num_infected = 10
    # TODO: need to update some status/check the status update;
    p.init_animals(None)
    infected_row = np.random.randint(0, len(p.chickens))  # this picks a random age
    for seed_animal in range(num_infected):
        p.chickens[infected_row][3][seed_animal].status = "infected"

    p.prop_infectious = num_infected / p.size
    p.cumulative_infections = num_infected

    output.plot_map(
        properties,
        time,
        xlims=xlims,
        ylims=ylims,
        folder_path=folder_path,
        real_situation=True,
        controlzone=None,
        infectionpoly=None,
        contacts_for_plotting={},  # contacts_for_plotting,  # hiding the contacts for plotting, to make things look clearer,,,, TODO in the real situation, these should be the actual movements, or something
    )

    fixed_spatial_setup.save_chicken_property_csv(properties, time, folder_path, unique_output)

    return properties, seed_property


def advance_chicken_egg_ages(properties):
    """increases the age of all the chickens and eggs by one day"""
    for facility in properties:
        for i in range(len(facility.chickens)):
            facility.chickens[i][2] += 1  # the third index is the age, by day
        for i in range(len(facility.eggs)):
            facility.eggs[i][1] += 1  # the second index is the age, by day
        for i in range(len(facility.eggs_fertilised)):
            facility.eggs_fertilised[i][1] += 1  # the second index is the age, by day

        # check if eggs are > 21 days, in which case they become chickens!
        rows_with_hatched_eggs = []
        for i in range(facility.eggs_fertilised):
            if facility.eggs_fertilised[i][1] > 21:
                rows_with_hatched_eggs.append(i)
        for i in rows_with_hatched_eggs:
            hatched_row = facility.eggs_fertilised.pop(i)
            shed = 1  # should do this properly...
            if facility.check_if_chicken_objects() == False:

                facility.chickens.append([hatched_row[0], shed, 0])  # adding new chickens of age zero
            else:
                chicken_animal_objs = [Animal(None) for _ in range(hatched_row[0])]
                facility.chickens.append(
                    [hatched_row[0], shed, 0, chicken_animal_objs]
                )  # adding new chickens of age zero


def egg_production(properties):
    """implements production of eggs..."""
    for facility in properties:
        if "layers" in facility.type:
            total_laying_chickens = 0
            for row in facility.chickens:
                if row[2] > 20 * 7 and row[2] < 78 * 7:  # i.e., if age is greater than 20 weeks
                    total_laying_chickens += row[0]  # the number of chickens
            facility.eggs.append(
                [int(total_laying_chickens / 2), 0]
            )  # assume half of the chickens lay eggs; age of eggs is zero
        elif facility.type == "meat growing-farm":
            pass  # no egg production
        elif facility.type == "pullets farm":
            pass  # no egg production
        elif facility.type == "egg processing":
            pass  # no egg production
        elif facility.type == "abbatoir":
            pass  # no egg production
        elif facility.type == "hatchery":
            total_laying_chickens = 0
            for row in facility.chickens:
                if row[2] > 20 * 7 and row[2] < 78 * 7:  # i.e., if age is greater than 20 weeks and less than 78
                    total_laying_chickens += row[0]  # the number of chickens
            facility.eggs_fertilised.append(
                [int(total_laying_chickens / 2), 0]
            )  # assume half of the chickens lay eggs; age of eggs is zero
            # NOTE I think the eggs should be hatched in pulses (.g. every 14 days) but for now, it'll be like this....
        else:
            raise ValueError(f"egg_production: property type not expected: {facility.type}")


movement_record_header = [
    "day",
    "date",
    "from",
    "to",
    "entity",
    "quantity",
    "facility_type_1",
    "facility_type_2",
    "report",
]


def create_movement_records_df():

    return pd.DataFrame(columns=movement_record_header)


def animal_movement(
    properties,
    day,
    controlzone,
    reduced_movement_zone=None,
    movement_reduction_factor=0.2,
    all_movement_reduction_factor=1.0,
):

    date = premises.convert_time_to_date(day)

    # rows of day, converted date, moving from property index, to property index, WHAT was moved (chickens or eggs), number of animals/eggs moved, a narrative report (locations, number of animals moved),
    movement_record = []

    indices_that_can_move = []
    for premise_index in range(len(properties)):
        if not properties[premise_index].culled_status:
            if controlzone == None or not properties[premise_index].polygon.intersects(controlzone):
                if reduced_movement_zone == None:
                    if random.uniform(0, 1) < all_movement_reduction_factor:
                        indices_that_can_move.append(premise_index)
                else:
                    if properties[premise_index].polygon.intersects(reduced_movement_zone):
                        if random.uniform(0, 1) < movement_reduction_factor:
                            indices_that_can_move.append(premise_index)
                    else:
                        if random.uniform(0, 1) < all_movement_reduction_factor:
                            indices_that_can_move.append(premise_index)

    # unlike the LSD case, chickens and eggs shouldn't be able to move twice in day, due to their more directional, conditional movement in this version...

    for premise_index in indices_that_can_move:
        facility = properties[premise_index]
        allowed_movement_neighbours, total_num_allowed = facility.calculate_allowed_movement_neighbours(
            indices_that_can_move
        )

        if (
            "layers" in facility.type or facility.type == "meat growing-farm" or facility.type == "pullets farm"
        ):  # these have the same procedure for chickens
            # movements possible: eggs to egg processing; old chickens to abbatoir
            for allowed_type in allowed_movement_neighbours:
                num_properties_to_move_to = np.random.randint(1, len(allowed_movement_neighbours[allowed_type]) + 1)

                entity_to_move = facility.allowed_movement_details[allowed_type]["entity"]

                if entity_to_move == "chicken":
                    num_chickens_to_move = 0
                    row_indices_to_move = []
                    chickens_to_move = []
                    for i in range(len(facility.chickens)):
                        row = facility.chickens[i]
                        chicken_age = row[2]
                        if chicken_age > facility.allowed_movement_details[allowed_type]["age"]:
                            num_chickens_to_move += row[0]
                            row_indices_to_move.append(i)

                    for i in row_indices_to_move:
                        chickens_to_move.append(facility.chickens.pop(i))

                    chickens_per_property_to_move = saferound(
                        [num_chickens_to_move / num_properties_to_move_to] * num_properties_to_move_to,
                        places=0,
                    )
                    chickens_per_property_to_move = [int(x) for x in chickens_per_property_to_move]

                    for moving_to_premise_index, number_animals in zip(
                        allowed_movement_neighbours[allowed_type], chickens_per_property_to_move
                    ):
                        new_facility = properties[moving_to_premise_index]
                        animals_moved = 0

                        # uh oh, how do I deal with sheds.... - just move into shed #1 for now? / do abbatoir have sheds?
                        shed = 1
                        while animals_moved < number_animals:
                            animals_left_to_move = number_animals - animals_moved

                            chickens_to_move_first_row = chickens_to_move[0]
                            if (
                                chickens_to_move_first_row[0] > animals_left_to_move
                            ):  #  if the number of chickens in the first row is more than the number of animals to move, then we only need to move a subset
                                if facility.check_if_chicken_objects():
                                    if new_facility.check_if_chicken_objects() == False:
                                        new_facility.init_animals()
                                    # now both have chicken objects
                                    new_row = [
                                        animals_left_to_move,
                                        shed,
                                        chickens_to_move_first_row[2],
                                        chickens_to_move_first_row[3][:animals_left_to_move],
                                    ]
                                    old_row = [
                                        chickens_to_move_first_row[0] - animals_left_to_move,
                                        chickens_to_move_first_row[1],
                                        chickens_to_move_first_row[2],
                                        chickens_to_move_first_row[3][animals_left_to_move:],
                                    ]
                                elif (
                                    facility.check_if_chicken_objects() == False
                                    and new_facility.check_if_chicken_objects() == False
                                ):
                                    new_row = [animals_left_to_move, shed, chickens_to_move_first_row[2]]
                                    old_row = [
                                        chickens_to_move_first_row[0] - animals_left_to_move,
                                        chickens_to_move_first_row[1],
                                        chickens_to_move_first_row[2],
                                    ]

                                elif (
                                    facility.check_if_chicken_objects() == False
                                    and new_facility.check_if_chicken_objects() == True
                                ):
                                    # need to convert new chickens into chicken objects before passing them on
                                    new_row = [animals_left_to_move, shed, chickens_to_move_first_row[2]]
                                    old_row = [
                                        chickens_to_move_first_row[0] - animals_left_to_move,
                                        chickens_to_move_first_row[1],
                                        chickens_to_move_first_row[2],
                                    ]
                                    chicken_animal_objs = [Animal(None) for _ in range(animals_left_to_move)]
                                    new_row.append(chicken_animal_objs)

                                else:
                                    raise ValueError("Eh?")

                                chickens_to_move[0] = old_row
                                new_facility.chickens.append(new_row)

                                animals_moved += animals_left_to_move
                            else:

                                # this means we pop the entire first row
                                moving_row = chickens_to_move.pop(0)
                                if facility.check_if_chicken_objects():
                                    if new_facility.check_if_chicken_objects() == False:
                                        new_facility.init_animals()
                                    # now both have chicken objects
                                    new_row = [moving_row[0], shed, moving_row[2], moving_row[3]]
                                elif (
                                    facility.check_if_chicken_objects() == False
                                    and new_facility.check_if_chicken_objects() == False
                                ):
                                    new_row = [moving_row[0], shed, moving_row[2]]

                                elif (
                                    facility.check_if_chicken_objects() == False
                                    and new_facility.check_if_chicken_objects() == True
                                ):
                                    # need to convert new chickens into chicken objects before passing them on
                                    new_row = [moving_row[0], shed, moving_row[2]]

                                    chicken_animal_objs = [Animal(None) for _ in range(animals_left_to_move)]
                                    new_row.append(chicken_animal_objs)

                                else:
                                    raise ValueError("Eh?")

                                new_facility.chickens.append(new_row)
                                animals_moved += moving_row[0]
                        if animals_moved != number_animals:
                            raise ValueError("The number of animals moved does not match the target")

                        row = [
                            day,
                            f"{date}",
                            premise_index,
                            moving_to_premise_index,
                            entity_to_move,
                            number_animals,
                            facility.type,
                            new_facility.type,
                            f"DAY {date} - moved {number_animals} {entity_to_move}(s) from {facility.type} ID {facility.id} ({facility.state}) to {new_facility.type} ID {new_facility.type.id} ({new_facility.type.state})",
                        ]

                        if len(row) != len(movement_record_header):
                            raise ValueError("The length of movement record is not the same as the movement header")
                            # added in case I decide to change the information recorded again

                        movement_record.append(row)

                elif facility.allowed_movement_details[allowed_type]["entity"] == "egg":  # for layers

                    num_eggs_to_move = 0
                    row_indices_to_move = []
                    egg_rows_to_move = []
                    for i in range(len(facility.eggs)):
                        row = facility.eggs[i]
                        egg_age = row[1]
                        if egg_age > facility.allowed_movement_details[allowed_type]["age"]:
                            num_eggs_to_move += row[0]
                            row_indices_to_move.append(i)

                    for i in row_indices_to_move:
                        egg_rows_to_move.append(facility.eggs.pop(i))

                    eggs_per_property_to_move = saferound(
                        [num_eggs_to_move / num_properties_to_move_to] * num_properties_to_move_to,
                        places=0,
                    )
                    eggs_per_property_to_move = [int(x) for x in eggs_per_property_to_move]

                    # divide this by the number of properties to move to (should be egg processing, should only have one...)
                    # move the eggs to those properties, and remove from current facility

                    for moving_to_premise_index, number_eggs in zip(
                        allowed_movement_neighbours[allowed_type], eggs_per_property_to_move
                    ):
                        new_facility = properties[moving_to_premise_index]
                        eggs_moved = 0

                        while eggs_moved < number_eggs:
                            eggs_left_to_move = number_eggs - eggs_moved

                            eggs_to_move_first_row = egg_rows_to_move[0]
                            if (
                                eggs_to_move_first_row[0] > eggs_left_to_move
                            ):  #  if the number of eggs in the first row is more than the number of eggs to move, then we only need to move a subset
                                new_row = [eggs_left_to_move, eggs_to_move_first_row[1]]
                                old_row = [eggs_to_move_first_row[0] - eggs_left_to_move, eggs_to_move_first_row[1]]

                                egg_rows_to_move[0] = old_row
                                new_facility.eggs.append(new_row)

                                eggs_moved += eggs_left_to_move
                            else:

                                # this means we pop the entire first row
                                moving_row = egg_rows_to_move.pop(0)

                                new_facility.chickens.append(moving_row)
                                eggs_moved += moving_row[0]

                        if eggs_moved != number_eggs:
                            raise ValueError("The number of eggs moved does not match the target")

                        row = [
                            day,
                            f"{date}",
                            premise_index,
                            moving_to_premise_index,
                            entity_to_move,
                            number_animals,
                            facility.type,
                            new_facility.type,
                            f"DAY {date} - moved {number_animals} {entity_to_move}(s) from {facility.type} ID {facility.id} ({facility.state}) to {new_facility.type} ID {new_facility.type.id} ({new_facility.type.state})",
                        ]

                        if len(row) != len(movement_record_header):
                            raise ValueError("The length of movement record is not the same as the movement header")
                            # added in case I decide to change the information recorded again

                        movement_record.append(row)

        elif facility.type == "egg processing":
            # movements possible - eggs removed from system, i.e., sent to distribution
            total_eggs_being_moved = 0
            for i in range(len(facility.eggs)):
                row = facility.eggs[i]
                total_eggs_being_moved += row[0]
            facility.eggs = []  # reset to zero

            # create the movement record
            row = [
                day,
                f"{date}",
                premise_index,
                -1,
                entity_to_move,
                total_eggs_being_moved,
                facility.type,
                "egg distributor",
                f"DAY {date} - moved {number_animals} {entity_to_move}(s) from {facility.type} ID {facility.id} ({facility.state}) to egg distributor",
            ]

            if len(row) != len(movement_record_header):
                raise ValueError("The length of movement record is not the same as the movement header")
                # added in case I decide to change the information recorded again

            movement_record.append(row)

        elif facility.type == "hatchery":
            # TODO: movements possible - baby chicks to layers, meat growing, pullets; old chickens to abbatoir
            # need to somehow separate the baby chicks from the old laying chickens...
            # move the older ones first...?
            for allowed_type in ["abbatoir", "pullets farm", "meat growing-farm"]:  # forcing this priority ordering
                if allowed_type in allowed_movement_neighbours:
                    pass
                else:
                    continue
                num_properties_to_move_to = np.random.randint(1, len(allowed_movement_neighbours[allowed_type]) + 1)

                entity_to_move = facility.allowed_movement_details[allowed_type]["entity"]
                num_chickens_to_move = 0
                row_indices_to_move = []
                chickens_to_move = []
                for i in range(len(facility.chickens)):
                    row = facility.chickens[i]
                    chicken_age = row[2]
                    if chicken_age > facility.allowed_movement_details[allowed_type]["age"]:
                        num_chickens_to_move += row[0]
                        row_indices_to_move.append(i)

                for i in row_indices_to_move:
                    chickens_to_move.append(facility.chickens.pop(i))

                chickens_per_property_to_move = saferound(
                    [num_chickens_to_move / num_properties_to_move_to] * num_properties_to_move_to,
                    places=0,
                )
                chickens_per_property_to_move = [int(x) for x in chickens_per_property_to_move]

                for moving_to_premise_index, number_animals in zip(
                    allowed_movement_neighbours[allowed_type], chickens_per_property_to_move
                ):
                    new_facility = properties[moving_to_premise_index]
                    animals_moved = 0

                    # uh oh, how do I deal with sheds.... - just move into shed #1 for now? / do abbatoir have sheds?
                    shed = 1
                    while animals_moved < number_animals:
                        animals_left_to_move = number_animals - animals_moved

                        chickens_to_move_first_row = chickens_to_move[0]
                        if (
                            chickens_to_move_first_row[0] > animals_left_to_move
                        ):  #  if the number of chickens in the first row is more than the number of animals to move, then we only need to move a subset
                            if facility.check_if_chicken_objects():
                                if new_facility.check_if_chicken_objects() == False:
                                    new_facility.init_animals()
                                # now both have chicken objects
                                new_row = [
                                    animals_left_to_move,
                                    shed,
                                    chickens_to_move_first_row[2],
                                    chickens_to_move_first_row[3][:animals_left_to_move],
                                ]
                                old_row = [
                                    chickens_to_move_first_row[0] - animals_left_to_move,
                                    chickens_to_move_first_row[1],
                                    chickens_to_move_first_row[2],
                                    chickens_to_move_first_row[3][animals_left_to_move:],
                                ]
                            elif (
                                facility.check_if_chicken_objects() == False
                                and new_facility.check_if_chicken_objects() == False
                            ):
                                new_row = [animals_left_to_move, shed, chickens_to_move_first_row[2]]
                                old_row = [
                                    chickens_to_move_first_row[0] - animals_left_to_move,
                                    chickens_to_move_first_row[1],
                                    chickens_to_move_first_row[2],
                                ]

                            elif (
                                facility.check_if_chicken_objects() == False
                                and new_facility.check_if_chicken_objects() == True
                            ):
                                # need to convert new chickens into chicken objects before passing them on
                                new_row = [animals_left_to_move, shed, chickens_to_move_first_row[2]]
                                old_row = [
                                    chickens_to_move_first_row[0] - animals_left_to_move,
                                    chickens_to_move_first_row[1],
                                    chickens_to_move_first_row[2],
                                ]
                                chicken_animal_objs = [Animal(None) for _ in range(animals_left_to_move)]
                                new_row.append(chicken_animal_objs)

                            else:
                                raise ValueError("Eh?")

                            chickens_to_move[0] = old_row
                            new_facility.chickens.append(new_row)

                            animals_moved += animals_left_to_move
                        else:

                            # this means we pop the entire first row
                            moving_row = chickens_to_move.pop(0)
                            if facility.check_if_chicken_objects():
                                if new_facility.check_if_chicken_objects() == False:
                                    new_facility.init_animals()
                                # now both have chicken objects
                                new_row = [moving_row[0], shed, moving_row[2], moving_row[3]]
                            elif (
                                facility.check_if_chicken_objects() == False
                                and new_facility.check_if_chicken_objects() == False
                            ):
                                new_row = [moving_row[0], shed, moving_row[2]]

                            elif (
                                facility.check_if_chicken_objects() == False
                                and new_facility.check_if_chicken_objects() == True
                            ):
                                # need to convert new chickens into chicken objects before passing them on
                                new_row = [moving_row[0], shed, moving_row[2]]

                                chicken_animal_objs = [Animal(None) for _ in range(animals_left_to_move)]
                                new_row.append(chicken_animal_objs)

                            else:
                                raise ValueError("Eh?")

                            new_facility.chickens.append(new_row)
                            animals_moved += moving_row[0]
                    if animals_moved != number_animals:
                        raise ValueError("The number of animals moved does not match the target")

                    row = [
                        day,
                        f"{date}",
                        premise_index,
                        moving_to_premise_index,
                        entity_to_move,
                        number_animals,
                        facility.type,
                        new_facility.type,
                        f"DAY {date} - moved {number_animals} {entity_to_move}(s) from {facility.type} ID {facility.id} ({facility.state}) to {new_facility.type} ID {new_facility.type.id} ({new_facility.type.state})",
                    ]

                    if len(row) != len(movement_record_header):
                        raise ValueError("The length of movement record is not the same as the movement header")
                        # added in case I decide to change the information recorded again

                    movement_record.append(row)

        elif facility.type == "abbatoir":
            # movements possible - chickens removed from system, i.e., sent to distribution
            # for now, just remove ALL chickens that are available
            total_chickens_being_slaughtered = 0
            for i in range(len(facility.chickens)):
                row = facility.chickens[i]
                total_chickens_being_slaughtered += row[0]
            facility.chickens = []  # reset to zero

            # create the movement record
            row = [
                day,
                f"{date}",
                premise_index,
                -2,
                entity_to_move,
                total_chickens_being_slaughtered,
                facility.type,
                "chicken meat distributor",
                f"DAY {date} - moved {number_animals} {entity_to_move}(s) from {facility.type} ID {facility.id} ({facility.state}) to chicken meat distributor",
            ]

            if len(row) != len(movement_record_header):
                raise ValueError("The length of movement record is not the same as the movement header")
                # added in case I decide to change the information recorded again

            movement_record.append(row)
        else:
            raise ValueError(f"animal_movement: property type not expected: {facility.type}")
