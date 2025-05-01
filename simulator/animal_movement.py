""" Animal movement code

    Adapted from the animal_movement_code.py in the FMD_modelling module
    (Adapted to add more control over movements and output movements that had occured for contact tracting purposes)

"""

import numpy as np
from simulator.premises import convert_time_to_date
from simulator.spatial_functions import quick_distance_haversine
from iteround import saferound
import warnings
import os
import csv
import pandas as pd
import random


movement_record_header = [
    "day",
    "date",
    "from",
    "to",
    "animals",
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
    """Conduct animal movements between properties that are allowed to move

    Parameters
    ----------
    properties : list
        list of premises, with information about where they can move, and when they can move
    day : int
        current simulation day
    controlzone : polygon
        polygon that describes movement restrictions, if any
    """
    added_animals = []

    date = convert_time_to_date(day)

    # rows of day, converted date, moving from property index, to property index, number of animals moved, a narrative report (locations, number of animals moved),
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

    # take animals out first, then add them to other properties later (so animals don't move twice in one day)
    for premise_index in indices_that_can_move:
        property_p = properties[premise_index]
        if property_p.movement_flag(day):
            allowed_movement_neighbours, total_num_allowed = property_p.calculate_allowed_movement_neighbours(
                indices_that_can_move
            )

            # if there's somewhere to move the animals
            if total_num_allowed > 0:
                number_animals = property_p.calculate_num_animals_to_move()

                if number_animals == 0:
                    break  # no animals to move

                # next, calculate the properties to move to (at least one property):
                num_properties_to_move_to = np.random.randint(1, property_p.max_daily_movements + 1)

                # capping the number of properties if there aren't enough animals
                if num_properties_to_move_to > number_animals:
                    num_properties_to_move_to = number_animals

                # distributing out the number of animals to different properties
                num_animals_moved_to_each_property = saferound(
                    [number_animals / num_properties_to_move_to] * num_properties_to_move_to,
                    places=0,
                )
                num_animals_moved_to_each_property = [int(x) for x in num_animals_moved_to_each_property]

                # choose some random properties to move to, based on their movement probabilities
                move_to_types_list = property_p.calculate_where_to_move(
                    num_properties_to_move_to, allowed_movement_neighbours
                )

                moving_to_premises_indices = [
                    np.random.choice(allowed_movement_neighbours[ptype]) for ptype in move_to_types_list
                ]
                if len(set(moving_to_premises_indices)) != len(moving_to_premises_indices):
                    warnings.warn("There are duplicate indices, this should probably be changed")

                for moving_to_premise_index, number_animals in zip(
                    moving_to_premises_indices, num_animals_moved_to_each_property
                ):

                    row = [
                        day,
                        f"{date}",
                        premise_index,
                        moving_to_premise_index,
                        f"{number_animals}",
                        f"DAY {date} - moved {number_animals} animals from property ID {property_p.id} ({property_p.type} in {property_p.state}) to property ID {properties[moving_to_premise_index].id} ({properties[moving_to_premise_index].type} in {properties[moving_to_premise_index].state})",
                    ]
                    if len(row) != len(movement_record_header):
                        raise ValueError("The length of movement record is not the same as the movement header")
                        # added in case I decide to change the information recorded again

                    movement_record.append(row)

                    # keeping track of moving the animals, the actual movement will occur at the end
                    moving_animal_list = property_p.move_out_animals(number_animals)

                    added_animals.append([moving_animal_list, moving_to_premise_index])
    # move animals to properties
    if added_animals:  # as long as there are animals to move
        for moving_animal_list, moving_index in added_animals:
            properties[moving_index].add_animals(moving_animal_list)

    movement_record = pd.DataFrame(movement_record, columns=movement_record_header)

    return movement_record


def extra_southward_movement(properties, day):
    """Conduct extra southward movements of infected animals between properties
    Purpose is to hopefully speed up spread of disease from Queensland southward

    Parameters
    ----------
    properties : list
        list of premises, with information about where they can move, and when they can move
    day : int
    """
    added_animals = []

    date = convert_time_to_date(day)

    # rows of day, converted date, moving from property index, to property index, number of animals moved, a narrative report (locations, number of animals moved),
    movement_record = []

    # find premises that are infected but not culled or under testing
    indices_that_can_move = []
    for premise_index in range(len(properties)):
        site = properties[premise_index]
        if (
            not site.culled_status
            and site.clinical_report_outcome == None
            and site.undergoing_testing == False
            and site.prop_infectious > 0
        ):
            indices_that_can_move.append(premise_index)

    # take animals out first, then add them to other properties later
    for premise_index in indices_that_can_move:
        property_p = properties[premise_index]
        if random.uniform(0, 1) < 0.7:
            allowed_movement_neighbours, total_num_allowed = property_p.calculate_allowed_movement_neighbours(
                indices_that_can_move
            )

            # then, only select southern neighbours
            allowed_southern_neighbours = {}
            actual_total_num_allowed = 0
            for allowed_type in allowed_movement_neighbours.keys():
                allowed_southern_neighbours[allowed_type] = []
                for index_j in allowed_movement_neighbours[allowed_type]:
                    property_j = properties[index_j]
                    if property_j.y < property_p.y and property_j.x > 141:
                        allowed_southern_neighbours[allowed_type].append(index_j)
                        actual_total_num_allowed += 1
            total_num_allowed = actual_total_num_allowed
            allowed_movement_neighbours = allowed_southern_neighbours

            south_most_neighbours = {}
            # version to select the MOST southern neighbours only
            actual_total_num_allowed = 0
            for allowed_type in allowed_movement_neighbours.keys():
                y_list = []
                south_most_neighbours[allowed_type] = []
                for index_j in allowed_movement_neighbours[allowed_type]:
                    property_j = properties[index_j]
                    y_list.append((index_j, property_j.y))

                if y_list != []:
                    min_y_position_index = max(y_list, key=lambda i: i[1])[0]
                    south_most_neighbours[allowed_type].append(min_y_position_index)
                    actual_total_num_allowed += 1

            total_num_allowed = actual_total_num_allowed
            allowed_movement_neighbours = south_most_neighbours

            # if there's somewhere to move the animals
            if total_num_allowed > 0:
                number_animals = property_p.calculate_num_animals_to_move()

                if number_animals == 0:
                    break  # no animals to move

                # next, calculate the properties to move to (at least one property):
                num_properties_to_move_to = np.random.randint(1, property_p.max_daily_movements + 1)

                # capping the number of properties if there aren't enough animals
                if num_properties_to_move_to > number_animals:
                    num_properties_to_move_to = number_animals

                # distributing out the number of animals to different properties
                num_animals_moved_to_each_property = saferound(
                    [number_animals / num_properties_to_move_to] * num_properties_to_move_to,
                    places=0,
                )
                num_animals_moved_to_each_property = [int(x) for x in num_animals_moved_to_each_property]

                # choose some random properties to move to, based on their movement probabilities
                move_to_types_list = property_p.calculate_where_to_move(
                    num_properties_to_move_to, allowed_movement_neighbours
                )

                moving_to_premises_indices = [
                    np.random.choice(allowed_movement_neighbours[ptype]) for ptype in move_to_types_list
                ]
                if len(set(moving_to_premises_indices)) != len(moving_to_premises_indices):
                    warnings.warn("There are duplicate indices, this should probably be changed")

                for moving_to_premise_index, number_animals in zip(
                    moving_to_premises_indices, num_animals_moved_to_each_property
                ):

                    row = [
                        day,
                        f"{date}",
                        premise_index,
                        moving_to_premise_index,
                        f"{number_animals}",
                        f"DAY {date} - moved {number_animals} animals from property ID {property_p.id} ({property_p.type} in {property_p.state}) to property ID {properties[moving_to_premise_index].id} ({properties[moving_to_premise_index].type} in {properties[moving_to_premise_index].state})",
                    ]
                    if len(row) != len(movement_record_header):
                        raise ValueError("The length of movement record is not the same as the movement header")
                        # added in case I decide to change the information recorded again

                    movement_record.append(row)

                    # keeping track of moving the animals, the actual movement will occur at the end
                    moving_animal_list = property_p.move_out_animals(number_animals)

                    extra = property_p.move_out_an_infectious_animal()
                    if extra != False:
                        moving_animal_list.append(extra)

                    added_animals.append([moving_animal_list, moving_to_premise_index])
    # move animals to properties
    if added_animals:  # as long as there are animals to move
        for moving_animal_list, moving_index in added_animals:
            properties[moving_index].add_animals(moving_animal_list)

    movement_record = pd.DataFrame(movement_record, columns=movement_record_header)

    return movement_record


def save_movement_record(folder_path, movement_records):
    """Saves records of animal movements as a csv."""

    file = os.path.join(folder_path, f"movement_records.csv")

    movement_records.to_csv(file, index=False)
