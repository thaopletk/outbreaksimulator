""" v0.3 Trial

This script controls and run different elements and steps, testing the expanded version of the code post v0.2 


"""

import sys
import os
import json
import pickle

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.simulator as simulator
import simulator.output as output
import simulator.disease_simulation as disease_simulation


folder_path_main = os.path.join(os.path.dirname(__file__), "outputs", "v03_trial")
folder_path_seed = os.path.join(folder_path_main, "01_seed")


# step 1: make main folder if it doesn't exist
if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)

# step 2: initiate the full proper map, including with different property types
# parameters
small_ver = "_small"
# small_ver = "" # for running on the cluster

with open(os.path.join(folder_path_main, f"spatial_only_parameters{small_ver}.json"), "r") as file:
    spatial_only_parameters = json.load(file)  # has the total number of properties, hence the {small_ver}
with open(os.path.join(folder_path_main, f"properties_specific_parameters.json"), "r") as file:
    properties_specific_parameters = json.load(file)
with open(os.path.join(folder_path_main, "job_parameters.json"), "r") as file:
    job_parameters = json.load(file)
with open(os.path.join(folder_path_main, "scenario_parameters.json"), "r") as file:
    scenario_parameters = json.load(file)


# limits for the figures
xlims = [
    round(spatial_only_parameters["xrange"][0], 2) - 0.005,
    round(spatial_only_parameters["xrange"][1], 2) + 0.005,
]
ylims = [
    round(spatial_only_parameters["yrange"][0], 1) - 0.05,
    round(spatial_only_parameters["yrange"][1], 1) + 0.05,
]

properties_filename = os.path.join(folder_path_main, "properties_init")
if not os.path.exists(properties_filename):
    property_setup_info = simulator.property_setup_v03(
        folder_path_main, spatial_only_parameters, properties_specific_parameters
    )

    (
        properties,
        property_coordinates,
        adjacency_matrix,
        neighbour_pairs,
        neighbourhoods,
        property_polygons,
        property_polygons_puffed,
        property_areas,
    ) = property_setup_info


else:
    # load properties
    with open(properties_filename, "rb") as file:
        properties = pickle.load(file)


# plot the neighbours (not wind-neighbours)
if not os.path.exists(os.path.join(folder_path_main, "map_underlying0.png")):
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


# step 3:  initial seeding of a property
# the initial seeding will occur in Northern Queensland
# COULD TODO: make seeding occur either near a major port
# to get something near major cities, I should get their lat/long positions, (either hard code or download something from ABS), and allow spread to a wind-radius around those cities.

time = 0
if not os.path.exists(folder_path_seed):
    os.makedirs(folder_path_seed)

# parameters
with open(os.path.join(folder_path_main, "disease_parameters.json"), "r") as file:
    disease_parameters = json.load(file)

properties_seeded_filename = os.path.join(folder_path_seed, "properties_0")

northQLDx = [141, 146]
northQLDy = [-17, -10]
if not os.path.exists(properties_seeded_filename):
    # seed property
    unique_output = "day0"

    properties, seed_property = simulator.seed_infection_within_bound(
        northQLDx,
        northQLDy,
        properties,
        time,
        xlims,
        ylims,
        folder_path_seed,
        unique_output,
        disease_parameters["latent_period"],
    )
    # seeds infection within bounds (northQLDx,northQLDy) and does some plotting and saving

else:
    with open(properties_seeded_filename, "rb") as file:
        properties = pickle.load(file)
