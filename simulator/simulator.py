"""Simulator

    Runs parts of the simulation. Adapted from FMD_modelling, abm_fn.py
    Adjusted to have explicit parameter requirements rather than a dictionary with params

    Typical workflow involves calling:
    * property_setup
    * simulate_outbreak

"""

import sys
import os
import random

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
import simulator.animal_movement as animal_movement
from iteround import saferound
from shapely.ops import transform, unary_union
from simulator.spatial_functions import quick_distance_haversine
import time


def calculate_num_property_types(num, proportion_dict):
    # calculate the number of properties for each type (and farms as the remainder)
    num_properties_per_type = {}
    if sum(list(proportion_dict.values())) <= 1:

        running_sum = 0
        for property_type, proportion in proportion_dict.items():
            num_properties_per_type[property_type] = max(int(math.ceil(num * proportion)), 1)
            running_sum += num_properties_per_type[property_type]

        if running_sum <= num:
            num_properties_per_type["farm"] = num - running_sum
        else:
            raise ValueError(
                "Total number of properties too is too high, and can't assign any farms. Recommend to lower proportions."
            )

    else:
        raise ValueError("Proportion of different property types exceeds 1 (exceeds 100%)")

    return num_properties_per_type


def property_specific_initialisation_animals(
    spatial_only_parameters,
    properties_specific_parameters,
    property_coordinates,
    property_areas,
    neighbourhoods,
    property_polygons,
    property_polygons_puffed,
):
    animal_types = list(properties_specific_parameters["animal_types_proportion"].keys())

    if sum(list(properties_specific_parameters["animal_types_proportion"].values())) != 1:
        raise ValueError("Total proportion of animals does not equal 1 (100%)")

    num_animal_properties = saferound(
        [x * spatial_only_parameters["n"] for x in properties_specific_parameters["animal_types_proportion"].values()],
        places=0,
    )
    num_animal_properties = [int(x) for x in num_animal_properties]
    # some might be zero. whatever.

    # assumes the types of properties are the same for all animals for now
    num_properties_per_type = {
        animal: calculate_num_property_types(num, properties_specific_parameters["special_property_types_proportion"])
        for animal, num in zip(animal_types, num_animal_properties)
    }

    # initialise properties
    properties = [None] * spatial_only_parameters["n"]

    available_i_s = list(range(0, len(property_coordinates)))
    random.shuffle(available_i_s)

    for animal in animal_types:
        for property_type, n_to_generate in num_properties_per_type[animal].items():
            for j in range(n_to_generate):
                new_p_i = available_i_s.pop()
                animal_multiplier = 1
                if property_type in ["saleyard", "feedlot"]:
                    animal_multiplier = 2  # double the number of animals on that property

                try:
                    new_p = premises.Premises(
                        num_animals=max(
                            int(
                                animal_multiplier
                                * property_areas[new_p_i]
                                * properties_specific_parameters["average_animals_per_ha"]
                            ),
                            animal_multiplier * 5,
                        ),  # at least five animals per property
                        movement_freq=properties_specific_parameters["movement_frequency"][property_type],
                        coordinates=property_coordinates[new_p_i],
                        area_ha=property_areas[new_p_i],
                        neighbourhood=neighbourhoods[new_p_i],
                        property_polygon=property_polygons[new_p_i],
                        property_polygon_puffed=property_polygons_puffed[new_p_i],
                        property_type=property_type,
                        movement_probability=properties_specific_parameters["movement_probability"][property_type],
                        movement_prop_animals=properties_specific_parameters["movement_prop_animals"][property_type],
                        allowed_movement=properties_specific_parameters["allowed_movement"][property_type],
                        max_daily_movements=properties_specific_parameters["max_daily_movements"][property_type],
                        animal_type=animal,
                    )
                except:
                    time.sleep(1.0)  # pause for a second to try and avoid errors due to geocoder requests

                properties[new_p_i] = new_p
                properties[new_p_i].id = (
                    new_p_i  # override the default assigned id, as the properties were added out of order (above)
                )
                properties[new_p_i].init_animals(
                    None
                )  # init with empty "params", as no parameters are actually used to initialise animals

    # construct their movement information
    for i, property_i in enumerate(properties):
        if property_i.type == "saleyard":
            # allowing for much longer range movement from saleyards to other places (but not vice-versa)
            max_allowable_movement = 5 * properties_specific_parameters["max_movement_km"]
        else:
            max_allowable_movement = properties_specific_parameters["max_movement_km"]

        property_i_neighbours = {}
        for allowed_type in property_i.allowed_movement.keys():
            property_i_neighbours[allowed_type] = []

        for j, property_j in enumerate(properties):
            if i == j:
                continue
            if property_j.type in property_i_neighbours and property_j.animal_type == property_i.animal_type:
                distance = quick_distance_haversine(
                    property_i.coordinates,
                    property_j.coordinates,
                )

                if distance < max_allowable_movement and distance > 100 and random.uniform(0, 1) < 0.2:
                    property_i_neighbours[property_j.type].append(j)

        property_i.movement_neighbours = property_i_neighbours

    return properties


def property_setup_v03(
    folder_path,
    spatial_only_paramaters={
        "n": 10,
        "r_wind": 25,
        "xrange": [150.2503, 151.39695],
        "yrange": [-32.61181, -31.60829],
        "average_property_ha": 300,
    },
    properties_specific_parameters={
        "average_animals_per_ha": 0.2,
        "max_movement_km": 500,
        "special_property_types_proportion": {
            "saleyard": 0.001,
            "trader": 0.0025,
            "feedlot": 0.005,
            "abbattoir": 0.005,
            "stud farm": 0.001,
            # "farm": None, Note: "farm" types will be calculated as the remainder
        },
        "movement_frequency": {
            "saleyard": 1,
            "trader": 1,
            "feedlot": 1,
            "abbattoir": 1000,
            "stud farm": 7,
            "farm": 5,
        },
        "movement_probability": {
            "saleyard": 0.8,
            "trader": 0.8,
            "feedlot": 0.2,
            "abbattoir": 0,
            "stud farm": 0.8,
            "farm": 0.4,
        },
        "movement_prop_animals": {
            "saleyard": 0.2,
            "trader": 0.2,
            "feedlot": 0.1,
            "abbattoir": 0,
            "stud farm": 0.2,
            "farm": 0.1,
        },
        "allowed_movement": {
            "saleyard": {
                "saleyard": 0.1,
                "trader": 0.1,
                "feedlot": 0.2,
                "abbattoir": 0.1,
                "farm": 0.4,
                "stud farm": 0.1,
            },
            "trader": {
                "saleyard": 0.1,
                "trader": 0.05,
                "feedlot": 0.3,
                "abbattoir": 0.05,
                "farm": 0.4,
                "stud farm": 0.1,
            },
            "feedlot": {"abbattoir": 1},
            "abbattoir": {},
            "farm": {
                "saleyard": 0.2,
                "trader": 0.2,
                "feedlot": 0.2,
                "abbattoir": 0.1,
                "farm": 0.2,
                "stud farm": 0.1,
            },
            "stud farm": {"farm": 0.4, "saleyard": 0.4, "trader": 0.2},
        },
        "max_daily_movements": {
            "saleyard": 6,
            "trader": 3,
            "feedlot": 2,
            "abbattoir": 0,
            "farm": 1,
            "stud farm": 6,
        },
    },
):
    """Set up the map and initiate properties: first half of 2025 version

    Differences from previous version (trial_simex_property_setup(...)):
        - No unique stud-farm allocation (i.e., not placing the stud farm first at a central location)
        - changed the input format so that different property types are entered as a percentage rather than a hard-fixed number, and the code takes a minimum of 1 type of each property. (i.e., coming back to the older version property_setup(...) though with a slight modification of which proportions need to be included - farm type is now automatically calculated. )


    TODO: complete this description

    Parameters
    ----------
    n : int
        number of properties to generate
    xrange : list
        x (longitude) width
    yrange  : list
        y (latitude) width
    average_property_ha : double or int
        a rough target for the average property size, in hectares

    Returns
    -------
    property_coordinates : list
        list of coordinates of the properties (center)
    property_polygons : list of Polygons
        the list containing the properties' shapely Polygon shape
    property_areas : list
        list of sizes/areas (in hectares) of the generated properties

    """

    spatial_only_filename = os.path.join(folder_path, "spatial_only_setup.pickle")
    if not os.path.exists(spatial_only_filename):

        # 1. Spatial-only, property-type-agnostic setup
        (
            property_coordinates,
            adjacency_matrix,
            neighbour_pairs,
            neighbourhoods,
            property_polygons,
            property_polygons_puffed,
            property_areas,
        ) = spatial_setup.generate_properties_with_land(
            spatial_only_paramaters["n"],
            spatial_only_paramaters["r_wind"],
            spatial_only_paramaters["xrange"],
            spatial_only_paramaters["yrange"],
            spatial_only_paramaters["average_property_ha"],
        )  # uses the spatial-setup specific generator, rather than the fmdmodelling property generator

        output.plot_map_land(
            property_polygons,
            property_polygons_puffed,
            spatial_only_paramaters["xrange"],
            spatial_only_paramaters["yrange"],
            folder_path,
        )

        with open(spatial_only_filename, "wb") as file:
            pickle.dump(
                [
                    property_coordinates,
                    adjacency_matrix,
                    neighbour_pairs,
                    neighbourhoods,
                    property_polygons,
                    property_polygons_puffed,
                    property_areas,
                ],
                file,
            )
    else:
        with open(spatial_only_filename, "rb") as file:
            (
                property_coordinates,
                adjacency_matrix,
                neighbour_pairs,
                neighbourhoods,
                property_polygons,
                property_polygons_puffed,
                property_areas,
            ) = pickle.load(file)

    # 2. Property-specific initialisation

    # calculate the number of properties for each type (and farms as the remainder)
    num_properties_per_type = {}
    # first, a check that the proportion is <=1:
    if sum(list(properties_specific_parameters["special_property_types_proportion"].values())) <= 1:

        running_sum = 0

        for property_type, proportion in properties_specific_parameters["special_property_types_proportion"].items():
            num_properties_per_type[property_type] = max(int(math.ceil(spatial_only_paramaters["n"] * proportion)), 1)
            running_sum += num_properties_per_type[property_type]

        if running_sum <= spatial_only_paramaters["n"]:
            num_properties_per_type["farm"] = spatial_only_paramaters["n"] - running_sum
        else:
            raise ValueError(
                "Total number of properties too is too high, and can't assign any farms. Recommend to lower proportions."
            )

    else:
        raise ValueError("Proportion of different property types exceeds 1 (exceeds 100%)")

    # initialise properties
    properties = [None] * spatial_only_paramaters["n"]

    available_i_s = list(range(0, len(property_coordinates)))
    random.shuffle(available_i_s)

    for property_type, n_to_generate in num_properties_per_type.items():
        # if property_type == "stud farm":
        #     if n_to_generate != 1:
        #         raise ValueError("Code assumes that there will only be one stud farm") # allowing multiple stud farms now

        for j in range(n_to_generate):
            new_p_i = available_i_s.pop()

            animal_multiplier = 1
            if property_type in ["saleyard", "feedlot"]:
                animal_multiplier = 2  # double the number of animals on that property

            try:
                new_p = premises.Premises(
                    num_animals=max(
                        int(
                            animal_multiplier
                            * property_areas[new_p_i]
                            * properties_specific_parameters["average_animals_per_ha"]
                        ),
                        animal_multiplier * 5,
                    ),  # at least five animals per property
                    movement_freq=properties_specific_parameters["movement_frequency"][property_type],
                    coordinates=property_coordinates[new_p_i],
                    area_ha=property_areas[new_p_i],
                    neighbourhood=neighbourhoods[new_p_i],
                    property_polygon=property_polygons[new_p_i],
                    property_polygon_puffed=property_polygons_puffed[new_p_i],
                    property_type=property_type,
                    movement_probability=properties_specific_parameters["movement_probability"][property_type],
                    movement_prop_animals=properties_specific_parameters["movement_prop_animals"][property_type],
                    allowed_movement=properties_specific_parameters["allowed_movement"][property_type],
                    max_daily_movements=properties_specific_parameters["max_daily_movements"][property_type],
                )
            except:
                time.sleep(1.0)  # pause for a second to try and avoid errors due to geocoder requests

            properties[new_p_i] = new_p
            properties[new_p_i].id = (
                new_p_i  # override the default assigned id, as the properties were added out of order (above)
            )
            properties[new_p_i].init_animals(
                None
            )  # init with empty "params", as no parameters are actually used to initialise animals

    # construct their movement information
    for i, property_i in enumerate(properties):
        if property_i.type == "saleyard":
            # allowing for much longer range movement from saleyards to other places (but not vice-versa)
            max_allowable_movement = 5 * properties_specific_parameters["max_movement_km"]
        else:
            max_allowable_movement = properties_specific_parameters["max_movement_km"]

        property_i_neighbours = {}
        for allowed_type in property_i.allowed_movement.keys():
            property_i_neighbours[allowed_type] = []

        for j, property_j in enumerate(properties):
            if i == j:
                continue
            if property_j.type in property_i_neighbours:
                distance = quick_distance_haversine(
                    property_i.coordinates,
                    property_j.coordinates,
                )

                if distance < max_allowable_movement and distance > 100 and random.uniform(0, 1) < 0.2:
                    property_i_neighbours[property_j.type].append(j)

        property_i.movement_neighbours = property_i_neighbours

    property_setup_info = [
        properties,
        property_coordinates,
        adjacency_matrix,
        neighbour_pairs,
        neighbourhoods,
        property_polygons,
        property_polygons_puffed,
        property_areas,
    ]

    output.save_data_properties(property_setup_info, folder_path)

    save_current_state(properties, "init", folder_path, "init")

    return property_setup_info


def trial_simex_property_setup(
    folder_path,
    spatial_only_paramaters={
        "n": 10,
        "r_wind": 25,
        "xrange": [150.2503, 151.39695],
        "yrange": [-32.61181, -31.60829],
        "average_property_ha": 300,
    },
    properties_specific_parameters={
        "average_animals_per_ha": 0.2,
        "max_movement_km": 500,
        "n_property_types": {
            "saleyard": 2,
            "trader": 5,
            "feedlot": 10,
            "abbattoir": 10,
            "stud farm": 1,
            "farm": 1972,
        },
        "movement_frequency": {
            "saleyard": 1,
            "trader": 1,
            "feedlot": 1,
            "abbattoir": 1000,
            "stud farm": 7,
            "farm": 5,
        },
        "movement_probability": {
            "saleyard": 0.8,
            "trader": 0.8,
            "feedlot": 0.2,
            "abbattoir": 0,
            "stud farm": 0.8,
            "farm": 0.4,
        },
        "movement_prop_animals": {
            "saleyard": 0.2,
            "trader": 0.2,
            "feedlot": 0.1,
            "abbattoir": 0,
            "stud farm": 0.2,
            "farm": 0.1,
        },
        "allowed_movement": {
            "saleyard": {
                "saleyard": 0.1,
                "trader": 0.1,
                "feedlot": 0.2,
                "abbattoir": 0.1,
                "farm": 0.4,
                "stud farm": 0.1,
            },
            "trader": {
                "saleyard": 0.1,
                "trader": 0.05,
                "feedlot": 0.3,
                "abbattoir": 0.05,
                "farm": 0.4,
                "stud farm": 0.1,
            },
            "feedlot": {"abbattoir": 1},
            "abbattoir": {},
            "farm": {
                "saleyard": 0.2,
                "trader": 0.2,
                "feedlot": 0.2,
                "abbattoir": 0.1,
                "farm": 0.2,
                "stud farm": 0.1,
            },
            "stud farm": {"farm": 0.4, "saleyard": 0.4, "trader": 0.2},
        },
        "max_daily_movements": {
            "saleyard": 6,
            "trader": 3,
            "feedlot": 2,
            "abbattoir": 0,
            "farm": 1,
            "stud farm": 6,
        },
    },
):
    """Set up the map and initiate properties - for the December 2024 Trial Simulation Exercise"""

    # checks that the sum of n_property_types is equal to spatial_only_paramaters["n"]
    property_specific_sum = sum([value for key, value in properties_specific_parameters["n_property_types"].items()])
    if spatial_only_paramaters["n"] != property_specific_sum:
        raise ValueError(
            "The total number of properties in spatial_only_parameters doesn't match the number in properties_specific_parameters"
        )

    # 1. Spatial-only, property-type-agnostic setup
    (
        property_coordinates,
        adjacency_matrix,
        neighbour_pairs,
        neighbourhoods,
        property_polygons,
        property_polygons_puffed,
        property_areas,
    ) = spatial_setup.generate_properties_with_land(
        spatial_only_paramaters["n"],
        spatial_only_paramaters["r_wind"],
        spatial_only_paramaters["xrange"],
        spatial_only_paramaters["yrange"],
        spatial_only_paramaters["average_property_ha"],
    )  # uses the spatial-setup specific generator, rather than the fmdmodelling property generator

    output.plot_map_land(
        property_polygons,
        property_polygons_puffed,
        spatial_only_paramaters["xrange"],
        spatial_only_paramaters["yrange"],
        folder_path,
    )

    # 2. Property-specific initialisation

    # initialise properties
    properties = [None] * spatial_only_paramaters["n"]

    # unique situation: select one of the center properties to be the stud farm (where infection will be seeded)
    stud_farm_i = 0  # default
    # property coordinates allocated at random, so we can just go through one-by-one to find a suitable property to see
    x_width = spatial_only_paramaters["xrange"][1] - spatial_only_paramaters["xrange"][0]
    y_width = spatial_only_paramaters["yrange"][1] - spatial_only_paramaters["yrange"][0]
    for i in range(len(property_coordinates)):
        coords = property_coordinates[i]
        if (
            coords[0] <= spatial_only_paramaters["xrange"][1] - x_width / 3
            and coords[0] >= spatial_only_paramaters["xrange"][0] + x_width / 3
            and coords[1] <= spatial_only_paramaters["yrange"][1] - y_width / 3
            and coords[1] >= spatial_only_paramaters["yrange"][0] + y_width / 3
        ):
            # set this to be the stud farm
            stud_farm_i = i
            break

    # now initialise all the properties
    available_i_s = list(range(0, len(property_coordinates)))
    available_i_s.remove(stud_farm_i)
    random.shuffle(available_i_s)
    central_stud_farm_flag = False
    for property_type, n_to_generate in properties_specific_parameters["n_property_types"].items():
        # if property_type == "stud farm":
        #     if n_to_generate != 1:
        #         raise ValueError("Code assumes that there will only be one stud farm") # allowing multiple stud farms now

        for j in range(n_to_generate):
            if (
                property_type == "stud farm" and central_stud_farm_flag == False
            ):  # ensures that there is a central stud farm, while allowing for other stud farm locations
                new_p_i = stud_farm_i
                central_stud_farm_flag = True
            else:
                new_p_i = available_i_s.pop()

            animal_multiplier = 1
            if property_type in ["saleyard", "feedlot"]:
                animal_multiplier = 2  # double the number of animals on that property

            new_p = premises.Premises(
                num_animals=max(
                    int(
                        animal_multiplier
                        * property_areas[new_p_i]
                        * properties_specific_parameters["average_animals_per_ha"]
                    ),
                    animal_multiplier * 5,
                ),  # at least five animals per property
                movement_freq=properties_specific_parameters["movement_frequency"][property_type],
                coordinates=property_coordinates[new_p_i],
                area_ha=property_areas[new_p_i],
                neighbourhood=neighbourhoods[new_p_i],
                property_polygon=property_polygons[new_p_i],
                property_polygon_puffed=property_polygons_puffed[new_p_i],
                property_type=property_type,
                movement_probability=properties_specific_parameters["movement_probability"][property_type],
                movement_prop_animals=properties_specific_parameters["movement_prop_animals"][property_type],
                allowed_movement=properties_specific_parameters["allowed_movement"][property_type],
                max_daily_movements=properties_specific_parameters["max_daily_movements"][property_type],
            )

            properties[new_p_i] = new_p
            properties[new_p_i].id = (
                new_p_i  # override the default assigned id, as the properties were added out of order (above)
            )
            properties[new_p_i].init_animals(
                None
            )  # init with empty "params", as no parameters are actually used to initialise animals

    # construct their movement information
    for i, property_i in enumerate(properties):
        if property_i.type == "saleyard":
            # allowing for much longer range movement from saleyards to other places (but not vice-versa)
            max_allowable_movement = 5 * properties_specific_parameters["max_movement_km"]
        else:
            max_allowable_movement = properties_specific_parameters["max_movement_km"]

        property_i_neighbours = {}
        for allowed_type in property_i.allowed_movement.keys():
            property_i_neighbours[allowed_type] = []

        for j, property_j in enumerate(properties):
            if i == j:
                continue
            if property_j.type in property_i_neighbours:
                if (
                    quick_distance_haversine(
                        property_i.coordinates,
                        property_j.coordinates,
                    )
                    < max_allowable_movement
                ):
                    property_i_neighbours[property_j.type].append(j)

        property_i.movement_neighbours = property_i_neighbours

    property_setup_info = [
        properties,
        property_coordinates,
        adjacency_matrix,
        neighbour_pairs,
        neighbourhoods,
        property_polygons,
        property_polygons_puffed,
        property_areas,
    ]

    output.save_data_properties(property_setup_info, folder_path)

    save_current_state(properties, "init", folder_path, "init")

    return property_setup_info


# NOTE this could be moved into the spatial_setup file...
def property_setup(
    folder_path,
    n=10,
    r_wind=25,
    average_property_ha=300,
    xrange=[150.2503, 151.39695],
    yrange=[-32.61181, -31.60829],
    average_animals_per_ha=0.1,
    property_types={
        "saleyard": 0.001,
        "trader": 0.007,
        "feedlot": 0.007,
        "abbattoir": 0.001,
        "farm": 1 - 0.001 - 0.007 - 0.007 - 0.001,
    },
    movement_frequency={
        "saleyard": 1,
        "trader": 1,
        "feedlot": 7,
        "abbattoir": 10000,
        "farm": 5,
    },
    movement_probability={
        "saleyard": 1,
        "trader": 1,
        "feedlot": 0.2,
        "abbattoir": 0,
        "farm": 0.5,
    },
    movement_prop_animals={
        "saleyard": 0.2,
        "trader": 0.8,
        "feedlot": 0.1,
        "abbattoir": 0,
        "farm": 0.2,
    },
    allowed_movement={
        "saleyard": ["saleyard", "trader", "feedlot", "abbattoir", "farm"],
        "trader": ["saleyard", "trader", "feedlot", "abbattoir", "farm"],
        "feedlot": ["abbattoir"],
        "abbattoir": [],
        "farm": ["saleyard", "trader", "feedlot", "abbattoir", "farm"],
    },
    max_daily_movements={
        "saleyard": 6,
        "trader": 3,
        "feedlot": 2,
        "abbattoir": 0,
        "farm": 1,
    },
    **_,
):
    """

    n: int
        Number of properties to generate
    r_wind : int, double
        Distance in kilometers, to define wind neighbours
    average_property_ha : int, double
        Not actually the average property hectares generated at the moment... but as a rough guide (TODO - adjust generation to make this value the actual average?)
    average_animals_per_ha : double
        Average number of animals per hectare, to initialise properties
        The default value comes from https://www.farmstyle.com.au/forum/raising-cattle-meat-how-many-acre where a cow needs ~10 hectares of land to raise
    property_types : dictionary
        the different property types and their proportions (to generate)
    movement_frequency : dictionary
        Properties might move animals every x days; a dictionary containing this information for different types of properties
    movement_probability: dictionary
        The probability of movement on a given day
    movement_prop_animals : dictionary
        number of animals that might be moved
    allowed_movement : dictionary
        the property types that the key-property can move animals to
    max_daily_movements : dictionary
        some property types can move animals to multiple different properties

    """

    (
        property_coordinates,
        adjacency_matrix,
        neighbour_pairs,
        neighbourhoods,
        property_polygons,
        property_polygons_puffed,
        property_areas,
    ) = spatial_setup.generate_properties_with_land(
        n, r_wind, xrange, yrange, average_property_ha
    )  # uses the spatial-setup specific generator, rather than the fmdmodelling property generator

    output.plot_map_land(property_polygons, property_polygons_puffed, xrange, yrange, folder_path)

    properties_type_number = saferound([max(x * n, 1.0) for x in property_types.values()], places=0)
    properties_type_number = [int(x) for x in properties_type_number]
    if sum(properties_type_number) > n:
        difference = sum(properties_type_number) - n
        max_index = properties_type_number.index(max(properties_type_number))
        properties_type_number[max_index] = properties_type_number[max_index] - difference

    if any(properties_type_number) == 0:
        raise ValueError("After all this hard work, there should be at least one property for each property type")

    # initialise properties
    properties = []
    i = 0
    for property_type, n_to_generate in zip(property_types.keys(), properties_type_number):

        for j in range(n_to_generate):
            # new property
            animal_multiplier = 1
            if property_type in ["saleyard", "feedlot"]:
                animal_multiplier = 2  # double the number of animals on that property
            new_p = premises.Premises(
                num_animals=max(
                    int(animal_multiplier * property_areas[i] * average_animals_per_ha),
                    animal_multiplier * 5,
                ),  # at least five animals per property
                movement_freq=movement_frequency[property_type],
                coordinates=property_coordinates[i],
                area_ha=property_areas[i],
                neighbourhood=neighbourhoods[i],
                property_polygon=property_polygons[i],
                property_polygon_puffed=property_polygons_puffed[i],
                property_type=property_type,
                movement_probability=movement_probability[property_type],
                movement_prop_animals=movement_prop_animals[property_type],
                allowed_movement=allowed_movement[property_type],
                max_daily_movements=max_daily_movements[property_type],
            )

            properties.append(new_p)
            properties[i].init_animals(
                None
            )  # init with empty "params", as no parameters are actually used to initialise animals

            i += 1

    property_setup_info = [
        properties,
        property_coordinates,
        adjacency_matrix,
        neighbour_pairs,
        neighbourhoods,
        property_polygons,
        property_polygons_puffed,
        property_areas,
    ]

    output.save_data_properties(property_setup_info, folder_path)

    # note that you should only need to keep "properties" from here on
    return property_setup_info


def seed_infection_within_bound(
    xrange_bounds,
    yrange_bounds,
    properties,
    time=0,
    xlims=[],
    ylims=[],
    folder_path="",
    unique_output="",
    latent_period=7,
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
        ):
            viable_properties.append(i)

    # seed this property
    # randomly pick a property to see:
    seed_property = random.choice(viable_properties)

    p = properties[seed_property]
    # TODO technically, to encapsulate this better, there should a function that allows you to infect a specific animal(s), and that will then update infection_status, prop_infections, cumulative_infections, and exposure_date, and anything else that may need to be updated
    p.infection_status = 1
    p.exposure_date = premises.convert_time_to_date(time - latent_period)
    num_infected = 10
    for seed_animal in range(num_infected):
        p.animals[seed_animal].status = "infected"

    p.prop_infectious = num_infected / p.size
    p.cumulative_infections = num_infected

    plot_current_state(
        properties,
        time,
        xlims,
        ylims,
        folder_path,
        controlzone={},
        infectionpoly=False,
        contacts_for_plotting={},
    )

    save_current_state(properties, time, folder_path, unique_output)

    return properties, seed_property


def seed_infection_at_property_type(
    xrange,
    yrange,
    properties,
    property_type,
    time=0,
    xlims=[],
    ylims=[],
    folder_path="",
    unique_output="",
    latent_period=7,
):
    """Seeds an infection at a particular type of property (e.g., farm, stud farm, feedlot).

    The code tries to find a location in the middle third of the map (so that spread can be limited within the map).

    """
    seed_property = 0  # default
    seed_animal = 0  # default

    # property coordinates allocated at random, so we can just go through one-by-one to find a suitable property to see
    x_width = xrange[1] - xrange[0]
    y_width = yrange[1] - yrange[0]

    for i, property in enumerate(properties):
        if property.type == property_type:
            seed_property = i
            coords = property.coordinates
            if (
                coords[0] <= xrange[1] - x_width / 3
                and coords[0] >= xrange[0] + x_width / 3
                and coords[1] <= yrange[1] - y_width / 3
                and coords[1] >= yrange[0] + y_width / 3
            ):
                # seed this property
                seed_property = i
                break

    p = properties[seed_property]
    # TODO technically, to encapsulate this better, there should a function that allows you to infect a specific animal(s), and that will then update infection_status, prop_infections, cumulative_infections, and exposure_date, and anything else that may need to be updated
    p.infection_status = 1
    p.exposure_date = premises.convert_time_to_date(time - latent_period)
    p.animals[seed_animal].status = "infected"
    p.prop_infectious = 1 / p.size
    p.cumulative_infections = 1

    plot_current_state(
        properties,
        time,
        xlims,
        ylims,
        folder_path,
        controlzone={},
        infectionpoly=False,
        contacts_for_plotting={},
    )

    save_current_state(properties, time, folder_path, unique_output)

    return properties, seed_property


def seed_infection(xrange, yrange, properties, time=0):
    """Send infection in the middle third of the map if possible (we don't want the outbreak spreading to edges and stop simply because of the unnatural map boundaries)"""
    seed_property = 0  # default
    seed_animal = 0

    # property coordinates allocated at random, so we can just go through one-by-one to find a suitable property to see
    x_width = xrange[1] - xrange[0]
    y_width = yrange[1] - yrange[0]
    for i in range(len(properties)):
        coords = properties[i].coordinates
        if (
            coords[0] <= xrange[1] - x_width / 3
            and coords[0] >= xrange[0] + x_width / 3
            and coords[1] <= yrange[1] - y_width / 3
            and coords[1] >= yrange[0] + y_width / 3
            and properties[i].type == "farm"
        ):
            # seed this property
            seed_property = i
            break

    p = properties[seed_property]
    # TODO technically, to encapsulate this better, there should a function that allows you to infect a specific animal(s), and that will then update infection_status, prop_infections, cumulative_infections, and exposure_date, and anything else that may need to be updated
    p.infection_status = 1
    p.exposure_date = premises.convert_time_to_date(time)
    p.animals[seed_animal].status = "infected"
    p.prop_infectious = 1 / p.size
    p.cumulative_infections = 1

    return properties, seed_property


def initialise_infection_vaccination(properties, n, xrange, yrange, init_vax_probability, time=0):
    """Randomly seeds an infection in the map, and also implements any initial vaccination (though, initial vaccination is not relevant for Lumpy Skin Disease in Australia)"""

    # seed infection (in the center third)
    properties, seed_property = seed_infection(xrange, yrange, properties)

    # initialise list of cumulative infections from each property - calculated for FOI every loop
    cumulative_infection_proportions = list(np.zeros(n))
    cumulative_infection_proportions[seed_property] = (
        properties[seed_property].cumulative_infections / properties[seed_property].size
    )

    # set up some random initial vaccination
    for i, premise in enumerate(properties):
        if premise.infection_status != 1:
            premise.vaccination(init_vax_probability, properties, time, culled_neighbours_only=False)

    return properties, seed_property, cumulative_infection_proportions


def plot_current_state(
    properties,
    time,
    xlims,
    ylims,
    folder_path,
    controlzone,
    infectionpoly=False,
    contacts_for_plotting={},
):
    """Plots the map for the "apparent" state (known be decision-makers) and the true underlying state (includes undetected infected properties)"""

    output.plot_map(
        properties,
        time,
        xlims=xlims,
        ylims=ylims,
        folder_path=folder_path,
        real_situation=True,
        controlzone=controlzone,
        infectionpoly=infectionpoly,
        contacts_for_plotting={},  # contacts_for_plotting,  # hiding the contacts for plotting, to make things look clearer,,,, TODO in the real situation, these should be the actual movements, or something
    )
    output.plot_map(
        properties,
        time,
        xlims=xlims,
        ylims=ylims,
        folder_path=folder_path,
        real_situation=False,
        controlzone=controlzone,
        infectionpoly=infectionpoly,
        contacts_for_plotting={},  # contacts_for_plotting, # not plotting them to make it easier to see what's happening...
    )


def save_reports(
    properties,
    folder_path,
    total_culled_animals,
    combined_narrative,
    report,
    contact_tracing_reports,
    testing_reports,
    movement_records,
):
    """Saves the text reports of management action and outcomes"""
    total_culled = 0
    total_vaccinated = 0
    for premise in properties:
        if premise.culled_status:
            total_culled += 1
        if premise.vaccination_status:
            total_vaccinated += 1

    to_save_narrative = (
        combined_narrative
        + f"\n==============\nTotal culled properties: {total_culled}; total vaccinated properties: {total_vaccinated}; total culled animals: {total_culled_animals}"
    )

    # output "reports" report
    with open(os.path.join(folder_path, "report.txt"), "w") as file:
        file.write(report)

    # output contact tracing reports
    with open(os.path.join(folder_path, "report_contact_tracing.txt"), "w") as file:
        file.write(contact_tracing_reports)

    # output testing reports
    with open(os.path.join(folder_path, "report_testing.txt"), "w") as file:
        file.write(testing_reports)

    # output the inter-twined narrative (of known occurences)
    with open(os.path.join(folder_path, "report_combined_narrative.txt"), "w") as file:
        file.write(to_save_narrative)

    # write movement records
    animal_movement.save_movement_record(folder_path, movement_records)


def save_current_state(properties, time, folder_path, unique_output):

    to_save = properties

    with open(os.path.join(folder_path, "properties_" + str(time)), "wb") as file:
        pickle.dump(to_save, file)

    # print output: all
    header = [
        "id",
        "status",
        "ip",
        "exposure_date",
        "clinical_date",
        "notification_date",
        "removal_date",
        "recovery_date",
        "vacc_date",
        "region",
        "county",
        "cluster",
        "xcoord",
        "ycoord",
        "area",
        "type",
        "total",
    ]
    file = os.path.join(folder_path, f"fake_data_underlying_{unique_output}.csv")
    with open(file, "w", newline="") as f:

        # create the csv writer
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

        for premise in properties:
            row = premise.return_output_row()
            writer.writerow(row)

    # print output: known
    file = os.path.join(folder_path, f"fake_data_apparent_{unique_output}.csv")
    with open(file, "w", newline="") as f:

        # create the csv writer
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

        for premise in properties:
            row = premise.return_known_output_row()
            writer.writerow(row)

    # print output: known for RTM
    header = [
        "id",
        "status",
        "clinical_date",
        "notification_date",
        "recovery_date",
        "removal_date",
        "vacc_date",
        "longitude",
        "latitude",
        "area_h",
        "n_total",
    ]
    file = os.path.join(folder_path, f"fake_data_apparent_RTM_{unique_output}.csv")
    with open(file, "w", newline="") as f:

        # create the csv writer
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

        for premise in properties:
            row = premise.return_known_output_row(RTM=True)
            writer.writerow(row)


def save_outbreak_state(
    properties,
    time,
    folder_path,
    unique_output,
    total_culled_animals,
    movement_records,
    job_manager,
):

    # saves properties
    save_current_state(properties, time, folder_path, unique_output)

    # to save everything else
    to_save = [total_culled_animals, movement_records, job_manager]
    with open(os.path.join(folder_path, "outbreak_state_other_" + str(time)), "wb") as file:
        pickle.dump(to_save, file)
