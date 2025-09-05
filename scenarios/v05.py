""" v0.5

    This script runs code to simulate an FMD outbreak seeded in Victoria

"""

import sys
import os
import json
import pickle
import random
import numpy as np
import subprocess


sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.simulator as simulator
import simulator.output as output
import simulator.disease_simulation as disease_simulation
import simulator.management as management
import simulator.premises as premises
import simulator.spatial_functions as spatial_functions
import simulator.spatial_setup as spatial_setup

folder_path_main = os.path.join(os.path.dirname(__file__), "v05")

# make main folder if it doesn't exist
if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)

# generate map and properties
# extension: generate a random map using, e.g., perlin noise

small_ver = "_small"  # for testing purposes
# small_ver = ""  # for running on the cluster


with open(os.path.join(folder_path_main, f"spatial_only_parameters{small_ver}.json"), "r") as file:
    spatial_only_parameters = json.load(file)  # has the total number of properties, hence the {small_ver}

# 1. Spatial-only, property-type-agnostic setup
spatial_only_filename = os.path.join(folder_path_main, "spatial_only_setup.pickle")
if not os.path.exists(spatial_only_filename):
    (
        property_coordinates,
        adjacency_matrix,
        neighbour_pairs,
        neighbourhoods,
        property_polygons,
        property_polygons_puffed,
        property_areas,
    ) = spatial_setup.generate_properties_with_land(
        spatial_only_parameters["n"],
        spatial_only_parameters["r_wind"],
        spatial_only_parameters["xrange"],
        spatial_only_parameters["yrange"],
        spatial_only_parameters["average_property_ha"],
    )

    output.plot_map_land(
        property_polygons,
        property_polygons_puffed,
        spatial_only_parameters["xrange"],
        spatial_only_parameters["yrange"],
        folder_path_main,
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
properties_filename = os.path.join(folder_path_main, "properties_init")

with open(os.path.join(folder_path_main, f"properties_specific_parameters.json"), "r") as file:
    properties_specific_parameters = json.load(file)


random.seed(1)
np.random.seed(1)

if not os.path.exists(properties_filename):
    # set up properties
    properties = simulator.property_specific_initialisation_animals(
        spatial_only_parameters,
        properties_specific_parameters,
        property_coordinates,
        property_areas,
        neighbourhoods,
        property_polygons,
        property_polygons_puffed,
    )

    with open(properties_filename, "wb") as file:
        pickle.dump(properties, file)

else:
    # load properties
    with open(properties_filename, "rb") as file:
        properties = pickle.load(file)


# limits for the figures
xlims = [
    round(spatial_only_parameters["xrange"][0], 2) - 0.005,
    round(spatial_only_parameters["xrange"][1], 2) + 0.005,
]
ylims = [
    round(spatial_only_parameters["yrange"][0], 1) - 0.05,
    round(spatial_only_parameters["yrange"][1], 1) + 0.05,
]


# plot the neighbours (not wind-neighbours)
if not os.path.exists(os.path.join(folder_path_main, "map_underlying_neighbours.png")):
    output.plot_map(
        properties,
        time=0,
        xlims=xlims,
        ylims=ylims,
        folder_path=folder_path_main,
        real_situation=True,
        controlzone=None,
        infectionpoly=False,
        contacts_for_plotting={},
        show_movement_neighbours=True,
    )


# plot the animal density
if not os.path.exists(os.path.join(folder_path_main, "animal_density.png")):
    output.plot_animal_density(properties, xlims, ylims, folder_path=folder_path_main)


# seed infection
time = 0

folder_path_seed = os.path.join(folder_path_main, "01_seed")
if not os.path.exists(folder_path_seed):
    os.makedirs(folder_path_seed)

# parameters
with open(os.path.join(folder_path_main, "disease_parameters.json"), "r") as file:
    disease_parameters = json.load(file)

properties_seeded_filename = os.path.join(folder_path_seed, "properties_0")

northVICx = [141, 147]
northVICy = [-37, -34]


random.seed(52)
np.random.seed(23)
if not os.path.exists(properties_seeded_filename):
    # seed property
    unique_output = "day0"
    properties, seed_property = simulator.seed_infection_within_bound(
        northVICx,
        northVICy,
        properties,
        time,
        xlims,
        ylims,
        folder_path_seed,
        unique_output,
        None,  # disease_parameters["latent_period"],
        disease_parameters,
    )
    # seeds infection within bounds (QLDx,QLDy) and does some plotting and saving

else:
    with open(properties_seeded_filename, "rb") as file:
        properties = pickle.load(file)


# area for first report Victoria
reportingregion_x = [141, 150]
reportingregion_y = [-40, -34]
