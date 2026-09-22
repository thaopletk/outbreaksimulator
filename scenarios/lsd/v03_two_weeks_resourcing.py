""" v0.3 Trial

This script controls and run different elements and steps, testing the expanded version of the code post v0.2 


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

folder_path_main = os.path.join(os.path.dirname(__file__), "outputs", "v03_trial")

small_ver = ""
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

undetected_version = sys.argv[1]  # the undetected spread version
twoweeks_version = sys.argv[2]  # version for outbreak detection and two weeks of spread
local_ver = sys.argv[3]
resource_setting = sys.argv[4]  # high or low

random.seed(10 * int(local_ver))
np.random.seed(10 * int(local_ver))

# step 6 components
# about two weeks of simulation
unique_output = f"{undetected_version}_04_two_weeks_{twoweeks_version}"
folder_path = os.path.join(folder_path_main, unique_output)
spread_properties_filename = os.path.join(folder_path, "properties_" + unique_output)
spread_diseaseoutbreak_filename = os.path.join(folder_path, "outbreakobject_" + unique_output)
outbreak_step_6_filenames = [
    [spread_properties_filename, spread_diseaseoutbreak_filename, unique_output],
]


# function to make it easier to run specific "branches" of the simulator "history"
def run_specific_branch(
    local_properties_filename,
    local_diseaseoutbreak_filename,
    properties_filename,
    diseaseoutbreak_filename,
    folder_path_local,
    unique_output,
    management_parameters,
    days_to_run_for,
    resource_setting,
    vaccination=False,
):

    if not os.path.exists(local_properties_filename) or not os.path.exists(local_diseaseoutbreak_filename):

        with open(properties_filename, "rb") as file:
            properties = pickle.load(file)
        with open(diseaseoutbreak_filename, "rb") as file:
            diseaseoutbreak = pickle.load(file)

        # adjust the plotting parameters for this new scenario
        diseaseoutbreak.set_plotting_parameters(
            xlims=xlims,
            ylims=ylims,
            plotting=True,
            folder_path=folder_path_local,
            unique_output=unique_output,
        )

        properties, movement_records, time, total_culled_animals, job_manager = (
            diseaseoutbreak.simulate_outbreak_management(
                properties, management_parameters, days_to_run_for, resource_setting, vaccination
            )
        )

        # and then resave the end state
        with open(local_properties_filename, "wb") as file:
            pickle.dump(properties, file)

        # and save the diseaseoutbreak object
        with open(local_diseaseoutbreak_filename, "wb") as file:
            pickle.dump(diseaseoutbreak, file)

        total_infected = 0
        for property_i in properties:
            if property_i.exposure_date != "NA":
                total_infected += 1
        print(f"Total number of infected premises: {total_infected}")


# STEP 7: run some different options after decision-making
days_to_run_for = 14

outbreak_step_7_filenames = []

management_parameters = []  # dummy parameters because they're not actually used right now

for properties_filename, diseaseoutbreak_filename, identifier in outbreak_step_6_filenames:
    unique_output = f"{undetected_version}_{twoweeks_version}_05_two_weeks_{local_ver}_{resource_setting}"
    print(unique_output)

    folder_path_local = os.path.join(folder_path_main, unique_output)
    if not os.path.exists(folder_path_local):
        os.makedirs(folder_path_local)
    local_properties_filename = os.path.join(folder_path_local, "properties_" + unique_output)
    local_diseaseoutbreak_filename = os.path.join(folder_path_local, "outbreakobject_" + unique_output)

    outbreak_step_7_filenames.append(
        [local_properties_filename, local_diseaseoutbreak_filename, resource_setting]
    )  # note, have set identifier = resource_setting

    run_specific_branch(
        local_properties_filename,
        local_diseaseoutbreak_filename,
        properties_filename,
        diseaseoutbreak_filename,
        folder_path_local,
        unique_output,
        management_parameters,
        days_to_run_for,
        resource_setting,
    )
