import sys
import os
import json
import pickle
import random
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.simulator as simulator
import simulator.output as output
import simulator.disease_simulation as disease_simulation
import simulator.management as management
import simulator.premises as premises
import simulator.spatial_functions as spatial_functions

folder_path_main = os.path.join(os.path.dirname(__file__), "outputs", "v03_trial")
folder_path_seed = os.path.join(folder_path_main, "01_seed")

# step 1: make main folder if it doesn't exist
if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)

# step 2: initiate the full proper map, including with different property types
# parameters
# small_ver = "_small"
small_ver = ""  # for running on the cluster

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

# area for first report
reportingregion_x = [140, 155]
reportingregion_y = [-32, -29]

properties_filename = os.path.join(folder_path_main, "properties_init")

# load properties
with open(properties_filename, "rb") as file:
    properties = pickle.load(file)


# plot the animal density
output.plot_animal_density(properties, xlims, ylims, folder_path=folder_path_main)
