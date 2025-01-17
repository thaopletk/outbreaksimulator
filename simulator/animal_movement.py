""" Animal movement code

    Adapted from the animal_movement_code.py in the FMD_modelling module
    (Adapted to add more control over movements and output movements that had occured for contact tracting purposes)

"""

import numpy as np
from simulator.premises import convert_time_to_date
from simulator.spatial_functions import quick_distance_haversine
from iteround import saferound
import warnings


def trialsimex_animal_movement(properties, day, controlzone):
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

    # rows of day, moving from property index, to property index, plus a narrative report (locations, number of animals moved)
    movement_record = []

    indices_that_can_move = []
    for premise_index in range(len(properties)):
        if not properties[premise_index].culled_status:
            if controlzone == None or not properties[premise_index].polygon.intersects(controlzone):

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
                        premise_index,
                        moving_to_premise_index,
                        f"DAY {date} - moved {number_animals} animals from property ID {property_p.id} ({property_p.type}) to property ID {properties[moving_to_premise_index].id} ({properties[moving_to_premise_index].type})",
                    ]  # TODO add more information in the narrative report or row as required
                    movement_record.append(row)

                    # keeping track of moving the animals, the actual movement will occur at the end
                    moving_animal_list = property_p.move_out_animals(number_animals)

                    added_animals.append([moving_animal_list, moving_to_premise_index])
    # move animals to properties
    if added_animals:  # as long as there are animals to move
        for moving_animal_list, moving_index in added_animals:
            properties[moving_index].add_animals(moving_animal_list)

    return movement_record


def animal_movement(
    properties,
    day,
    controlzone,
    max_movement_distance=500,
):
    """Conduct animal movements between properties that are allowed to move.

    This version assumes that all properties are the same type (without distinction between movement patterns)

    Parameters
    ----------
    properties : list
        list of premises
    day : int
        current simulation day
    controlzone : polygon
        polygon that describes movement restrictions, if any
    max_movement_distance : int, double
        maximum distance that animals could be moved, in kilometers
    """
    added_animals = []

    date = convert_time_to_date(day)

    movement_record = (
        []
    )  # rows of day, moving from property index, to property index, plus a narrative report (locations, number of animals moved)
    # required for: the narrative, but also if we want to implement certain things based on contact tracing

    # the only properties that can move are those who are not culled and do not intersect with the control zone
    # TODO : technically there probably shouldn't be movement if a property has been identified in contact tracing and is undergoing testing
    indices_that_can_move = []
    for premise_index in range(len(properties)):
        if not properties[premise_index].culled_status:
            if controlzone == None or not properties[premise_index].polygon.intersects(controlzone):
                indices_that_can_move.append(premise_index)

    # take animals out first, then add them to other properties later (so animals don't move twice in one day)
    for premise_index in indices_that_can_move:

        # if it's a movement day for this property
        if not ((day - properties[premise_index].movement_start_day) % properties[premise_index].movement_frequency):

            # if there is movement
            prob_movement = np.random.rand()
            if prob_movement < properties[premise_index].movement_probability:

                # where can the animals moving to
                moving_to_premise_indices = []
                for i in indices_that_can_move:
                    if i != premise_index:  # property hasn't been culled and isn't the moving from property
                        # check if distance is less than max distance max_movement_distance
                        # actually, this should be pre-calculated at the start, to reduce time later on... TODO
                        if (
                            quick_distance_haversine(
                                properties[premise_index].coordinates,
                                properties[i].coordinates,
                            )
                            < max_movement_distance
                        ):
                            # and also check if the property is the right type for moving to
                            if properties[i].type in properties[premise_index].allowed_movement:

                                moving_to_premise_indices.append(i)

                # if there's somewhere to move the animals
                if moving_to_premise_indices:

                    # how many animals moving
                    property_size = len(properties[premise_index].animals)
                    number_animals = int(np.floor(properties[premise_index].movement_prop_animals * property_size))
                    if property_size > 1 and number_animals == 0:
                        number_animals = 1  # keeping at least one animal in each property

                    if number_animals == 0:
                        break  # no animals to move

                    # how many different properties will the animals be moving to
                    num_properties_to_move_to = (
                        np.random.randint(1, properties[premise_index].max_daily_movements + 1)
                        if properties[premise_index].max_daily_movements > 1
                        else 1
                    )

                    if num_properties_to_move_to > number_animals:
                        num_properties_to_move_to = number_animals

                    num_animals_moved_to_each_property = saferound(
                        [number_animals / num_properties_to_move_to] * num_properties_to_move_to,
                        places=0,
                    )
                    num_animals_moved_to_each_property = [int(x) for x in num_animals_moved_to_each_property]

                    # choose random premise to move to
                    # for saleyards and traders, they should be able to have movement to MULTIPLE different properties in one day
                    moving_to_premise_indices = np.random.choice(
                        moving_to_premise_indices,
                        size=num_properties_to_move_to,
                        replace=False,
                    )

                    for moving_to_premise_index, number_animals in zip(
                        moving_to_premise_indices, num_animals_moved_to_each_property
                    ):

                        row = [
                            day,
                            premise_index,
                            moving_to_premise_index,
                            f"DAY {date} - moved {number_animals} animals from property ID {properties[premise_index].id} ({properties[premise_index].type}) to property ID {properties[moving_to_premise_index].id} ({properties[moving_to_premise_index].type})",
                        ]  # TODO add more information in the narrative report or row as required
                        movement_record.append(row)

                        # keeping track of moving the animals
                        moving_animal_list = []
                        for _ in range(int(number_animals)):
                            moving_animal_index = np.random.randint(0, len(properties[premise_index].animals))
                            moving_animal = properties[premise_index].animals.pop(moving_animal_index)

                            moving_animal_list.append(moving_animal)

                        added_animals.append([moving_animal_list, moving_to_premise_index])

    # move animals to properties
    if added_animals:  # as long as there are animals to move
        for moving_list, moving_index in added_animals:
            for moving_animal in moving_list:
                properties[moving_index].animals.append(moving_animal)

    return movement_record
