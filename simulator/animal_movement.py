""" Animal movement code

    Adapted from the animal_movement_code.py in the FMD_modelling module
    (Adapted to add more control over movements and output movements that had occured for contact tracting purposes)

"""

import numpy as np
from simulator.premises import convert_time_to_date
from simulator.spatial_setup import quick_distance_haversine
from iteround import saferound


def animal_movement(
    properties,
    n,
    movement_frequency,  # TODO ? remove this and have it as an attribute for each property?
    movement_probability,  # TODO ? remove this and have it as an attribute for each property?
    movement_prop_animals,  # TODO ? remove this and have it as an attribute for each property?
    day,
    controlzone,
    max_movement_distance=500,
):
    """Conduct animal movements between properties that are allowed to move

    Parameters
    ----------
    properties : list
        list of premises
    n : int
        number of total properties (not used, TODO - remove it? and modify wherever animal_movement is called)
    movement_frequency : int
        properties might move animals every #movement_frequency days
    movement_probability : double
        probability of animal movement on a movement day
    movement_prop_animals : double
        proportion of animals that would move
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
            if controlzone == None or not properties[premise_index].polygon.intersects(
                controlzone
            ):
                indices_that_can_move.append(premise_index)

    # take animals out first, then add them to other properties later (so animals don't move twice in one day)
    for premise_index in indices_that_can_move:

        # if it's a movement day for this property
        if not (
            (day - properties[premise_index].movement_start_day)
            % properties[premise_index].movement_frequency
        ):

            # if there is movement
            prob_movement = np.random.rand()
            if prob_movement < properties[premise_index].movement_probability:

                # where can the animals moving to
                moving_to_premise_indices = []
                for i in indices_that_can_move:
                    if (
                        i != premise_index
                    ):  # property hasn't been culled and isn't the moving from property
                        # check if distance is less than max distance max_movement_distance
                        if (
                            quick_distance_haversine(
                                properties[premise_index].coordinates,
                                properties[i].coordinates,
                            )
                            < max_movement_distance
                        ):
                            # and also check if the property is the right type for moving to
                            if (
                                properties[i].type
                                in properties[premise_index].allowed_movement
                            ):

                                moving_to_premise_indices.append(i)

                # if there's somewhere to move the animals
                if moving_to_premise_indices:

                    # how many animals moving
                    property_size = len(properties[premise_index].animals)
                    number_animals = int(
                        np.floor(
                            properties[premise_index].movement_prop_animals
                            * property_size
                        )
                    )
                    if property_size > 1 and number_animals == 0:
                        number_animals = (
                            1  # keeping at least one animal in each property
                        )

                    if number_animals == 0:
                        break  # no animals to move

                    # how many different properties will the animals be moving to
                    num_properties_to_move_to = (
                        np.random.randint(
                            1, properties[premise_index].max_daily_movements
                        )
                        if properties[premise_index].max_daily_movements > 1
                        else 1
                    )

                    if num_properties_to_move_to > number_animals:
                        num_properties_to_move_to = number_animals

                    num_animals_moved_to_each_property = saferound(
                        [number_animals / num_properties_to_move_to]
                        * num_properties_to_move_to,
                        places=0,
                    )
                    num_animals_moved_to_each_property = [
                        int(x) for x in num_animals_moved_to_each_property
                    ]

                    # choose random premise to move to
                    # for saleyards and traders, they should be able to have movement to MULTIPLE different properties in one day
                    moving_to_premise_indices = np.random.choice(
                        moving_to_premise_indices,
                        size=num_properties_to_move_to,
                        replace=False,
                    )

                    # TODO haven't actually used the capacity limit here...

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
                            moving_animal_index = np.random.randint(
                                0, len(properties[premise_index].animals)
                            )
                            moving_animal = properties[premise_index].animals.pop(
                                moving_animal_index
                            )
                            moving_animal_list.append(moving_animal)

                        added_animals.append(
                            [moving_animal_list, moving_to_premise_index]
                        )

    # move animals to properties
    if added_animals:  # as long as there are animals to move
        for moving_list, moving_index in added_animals:
            for moving_animal in moving_list:
                properties[moving_index].animals.append(moving_animal)

    return movement_record
