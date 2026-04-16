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
from FMD_modelling_code.class_definitions import Animal


def seed_HPAI_infection(
    xrange_bounds,
    yrange_bounds,
    properties,
    int_time=0,
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
            (coords[0] <= xrange_bounds[1] and coords[0] >= xrange_bounds[0] and coords[1] <= yrange_bounds[1] and coords[1] >= yrange_bounds[0])
            and property.type
            not in ["egg processing", "abbatoir", "hatchery", "backyard", "layers free-range", "layers caged", "layers barn", "layers"]
            and property.get_num_chickens() > 700
            and property.get_num_chickens() < 50000
        ):
            viable_properties.append(i)

    # seed this property
    # randomly pick a property to see:
    seed_property = random.choice(viable_properties)

    p = properties[seed_property]
    # TODO technically, to encapsulate this better, there should a function that allows you to infect a specific animal(s), and that will then update infection_status, prop_infections, cumulative_infections, and exposure_date, and anything else that may need to be updated
    p.infection_status = 1
    if latent_period != None:
        p.exposure_date = premises.convert_time_to_date(int_time - latent_period)
    else:  # the version with multiple animals
        latent_period = disease_parameters[p.animal_type]["latent_period"]
        p.exposure_date = premises.convert_time_to_date(int_time - latent_period)

    num_infected = 10
    p.init_animals(None)
    infected_shed = np.random.randint(1, p.num_sheds + 1)
    for seed_animal in range(num_infected):
        p.sheds[infected_shed]["chickens"][0]["objs"][seed_animal].status = "infected"  # picks chickens from the first row

    p.prop_infectious = num_infected / p.get_num_chickens()
    p.cumulative_infections = num_infected

    output.plot_map(
        properties,
        int_time,
        xlims=xlims,
        ylims=ylims,
        folder_path=folder_path,
        real_situation=True,
        controlzone=None,
        infectionpoly=None,
        contacts_for_plotting={},  # contacts_for_plotting,  # hiding the contacts for plotting, to make things look clearer,,,, TODO in the real situation, these should be the actual movements, or something
    )

    fixed_spatial_setup.save_chicken_property_csv(properties, int_time, folder_path, unique_output)

    return properties, seed_property


def advance_chicken_egg_ages(properties):
    """increases the age of all the chickens and [fertilised] eggs by one day"""
    for facility in properties:
        for shed_i, shed_info in facility.sheds.items():
            if "chickens" in shed_info:
                for i in range(len(facility.sheds[shed_i]["chickens"])):
                    facility.sheds[shed_i]["chickens"][i]["age"] += 1
            if "eggs" in shed_info:  # hatcheries only
                eggs_rows_to_hatch = []
                for i in range(len(facility.sheds[shed_i]["eggs"])):
                    facility.sheds[shed_i]["eggs"][i]["age"] += 1
                    if facility.sheds[shed_i]["eggs"][i]["age"] > 21:
                        # hatch the eggs!
                        eggs_rows_to_hatch.append(i)
                for i in reversed(eggs_rows_to_hatch):
                    hatched_row = facility.sheds[shed_i]["eggs"].pop(i)
                    if facility.check_if_chicken_objects() == False:
                        baby_chicks = {"n": hatched_row["n"], "age": 0}
                    else:
                        baby_chicks = {
                            "n": hatched_row["n"],
                            "age": 0,
                            "objs": [Animal(None) for _ in range(hatched_row["n"])],
                        }

                    if "chickens" in facility.sheds[shed_i]:
                        facility.sheds[shed_i]["chickens"].append(baby_chicks)
                    else:
                        facility.sheds[shed_i]["chickens"] = [baby_chicks]


def finish_cleaning_sheds(properties, int_time):
    for facility in properties:
        for shed_i, shed_info in facility.sheds.items():
            if shed_info["cleaning"] == True:
                if shed_info["cleaning_completion"] >= int_time:
                    shed_info["cleaning"] = False  # cleaning complete


def egg_production(properties):
    """implements production of eggs..."""
    for facility in properties:
        if "layers" in facility.type or "Egg production" in facility.type or "Mixed" in facility.type:
            total_laying_chickens = facility.get_num_laying_chickens()
            facility.eggs += max(1, int(total_laying_chickens / 2))  # assumption... TODO fix this
        elif facility.type == "broiler farm" or "Meat production" in facility.type:
            pass  # no egg production
        elif facility.type == "pullet farm":
            pass  # no egg production
        elif facility.type == "egg processing":
            pass  # no egg production
        elif facility.type == "abbatoir":
            pass  # no egg production
        elif facility.type == "hatchery":
            pass  # no egg production
        elif facility.type == "breeder":
            total_laying_chickens = facility.get_num_laying_chickens()
            facility.eggs += max(1, int(total_laying_chickens / 4))  # assumption... TODO fix this
        elif facility.type == "backyard" or "Other" in facility.type:
            if random.uniform(0, 1) < 0.5:
                total_laying_chickens = facility.get_num_laying_chickens()
                facility.eggs += max(1, int(total_laying_chickens / 2))  # assumption... TODO fix this
            else:
                facility.eggs = 0  # e.g. pretending that they just ate all the eggs or otherwise gave them away ....
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


def initiate_cleaning(properties, index, shed_i, time):
    # NOTE: only call if chickens have been just moved

    facility = properties[index]
    shed_info = facility.sheds[shed_i]
    # check if the shed is now empty
    # if so, initiate cleaning
    if shed_info["chickens"] == []:
        shed_info["cleaning"] = True
        shed_info["cleaning_completion"] = time + 7  # at least a week of cleaning


def remove_chickens_from_property_ready_for_movement(properties, start_index, int_time, capacity_in_unrestricted_zones=None):
    start_facility = properties[start_index]
    chickens_to_move = []
    if capacity_in_unrestricted_zones == None:  # if we want to move everything that can be moved
        if "chickens" in start_facility.allowed_movement_details:
            for shed_i, shed_info in start_facility.sheds.items():
                shed_has_had_chickens_removed = False
                if "chickens" in shed_info:
                    i = 0
                    while i < len(shed_info["chickens"]):
                        chicken_row = shed_info["chickens"][i]
                        if chicken_row["age"] >= start_facility.allowed_movement_details["chickens"]["age"]:
                            chickens_to_move.append(chicken_row)
                            shed_has_had_chickens_removed = True
                            del shed_info["chickens"][i]
                        else:
                            i += 1

                    if shed_has_had_chickens_removed:
                        initiate_cleaning(properties, start_index, shed_i, int_time)
    else:  # we can only move some, not all
        moved_so_far = 0
        if "chickens" in start_facility.allowed_movement_details:
            for shed_i, shed_info in start_facility.sheds.items():
                shed_has_had_chickens_removed = False
                if "chickens" in shed_info:
                    for chicken_row in shed_info["chickens"]:
                        if chicken_row["age"] >= start_facility.allowed_movement_details["chickens"]["age"]:
                            if moved_so_far + chicken_row["n"] <= capacity_in_unrestricted_zones:  # i.e., we can move everything
                                chickens_to_move.append(chicken_row)
                                shed_has_had_chickens_removed = True
                                moved_so_far += chicken_row["n"]
                            else:
                                actually_only_moving = capacity_in_unrestricted_zones - moved_so_far
                                if actually_only_moving > 0:
                                    moved_so_far += actually_only_moving
                                    new_row = {"n": actually_only_moving, "age": chicken_row["age"]}
                                    chicken_row["n"] = chicken_row["n"] - actually_only_moving
                                    if "objs" in chicken_row:
                                        new_row["objs"] = chicken_row["objs"][:actually_only_moving]
                                        chicken_row["objs"] = chicken_row["objs"][actually_only_moving:]
                                    chickens_to_move.append(new_row)

                    for chickens_removed in chickens_to_move:  # TODO should refactor this with del like the above part
                        if chickens_removed in shed_info["chickens"]:
                            shed_info["chickens"].remove(chickens_removed)
                    if shed_has_had_chickens_removed:
                        initiate_cleaning(properties, start_index, shed_i, int_time)

    return chickens_to_move


def chickens_to_cull(properties, start_index, int_time, num_to_cull):
    start_facility = properties[start_index]
    chickens_to_move = []

    moved_so_far = 0
    for shed_i, shed_info in start_facility.sheds.items():
        shed_has_had_chickens_removed = False
        if "chickens" in shed_info:
            for chicken_row in shed_info["chickens"]:
                if moved_so_far + chicken_row["n"] <= num_to_cull:  # i.e., we can move everything
                    chickens_to_move.append(chicken_row)
                    shed_has_had_chickens_removed = True
                    moved_so_far += chicken_row["n"]
                else:
                    actually_only_moving = num_to_cull - moved_so_far
                    if actually_only_moving > 0:
                        moved_so_far += actually_only_moving
                        new_row = {"n": actually_only_moving, "age": chicken_row["age"]}
                        chicken_row["n"] = chicken_row["n"] - actually_only_moving
                        if "objs" in chicken_row:
                            new_row["objs"] = chicken_row["objs"][:actually_only_moving]
                            chicken_row["objs"] = chicken_row["objs"][actually_only_moving:]
                        chickens_to_move.append(new_row)

            for chickens_removed in chickens_to_move:  # TODO should refactor this with del like the above part
                if chickens_removed in shed_info["chickens"]:
                    shed_info["chickens"].remove(chickens_removed)
            if shed_has_had_chickens_removed:
                initiate_cleaning(properties, start_index, shed_i, int_time)

    return chickens_to_move


def move_chickens_onto_truck(properties, start_index, target_index):
    start_facility = properties[start_index]
    target_facility = properties[target_index]

    num_chickens_to_move = 0
    row_indices_to_move = []
    for i in range(len(start_facility.chickens)):
        row = start_facility.chickens[i]
        chicken_age = row[2]
        if chicken_age > start_facility.allowed_movement_details[target_facility.type]["age"]:
            num_chickens_to_move += row[0]
            row_indices_to_move.append(i)

    chickens_to_move = []
    for i in reversed(row_indices_to_move):
        row = start_facility.chickens.pop(i)
        del row[1]  # delete the shed number
        chickens_to_move.append(row)

    return num_chickens_to_move, chickens_to_move


def get_eggs_to_move(properties, start_index, target_index):
    start_facility = properties[start_index]
    target_facility = properties[target_index]

    num_eggs_to_move = 0
    row_indices_to_move = []
    egg_rows_to_move = []
    for i in range(len(start_facility.eggs)):
        row = start_facility.eggs[i]
        egg_age = row[1]
        if egg_age > start_facility.allowed_movement_details[target_facility.type]["age"]:
            num_eggs_to_move += row[0]
            row_indices_to_move.append(i)

    for i in reversed(row_indices_to_move):  # pop from the end...
        egg_rows_to_move.append(start_facility.eggs.pop(i))

    return num_eggs_to_move, egg_rows_to_move


def align_chicken_objects(properties, start_index, target_index, chickens_on_truck):
    facility = properties[start_index]
    new_facility = properties[target_index]
    if facility.check_if_chicken_objects() == True and new_facility.check_if_chicken_objects() == False:
        new_facility.init_animals(None)  # now both have chicken objects
        # TODO: would be nice to actually check if any of those chickens on the truck are infected or not. if not, we can just remove the objs and not do this init'ing
    elif facility.check_if_chicken_objects() == False and new_facility.check_if_chicken_objects() == True:
        # need to convert new chickens into chicken objects before passing them on
        chickens_on_truck["objs"] = [Animal(None) for _ in range(chickens_on_truck["n"])]
    else:
        pass  # should already be aligned

    return chickens_on_truck


def animal_movement(
    properties,
    day,
    controlzone,
    reduced_movement_zone=None,
    movement_reduction_factor=0.2,
    all_movement_reduction_factor=1.0,
):
    """Animal movements

    TODO Would like to refactor this, at least a little
    E.g. assigning/moving animals to empty sheds ; keeping track of sheds that should actually be empty because they're under cleaning!!


    """

    date = premises.convert_time_to_date(day)

    # rows of day, converted date, moving from property index, to property index, WHAT was moved (chickens or eggs), number of animals/eggs moved, a narrative report (locations, number of animals moved)

    movement_record = []
    movement_permit_requests = []
    number_of_movement_requests = 0
    for premise_index, facility in enumerate(properties):
        in_control_zone = False
        if controlzone != None and facility.polygon.intersects(controlzone):
            in_control_zone = True
            # TODO: if True, use this to raise movement permit request

        in_reduced_movement_zone = False
        if reduced_movement_zone != None and facility.polygon.intersects(reduced_movement_zone):
            in_reduced_movement_zone = True

        # chickens movement only
        if (
            not facility.culled_status
            and facility.type != "abbatoir"
            and facility.type != "egg processing"
            and facility.type != "backyard"
            and facility.status != "IP"
            and facility.status != "RP"
        ):
            num_chickens_to_move, chicken_properties_to_move_to = facility.want_to_move_animals()

            if num_chickens_to_move > 0:  # if neither is >0, then there is no movement for this facility

                # get places to move to
                targets_unrestricted_zones = []
                targets_in_control_zones = []

                capacity_in_unrestricted_zones = 0
                capacity_in_restricted_zones = 0

                # go through the properties we *could* move chickens to, to find which ones *can* have chickens moved to them
                for property_index in chicken_properties_to_move_to:
                    target_facility = properties[property_index]
                    if target_facility == "IP" or target_facility == "RP":
                        continue  # skip it
                    empty_sheds, num_chickens_per_shed_target = target_facility.accepting_chickens()
                    # need to figure out....how many premises the movements need to be made to OTL
                    if empty_sheds != [] and num_chickens_per_shed_target > 0:
                        if controlzone != None and target_facility.polygon.intersects(controlzone):
                            if random.uniform(0, 1) < movement_reduction_factor * all_movement_reduction_factor:
                                # ILLEGAL MOVEMENT, aka with some probability, there will be movement without movement requests!
                                targets_unrestricted_zones.append([property_index, empty_sheds, num_chickens_per_shed_target])
                                capacity_in_unrestricted_zones += len(empty_sheds) * num_chickens_per_shed_target
                            else:
                                targets_in_control_zones.append([property_index, empty_sheds, num_chickens_per_shed_target])
                                capacity_in_restricted_zones += len(empty_sheds) * num_chickens_per_shed_target
                        else:
                            if reduced_movement_zone != None and target_facility.polygon.intersects(reduced_movement_zone):
                                if random.uniform(0, 1) < all_movement_reduction_factor:  # illegal or reduced movement
                                    targets_unrestricted_zones.append([property_index, empty_sheds, num_chickens_per_shed_target])
                                    capacity_in_unrestricted_zones += len(empty_sheds) * num_chickens_per_shed_target
                                else:
                                    targets_in_control_zones.append([property_index, empty_sheds, num_chickens_per_shed_target])
                                    capacity_in_restricted_zones += len(empty_sheds) * num_chickens_per_shed_target
                            else:
                                targets_unrestricted_zones.append([property_index, empty_sheds, num_chickens_per_shed_target])
                                capacity_in_unrestricted_zones += len(empty_sheds) * num_chickens_per_shed_target
                random.shuffle(targets_unrestricted_zones)
                random.shuffle(targets_in_control_zones)
                if targets_unrestricted_zones == [] and targets_in_control_zones == []:
                    # print(
                    #     f"facility {facility.id} ({facility.type}) wants to move {num_chickens_to_move} chickens to {facility.allowed_movement_details['chickens']} but no suitable target!"
                    # )
                    pass
                else:
                    if in_control_zone and (random.uniform(0, 1) > movement_reduction_factor):
                        # TODO permit request:  facility id[], type [], status [], requests to move [X animals] to [target facility]
                        if targets_unrestricted_zones != [] or targets_in_control_zones != []:  # i.e., there is a place it could have moved stuff
                            print(f"{facility.type} (sim_id {facility.id}) would like to move some chickens but is inside restricted zone")
                            number_of_movement_requests += 1
                    elif in_reduced_movement_zone and (random.uniform(0, 1) > movement_reduction_factor):
                        if targets_unrestricted_zones != [] or targets_in_control_zones != []:  # i.e., there is a place it could have moved stuff
                            print(f"{facility.type} (sim_id {facility.id}) would like to move some chickens but is inside control zone")
                            number_of_movement_requests += 1
                    else:
                        # ILLEGAL MOVEMENT, aka with some probability, there will be movement without movement requests!
                        # or just normal movement with source facility not in a restricted zone
                        if capacity_in_unrestricted_zones < num_chickens_to_move:
                            chickens_to_move = remove_chickens_from_property_ready_for_movement(
                                properties, premise_index, day, capacity_in_unrestricted_zones
                            )
                            chickens_left_to_move = capacity_in_unrestricted_zones
                        else:
                            chickens_to_move = remove_chickens_from_property_ready_for_movement(properties, premise_index, day)
                            chickens_left_to_move = num_chickens_to_move

                            # just a check to make sure it's the right number...
                            test = 0
                            for row in chickens_to_move:
                                test += row["n"]
                            if test != num_chickens_to_move:
                                raise ValueError("test is not the same as the num_chickens_to_move")

                        for target_index, empty_sheds, num_chickens_per_shed_target in targets_unrestricted_zones:
                            new_facility = properties[target_index]
                            chickens_moved = 0
                            for empty_shed in empty_sheds:
                                if num_chickens_per_shed_target > chickens_left_to_move:
                                    while chickens_to_move != []:
                                        chickens_on_truck = chickens_to_move.pop()
                                        chickens_to_transfer = align_chicken_objects(properties, premise_index, target_index, chickens_on_truck)
                                        chickens_left_to_move = chickens_left_to_move - chickens_on_truck["n"]
                                        chickens_moved += chickens_on_truck["n"]
                                        new_facility.sheds[empty_shed]["chickens"].append(chickens_to_transfer)

                                    if chickens_left_to_move != 0:
                                        raise ValueError("There should be no more chickens left to move!")
                                else:  # num_chickens_per_shed_target < chickens_left_to_move:
                                    # which means that we can't move all the chickens into this shed
                                    local_chickens_moved_into_this_shed = 0
                                    while local_chickens_moved_into_this_shed < num_chickens_per_shed_target:
                                        possible_chickens_on_truck = chickens_to_move.pop()
                                        chickens_left_to_move_into_this_shed = num_chickens_per_shed_target - local_chickens_moved_into_this_shed
                                        if chickens_left_to_move_into_this_shed < possible_chickens_on_truck["n"]:
                                            # only transfer some of them
                                            chickens_on_truck = {
                                                "n": chickens_left_to_move_into_this_shed,
                                                "age": possible_chickens_on_truck["age"],
                                            }
                                            chickens_left_over = {
                                                "n": possible_chickens_on_truck["n"] - chickens_left_to_move_into_this_shed,
                                                "age": possible_chickens_on_truck["age"],
                                            }
                                            if "objs" in possible_chickens_on_truck:
                                                chickens_on_truck["objs"] = possible_chickens_on_truck["objs"][:chickens_left_to_move_into_this_shed]
                                                chickens_left_over["objs"] = possible_chickens_on_truck["objs"][chickens_left_to_move_into_this_shed:]
                                            chickens_to_move.append(chickens_left_over)
                                        else:
                                            chickens_on_truck = possible_chickens_on_truck  # transfer all of them

                                        chickens_to_transfer = align_chicken_objects(properties, premise_index, target_index, chickens_on_truck)
                                        chickens_left_to_move = chickens_left_to_move - chickens_to_transfer["n"]
                                        chickens_moved += chickens_to_transfer["n"]
                                        local_chickens_moved_into_this_shed += chickens_to_transfer["n"]
                                        new_facility.sheds[empty_shed]["chickens"].append(chickens_to_transfer)

                                if chickens_to_move == []:
                                    break

                            if chickens_moved > 0:
                                row = [
                                    day,
                                    f"{date}",
                                    premise_index,
                                    target_index,
                                    "chicken",
                                    chickens_moved,
                                    facility.type,
                                    new_facility.type,
                                    f"DAY {date} - moved {chickens_moved} chicken(s) from {facility.type} (sim_id {facility.id}) ({facility.region}) to {new_facility.type} (sim_id {new_facility.id}) ( {new_facility.region})",
                                ]

                                if len(row) != len(movement_record_header):
                                    raise ValueError("The length of movement record is not the same as the movement header")
                                    # added in case I decide to change the information recorded again

                                movement_record.append(row)

                        # if (chickens_left_to_move > 0):
                        #     # which means there are still chickens to move, but target properties are all in movement restricted zones
                        #     # need to make some kind of "hypothetical chicken movement" here... or just request the first one rather than multiple
                        #     for property_index, empty_sheds, num_chickens_per_shed_target in targets_in_control_zones:
                        #         for empty_shed in empty_sheds:
                        #             if num_chickens_per_shed_target > num_chickens_to_move:
                        #                 pass
                        #         raise ValueError("Movement requests not yet coded!")

                        if chickens_left_to_move > 0:
                            raise ValueError("After everything, there are still chickens left...this shouldn't happen!")
        if "layers" in facility.type and facility.status not in ["IP", "RP"]:
            # movement should be to egg processors only
            num_eggs_to_move, egg_properties_to_move_to = facility.want_to_move_eggs()
            if num_eggs_to_move > 0:

                # get places to move to
                targets_unrestricted_zones = []
                targets_in_control_zones = []
                for property_index in egg_properties_to_move_to:
                    target_facility = properties[property_index]
                    if target_facility == "IP" or target_facility == "RP":
                        continue  # skip it
                    if controlzone != None and target_facility.polygon.intersects(controlzone):
                        if random.uniform(0, 1) < movement_reduction_factor * all_movement_reduction_factor:
                            # ILLEGAL MOVEMENT, aka with some probability, there will be movement without movement requests!
                            targets_unrestricted_zones.append(property_index)
                        else:
                            targets_in_control_zones.append(property_index)
                    else:
                        if reduced_movement_zone != None and target_facility.polygon.intersects(reduced_movement_zone):
                            if random.uniform(0, 1) < all_movement_reduction_factor:
                                targets_unrestricted_zones.append(property_index)
                            else:
                                targets_in_control_zones.append(property_index)
                        else:
                            targets_unrestricted_zones.append(property_index)
                random.shuffle(targets_unrestricted_zones)
                if targets_unrestricted_zones == []:
                    # print(
                    #     f"facility {facility.id} ({facility.type}) wants to move {num_eggs_to_move} eggs to {facility.allowed_movement_details['eggs']} but no suitable target!"
                    # )
                    pass
                else:
                    if in_control_zone and (random.uniform(0, 1) > movement_reduction_factor):
                        # TODO permit request:  facility id[], type [], status [], requests to move [X animals] to [target facility]
                        if targets_unrestricted_zones != [] or targets_in_control_zones != []:  # i.e., there is a place it could have moved stuff
                            print(f"{facility.type} (sim_id {facility.id}) would like to move some eggs but is in the restricted zone")
                            number_of_movement_requests += 1
                    elif in_reduced_movement_zone and (random.uniform(0, 1) > movement_reduction_factor):
                        if targets_unrestricted_zones != [] or targets_in_control_zones != []:  # i.e., there is a place it could have moved stuff
                            print(f"{facility.type} (sim_id {facility.id}) would like to move some chickens but is inside control zone")
                            number_of_movement_requests += 1
                    else:
                        # ILLEGAL MOVEMENT, aka with some probability, there will be movement without movement requests!
                        # or just normal movement with source facility not in a restricted zone
                        facility.eggs = facility.eggs - num_eggs_to_move  # remove eggs from source
                        new_facility = properties[targets_unrestricted_zones[0]]
                        # for now, we're just moving to one facility; later I could reduce this e.g. by the number of eggs that fit on a single truck or something
                        new_facility.eggs += num_eggs_to_move  # add eggs to target

                        row = [
                            day,
                            f"{date}",
                            premise_index,
                            targets_unrestricted_zones[0],
                            "egg",
                            num_eggs_to_move,
                            facility.type,
                            new_facility.type,
                            f"DAY {date} - moved {num_eggs_to_move} egg(s) from {facility.type} (sim_id {facility.id}) ({facility.region}) to {new_facility.type} (sim_id {new_facility.id}) ({new_facility.region})",
                        ]

                        if len(row) != len(movement_record_header):
                            raise ValueError("The length of movement record is not the same as the movement header")
                            # added in case I decide to change the information recorded again

                        movement_record.append(row)
        if facility.type == "breeder" and facility.status not in ["IP", "RP"]:
            # egg movements for breeder properties
            # if eggs, for movement to hatcheries, need to check chickens not check accepting eggs, and move eggs into sheds
            num_eggs_to_move, egg_properties_to_move_to = facility.want_to_move_eggs()
            if num_eggs_to_move > 0:

                # get places to move to
                targets_unrestricted_zones = []
                capacity_in_unrestricted_zones = 0
                targets_in_control_zones = []
                for property_index in egg_properties_to_move_to:
                    target_facility = properties[property_index]
                    if target_facility == "IP" or target_facility == "RP":
                        continue  # skip it
                    empty_sheds, num_chickens_per_shed_target = target_facility.accepting_chickens()
                    if empty_sheds != [] and num_chickens_per_shed_target > 0:
                        if controlzone != None and target_facility.polygon.intersects(controlzone):
                            if random.uniform(0, 1) < movement_reduction_factor * all_movement_reduction_factor:
                                # ILLEGAL MOVEMENT, aka with some probability, there will be movement without movement requests!
                                targets_unrestricted_zones.append([property_index, empty_sheds, num_chickens_per_shed_target])
                                capacity_in_unrestricted_zones += len(empty_sheds) * num_chickens_per_shed_target
                            else:
                                targets_in_control_zones.append([property_index, empty_sheds, num_chickens_per_shed_target])
                        else:
                            if reduced_movement_zone != None and target_facility.polygon.intersects(reduced_movement_zone):
                                if random.uniform(0, 1) < all_movement_reduction_factor:
                                    targets_unrestricted_zones.append([property_index, empty_sheds, num_chickens_per_shed_target])
                                    capacity_in_unrestricted_zones += len(empty_sheds) * num_chickens_per_shed_target
                                else:
                                    targets_in_control_zones.append([property_index, empty_sheds, num_chickens_per_shed_target])
                            else:
                                targets_unrestricted_zones.append([property_index, empty_sheds, num_chickens_per_shed_target])
                                capacity_in_unrestricted_zones += len(empty_sheds) * num_chickens_per_shed_target

                random.shuffle(targets_unrestricted_zones)
                if targets_unrestricted_zones == []:
                    # print(
                    #     f"facility {facility.id} ({facility.type}) wants to move {num_eggs_to_move} fertilised eggs to {facility.allowed_movement_details['eggs']} but no suitable target!"
                    # )
                    pass
                else:
                    if in_control_zone and (random.uniform(0, 1) > movement_reduction_factor):
                        if targets_unrestricted_zones != [] or targets_in_control_zones != []:  # i.e., there is a place it could have moved stuff
                            print(f"{facility.type} (sim_id {facility.id}) would like to move some chickens but is in the restricted zone")
                            number_of_movement_requests += 1
                    elif in_reduced_movement_zone and (random.uniform(0, 1) > movement_reduction_factor):
                        if targets_unrestricted_zones != [] or targets_in_control_zones != []:  # i.e., there is a place it could have moved stuff
                            print(f"{facility.type} (sim_id {facility.id}) would like to move some chickens but is inside control zone")
                            number_of_movement_requests += 1
                    else:
                        # ILLEGAL MOVEMENT, aka with some probability, there will be movement without movement requests!
                        # or just normal movement with source facility not in a restricted zone
                        if capacity_in_unrestricted_zones < num_eggs_to_move:
                            eggs_left_to_move = capacity_in_unrestricted_zones
                        else:
                            eggs_left_to_move = num_eggs_to_move
                        facility.eggs = facility.eggs - eggs_left_to_move

                        for target_index, empty_sheds, num_chickens_per_shed_target in targets_unrestricted_zones:
                            new_facility = properties[target_index]
                            eggs_moved_into_sheds = 0
                            for empty_shed in empty_sheds:
                                if num_chickens_per_shed_target > eggs_left_to_move:

                                    eggs_left_to_move = 0
                                    eggs_moved_into_sheds += eggs_left_to_move
                                    new_facility.sheds[empty_shed]["eggs"].append({"n": eggs_left_to_move, "age": 0})
                                else:  # num_chickens_per_shed_target < eggs_left_to_move:
                                    # which means that we can't move all the fertilised eggs into this shed
                                    eggs_left_to_move = eggs_left_to_move - num_chickens_per_shed_target
                                    eggs_moved_into_sheds += num_chickens_per_shed_target
                                    new_facility.sheds[empty_shed]["eggs"].append({"n": num_chickens_per_shed_target, "age": 0})
                            if eggs_moved_into_sheds > 0:
                                row = [
                                    day,
                                    f"{date}",
                                    premise_index,
                                    target_index,
                                    "egg",
                                    num_eggs_to_move,
                                    facility.type,
                                    new_facility.type,
                                    f"DAY {date} - moved {eggs_moved_into_sheds} egg(s) from {facility.type} (sim_id {facility.id}) ({facility.region}) to {new_facility.type} (sim_id {new_facility.id}) ({new_facility.region})",
                                ]

                                if len(row) != len(movement_record_header):
                                    raise ValueError("The length of movement record is not the same as the movement header")
                                    # added in case I decide to change the information recorded again

                                movement_record.append(row)

        if facility.type == "abbatoir" and facility.status not in ["IP", "RP"]:

            total_chickens_being_slaughtered = 0
            for shed_i, shed_info in facility.sheds.items():
                for row in shed_info["chickens"]:
                    total_chickens_being_slaughtered += row["n"]

                shed_info["chickens"] = []  # removing them from existence
            if total_chickens_being_slaughtered > 0 and controlzone != None and facility.polygon.intersects(controlzone):
                print(f"note that abbatoir (sim_{facility.id}) is in the control zone (just a note, no impact on slaughtering)")

            if total_chickens_being_slaughtered > 0:
                # create the movement record
                row = [
                    day,
                    f"{date}",
                    premise_index,
                    -2,
                    "chicken",
                    total_chickens_being_slaughtered,
                    facility.type,
                    "chicken meat distributor",
                    f"DAY {date} - moved {total_chickens_being_slaughtered} chickens from {facility.type} (sim_id {facility.id}) ({facility.region}) to chicken meat distributor",
                ]

                if len(row) != len(movement_record_header):
                    raise ValueError("The length of movement record is not the same as the movement header")
                    # added in case I decide to change the information recorded again

                movement_record.append(row)

        if facility.type == "egg processing" and facility.status not in ["IP", "RP"]:
            total_eggs_being_moved = facility.eggs
            facility.eggs = 0  # reset to zero
            if total_eggs_being_moved > 0:
                if controlzone != None and facility.polygon.intersects(controlzone):
                    print(
                        f"note that egg processor (sim_id {facility.id}) is in the control zone (just a note, no impact on processing/distribution)"
                    )

                # create the movement record
                row = [
                    day,
                    f"{date}",
                    premise_index,
                    -1,
                    "egg",
                    total_eggs_being_moved,
                    facility.type,
                    "egg distributor",
                    f"DAY {date} - moved {total_eggs_being_moved} egg(s) from {facility.type} (sim_id {facility.id}) ({facility.region}) to egg distributor",
                ]

                if len(row) != len(movement_record_header):
                    raise ValueError("The length of movement record is not the same as the movement header")
                    # added in case I decide to change the information recorded again

                movement_record.append(row)
        # TODO
        # if there are movement restrictions on the facility, raise a movement permit request
        # if there are movement restrictions on the property-to-move-to, also raise a movement request
        # otherwise, conduct the movement.
        # check if it has any eggs it wants to move
        # if yes: check if are any movement restrictions on it
        # get the properties that can accept the eggs, and sort them - as having movement restrictions too, and not
        # if there are movement restrictions on the facility, raise a movement permit request
        # if there are movement restrictions on the property-to-move-to, also raise a movement request
        # otherwise, conduct the movement.

    print(f"movements for day {day} / {date} completed")

    movement_record = pd.DataFrame(movement_record, columns=movement_record_header)

    return movement_record, number_of_movement_requests


def rounding_entities(val):
    if val < 10:
        return val
    if val < 100:
        return math.floor(val / 5) * 5
    if val < 500:
        return math.floor(val / 50) * 50
    if val < 1000:
        return math.floor(val / 100) * 100
    if val < 10000:
        return math.floor(val / 1000) * 1000
    if val < 100000:
        return math.floor(val / 10000) * 10000
    return math.floor(val / 100000) * 100000


def little_date_converter(input_date_string):
    """converts dd/mm/yyyy date into yyyy-mm-dd"""

    if input_date_string == "NA":
        return "NA"
    day_string, month_string, year_string = input_date_string.split("/")
    new_date = f"{year_string}-{month_string}-{day_string}"
    return new_date


def save_approx_known_data(properties, folder_path, unique_output="", output_suffix=""):
    """Outputs a csv with the approximately known data on properties and premises

    Returns
    -------
    list

    """

    header = [
        "sim_id",
        "case_id",
        "status",
        "ip",
        "clinical_date",
        "self_report_date",
        "confirmation_date",  # aka notification date
        "removal_date",
        "recovery_date",
        "vacc_date",
        "LGA",
        "xcoord",
        "ycoord",
        "area",
        "enterprise",
        "housing",
        "sheds",
        "total_chickens",
        "data_source",
        # "total_eggs",
        "last_surveillance_date",
        "animals_clinical",
        "last_PCR_date",
        "PCR_result",
        "last_cull_date",
        "culled_birds",
        "destroyed_eggs",
        "last_conducted_contact_tracing",
        "vaccinated_birds",
        "case_created_date",
    ]

    if "QLD-provided" in folder_path:
        header.append("QLD_property")

    data_rows_for_Biosecurity_Commons = []

    if output_suffix == "":
        file = os.path.join(folder_path, f"approx_known_data_{unique_output}.csv")
    else:
        file = os.path.join(folder_path, f"approx_known_data{output_suffix}.csv")
    with open(file, "w", newline="") as f:

        # create the csv writer
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

        for facility in properties:
            try:
                self_report_date = facility.custom_info["self_report_date"]
            except:
                self_report_date = "NA"

            try:
                infection_data_known = facility.custom_info["infection_data_known"]
            except:
                infection_data_known = False

            try:
                property_data_known = facility.custom_info["property_data_known"]
            except:
                property_data_known = False

            try:
                last_surveillance_date = facility.custom_info["last_surveillance_date"]
            except:
                last_surveillance_date = "NA"

            try:
                animals_clinical = facility.custom_info["animals_clinical"]
            except:
                animals_clinical = "NA"

            try:
                last_PCR_date = facility.custom_info["last_PCR_date"]
            except:
                last_PCR_date = "NA"

            try:
                PCR_result = facility.custom_info["PCR_result"]
            except:
                PCR_result = "NA"

            try:
                last_cull_date = facility.custom_info["last_cull_date"]
            except:
                last_cull_date = "NA"

            try:
                culled_birds = facility.custom_info["culled_birds"]
            except:
                culled_birds = "NA"

            try:
                destroyed_eggs = facility.custom_info["destroyed_eggs"]
            except:
                destroyed_eggs = "NA"

            try:
                last_conducted_contact_tracing_date = facility.custom_info["last_conducted_contact_tracing"]
            except:
                last_conducted_contact_tracing_date = "NA"

            if "vaccinated_birds" in facility.custom_info:
                vaccinated_birds = facility.custom_info["vaccinated_birds"]
            else:
                vaccinated_birds = "NA"

            # default known housing/enterprise type is nothing
            housing_type = ""
            enterprise_type = ""
            if facility.data_source == "RBE":
                enterprise_type = facility.type
                housing_type = facility.housing_type
            else:
                if "layers" in facility.type:
                    if facility.chicken_capacity >= 100 or facility.data_source != "ALSR":
                        enterprise_type = "layers"
                    if facility.data_source != "ALSR" or property_data_known:
                        housing_type = facility.type[7:]
                elif "broiler" in facility.type:
                    if facility.chicken_capacity >= 100 or facility.data_source != "ALSR" or property_data_known:
                        enterprise_type = facility.type

                    if facility.data_source != "ALSR" or property_data_known:
                        housing_type = facility.housing_type
                else:
                    if facility.chicken_capacity >= 100 or facility.data_source != "ALSR" or property_data_known:
                        enterprise_type = facility.type

            try:
                case_created_date = facility.case_created_date
            except:
                case_created_date = "NA"

            # num_chickens = facility.get_num_chickens()
            # num_eggs = facility.get_num_eggs() + facility.get_num_fertilised_eggs()

            if facility.data_source != "":  # if something is actually known!
                row = [
                    facility.id,  # facility.sim_id, sim_id is too complicated ya...
                    facility.case_id,
                    facility.status,
                    facility.ip,
                    facility.clinical_date if infection_data_known else "NA",
                    self_report_date,
                    facility.notification_date,
                    facility.removal_date,
                    facility.recovery_date if infection_data_known else "NA",
                    facility.vacc_date,
                    facility.region,
                    facility.coordinates[0],
                    facility.coordinates[1],
                    facility.known_area,
                    enterprise_type,
                    housing_type,
                    facility.known_sheds,
                    facility.known_birds,
                    facility.data_source,
                    last_surveillance_date,
                    animals_clinical,
                    last_PCR_date,
                    PCR_result,
                    last_cull_date,
                    culled_birds,
                    destroyed_eggs,
                    last_conducted_contact_tracing_date,
                    vaccinated_birds,
                    case_created_date,
                ]

                if "QLD-provided" in folder_path:
                    row.append(facility.QLD_property_type)

                writer.writerow(row)

                if facility.status == "NA":
                    BC_status = "NIL"
                elif facility.status == "RP":
                    BC_status = "IP"
                else:
                    BC_status = facility.status

                row = [
                    facility.id,
                    BC_status,
                    little_date_converter(facility.clinical_date) if infection_data_known else "NA",
                    little_date_converter(facility.notification_date),
                    little_date_converter(facility.removal_date),
                    little_date_converter(facility.recovery_date) if infection_data_known else "NA",
                    facility.coordinates[0],
                    facility.coordinates[1],
                ]

                data_rows_for_Biosecurity_Commons.append(row)

    BC_header = [
        "id",
        "status",
        "clinical_date",
        "notification_date",
        "removal_date",
        "recovery_date",
        "lon",
        "lat",
    ]

    if output_suffix == "":
        file = os.path.join(folder_path, f"approx_known_data_{unique_output}_Biosecurity_Commons.csv")
    else:
        file = os.path.join(folder_path, f"approx_known_data{output_suffix}_Biosecurity_Commons.csv")
    with open(file, "w", newline="") as f:
        # create the csv writer
        writer = csv.writer(f)

        # write the header
        writer.writerow(BC_header)
        for row in data_rows_for_Biosecurity_Commons:
            writer.writerow(row)
