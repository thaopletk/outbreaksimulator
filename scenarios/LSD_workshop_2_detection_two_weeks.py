"""Simulated lumpy skin disease outbreak

Runs detection and initial two week spread

submit as:
python LSD_workshop_2_detection_two_weeks.py initialspreadseed twoweeks_version

initialspreadseed = sys.argv[1]  # the version from 1_initial_spread
twoweeks_version = int(sys.argv[2]) # controls RNG for the detection+two weeks spread

"""

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

folder_path_main = os.path.join(os.path.dirname(__file__), "LSD_workshop")


with open(os.path.join(folder_path_main, f"spatial_only_parameters.json"), "r") as file:
    spatial_only_parameters = json.load(file)
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

version = sys.argv[1]  # the version from 1_initial_spread
unique_output = f"02_undetected_spread_{version}"
folder_path_undetected_spread = os.path.join(folder_path_main, unique_output)
undetected_spread_properties_filename = os.path.join(folder_path_undetected_spread, "properties_" + unique_output)
undetected_spread_diseaseoutbreak_filename = os.path.join(folder_path_undetected_spread, "outbreakobject_" + unique_output)

with open(undetected_spread_properties_filename, "rb") as file:
    properties = pickle.load(file)
with open(undetected_spread_diseaseoutbreak_filename, "rb") as file:
    diseaseoutbreak = pickle.load(file)


# Step 5: trigger the first report in northern NSW and initial actions
# the early time processes
# start the default processes (contact tracing, assume that clinical confirmation is immediate, lab testing in process). Management jobs are stored in a job manager object. The day will probably end with minimal movement restrictions for the infected property and the contact traced properties.
# These properties should shown on a map


random.seed(10 * int(sys.argv[2]))
np.random.seed(10 * int(sys.argv[2]))

unique_output = f"{version}_03_outbreak_detection_{sys.argv[2]}"
folder_path_first_report = os.path.join(folder_path_main, unique_output)

if not os.path.exists(folder_path_first_report):
    os.makedirs(folder_path_first_report)

spread_properties_filename = os.path.join(folder_path_first_report, "properties_" + unique_output)
spread_diseaseoutbreak_filename = os.path.join(folder_path_first_report, "outbreakobject_" + unique_output)

if not os.path.exists(spread_properties_filename) or not os.path.exists(spread_diseaseoutbreak_filename):
    # adjust the plotting parameters for this new scenario
    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path_first_report,
        unique_output=unique_output,
    )

    first_detection_day = diseaseoutbreak.time + 1

    # print(diseaseoutbreak.job_manager.jobs_queue)

    properties, movement_records, time, total_culled_animals, job_manager = diseaseoutbreak.simulate_first_two_days(
        properties, reportingregion_x, reportingregion_y
    )

    # and then resave the end state
    with open(spread_properties_filename, "wb") as file:
        pickle.dump(properties, file)

    # and save the diseaseoutbreak object
    with open(spread_diseaseoutbreak_filename, "wb") as file:
        pickle.dump(diseaseoutbreak, file)
else:
    with open(spread_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(spread_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)

# step 6
# about two weeks of simulation
unique_output = f"{version}_04_two_weeks_{sys.argv[2]}"
folder_path = os.path.join(folder_path_main, unique_output)
days_to_run_for = 14

if not os.path.exists(folder_path):
    os.makedirs(folder_path)

spread_properties_filename = os.path.join(folder_path, "properties_" + unique_output)
spread_diseaseoutbreak_filename = os.path.join(folder_path, "outbreakobject_" + unique_output)

outbreak_step_6_filenames = [
    [spread_properties_filename, spread_diseaseoutbreak_filename, unique_output],
]


if not os.path.exists(spread_properties_filename) or not os.path.exists(spread_diseaseoutbreak_filename):
    # adjust the plotting parameters for this new scenario
    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path,
        unique_output=unique_output,
    )

    # TODO not 100% satisfactorily complete
    properties, movement_records, time, total_culled_animals, job_manager = diseaseoutbreak.simulate_outbreak_management(
        properties, days_to_run_for, resource_setting="default"
    )

    # and then resave the end state
    with open(spread_properties_filename, "wb") as file:
        pickle.dump(properties, file)

    # and save the diseaseoutbreak object
    with open(spread_diseaseoutbreak_filename, "wb") as file:
        pickle.dump(diseaseoutbreak, file)

    total_infected = 0
    for property_i in properties:
        if property_i.exposure_date != "NA":
            total_infected += 1

    print(f"Total number of infected premises: {total_infected}")

# else:
#     with open(spread_properties_filename, "rb") as file:
#         properties = pickle.load(file)
#     with open(spread_diseaseoutbreak_filename, "rb") as file:
#         diseaseoutbreak = pickle.load(file)
