""" Main control

Aim: for this script to control and run different elements and steps needed for the trial simulation exercise.


"""

import sys
import os
import json
import pickle

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.simulator as simulator


# folder names
folder_path_main = os.path.join(os.path.dirname(__file__), "trial_simex")
folder_path_seed = os.path.join(os.path.dirname(__file__), "trial_simex", "01_seed")

# step 1: make folder for everything
# Not in output folder, so that it'll be synced...

if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)


# read in parameters
with open(os.path.join(folder_path_main, "trial_setup_parameters.json"), "r") as file:
    set_up_params = json.load(file)

with open(os.path.join(folder_path_main, "scenario_params.json"), "r") as file:
    scenario_params = json.load(file)

# step 2: initiate the full proper map, including with different property types

properties_filename = os.path.join(folder_path_main, "properties_initialised.pickle")
if not os.path.exists(properties_filename):
    property_setup_info = simulator.property_setup(folder_path_main, **set_up_params)
else:
    # load properties
    with open(properties_filename, "rb") as file:
        property_setup_info = pickle.load(file)


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


# step 3: force initial seeding of a property in/near the center (call it a "stud farm") and save
if not os.path.exists(folder_path_seed):
    os.makedirs(folder_path_seed)

# seed property

properties, seed_property = simulator.seed_infection(
    set_up_params["xrange"], set_up_params["yrange"], properties
)

# rename property as the stud farm
premises = properties[seed_property]
premises.type = "stud farm"

# save new properties output figures and tables as necessary

# limits for the figures
xlims = [
    round(set_up_params["xrange"][0], 2) - 0.005,
    round(set_up_params["xrange"][1], 2) + 0.005,
]
ylims = [
    round(set_up_params["yrange"][0], 1) - 0.05,
    round(set_up_params["yrange"][1], 1) + 0.05,
]

time = 0
controlzone = {}

simulator.plot_current_state(
    properties,
    property_coordinates,
    time,
    xlims,
    ylims,
    folder_path_seed,
    controlzone,
    infectionpoly=False,
    contacts_for_plotting={},
)

unique_output = "day0"
simulator.save_current_state(properties, time, folder_path_seed, unique_output)

# step 5: and force some initial movements from that center seeded property (say, over 7 days)

# step 6: run that simulation and stop after the first detection (default contact tracing can be done, but before the next day which might have wide-scale management)

# then, management options: complete standstill, or standstill of certain radius

# run a few days, and then give options regarding ring surveillance, ring culling, ring testing...
