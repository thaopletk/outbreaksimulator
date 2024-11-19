""" Main control

Aim: for this script to control and run different elements and steps needed for the trial simulation exercise.


"""

import sys
import os
import json
import pickle

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.simulator as simulator
import simulator.management as management

# folder names
folder_path_main = os.path.join(os.path.dirname(__file__), "trial_simex_v2")
folder_path_seed = os.path.join(folder_path_main, "01_seed")
folder_path_undetected_spread_1 = os.path.join(folder_path_main, "02_undetected_spread_one_week")

# step 1: make folder for everything
# Not in output folder, so that it'll be synced...

if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)


# step 2: initiate the full proper map, including with different property types
# parameters
with open(os.path.join(folder_path_main, "spatial_only_parameters.json"), "r") as file:
    spatial_only_paramaters = json.load(file)
with open(os.path.join(folder_path_main, "properties_specific_parameters.json"), "r") as file:
    properties_specific_parameters = json.load(file)

# properties_filename = os.path.join(folder_path_main, "properties_initialised.pickle")
properties_filename = os.path.join(folder_path_main, "properties_init")
if not os.path.exists(properties_filename):
    property_setup_info = simulator.trial_simex_property_setup(
        folder_path_main, spatial_only_paramaters, properties_specific_parameters
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


# limits for the figures
xlims = [
    round(spatial_only_paramaters["xrange"][0], 2) - 0.005,
    round(spatial_only_paramaters["xrange"][1], 2) + 0.005,
]
ylims = [
    round(spatial_only_paramaters["yrange"][0], 1) - 0.05,
    round(spatial_only_paramaters["yrange"][1], 1) + 0.05,
]


# step 3: force initial seeding of a property in/near the center (call it a "stud farm") and save
time = 0
if not os.path.exists(folder_path_seed):
    os.makedirs(folder_path_seed)

properties_seeded_filename = os.path.join(folder_path_seed, "properties_0")
if not os.path.exists(properties_seeded_filename):
    # seed property

    properties, seed_property = simulator.seed_infection_at_property_type(
        spatial_only_paramaters["xrange"], spatial_only_paramaters["yrange"], properties, "stud farm", time
    )

    # save new properties output figures and tables as necessary
    simulator.plot_current_state(
        properties,
        property_coordinates,
        time,
        xlims,
        ylims,
        folder_path_seed,
        controlzone={},
        infectionpoly=False,
        contacts_for_plotting={},
    )

    unique_output = "day0"
    simulator.save_current_state(properties, time, folder_path_seed, unique_output)
else:
    with open(properties_seeded_filename, "rb") as file:
        properties = pickle.load(file)


exit(0)

with open(os.path.join(folder_path_main, "scenario_params.json"), "r") as file:
    scenario_params = json.load(file)

with open(os.path.join(folder_path_main, "job_params.json"), "r") as file:
    job_params = json.load(file)


# step 4: run the simulation, including forcing some initial movements from that center seeded property (say, over 7 days).
if not os.path.exists(folder_path_undetected_spread_1):
    os.makedirs(folder_path_undetected_spread_1)
# to force some initial movements from that center seeded property, simply adjust some of its movement parameters
stud_farm_i = None
for i in range(len(properties)):
    if properties[i].type == "stud farm":
        stud_farm_i = i
        p = properties[i]
        p.movement_probability = 1
        p.movement_start_day = 1
        p.movement_frequency = 1
        p.max_daily_movements = 6
        break

if stud_farm_i == None:
    raise ValueError("Stud farm not found for some reason")

# run for one week (there shouldn't be any reporting - though if there is, we can force the probability of report down to zero)

stop_time = 3

# initiate various things that start from empty:
movement_records = []

unique_output = "02_undetected_spread_one_week"
properties, movement_records, time = simulator.simulate_outbreak_spread_only(
    time=time,
    stop_time=stop_time,
    movement_records=movement_records,
    plotting=True,
    folder_path=folder_path_undetected_spread_1,
    properties=properties,
    property_coordinates=property_coordinates,
    unique_output=unique_output,
    **set_up_params,
    **scenario_params
)

# total_culled_animals = 0
# local_movement_restrictions = []

# # initiate job_manager
# job_manager = management.JobManager(**job_params)

# simulator.simulate_outbreak_continue(
#     properties,
#     folder_path_undetected_spread_1,
#     stop_time,
#     unique_output,
#     total_culled_animals=total_culled_animals,
#     time=time,
#     movement_records=movement_records,
#     local_movement_restrictions=local_movement_restrictions,
#     job_manager=job_manager,
# )

# and then adjust those movements down after a week
p = properties[stud_farm_i]
p.movement_probability = set_up_params["movement_probability"]["farm"]
p.movement_frequency = set_up_params["movement_frequency"]["farm"]
p.max_daily_movements = set_up_params["max_daily_movements"]["farm"]

# Step 5: continue running simulation until the first detection (default contact tracing can be done, but before the next day which might have wide-scale management) and output


# then, management options: complete standstill, or standstill of certain radius

# run a few days, and then give options regarding ring surveillance, ring culling, ring testing...
