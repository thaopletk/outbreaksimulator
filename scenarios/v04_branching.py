""" v0.4 branching

    Runs the alternative histories given the different decisions


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

folder_path_main = os.path.join(os.path.dirname(__file__), "v04")

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

decision_ver = sys.argv[1]
# values: "cullingfocused", "vaccinationfocused", "surveillancefocused"

local_ver = sys.argv[2]  # for running an array of simulations
resource_setting = "default"  # keeping the same resource setting


random.seed(10 * int(local_ver))
np.random.seed(10 * int(local_ver))

# obtaining the previous step's file
unique_output = f"04_to_decision_point"
folder_path = os.path.join(folder_path_main, unique_output)
spread_properties_filename = os.path.join(folder_path, "properties_" + unique_output)
spread_diseaseoutbreak_filename = os.path.join(folder_path, "outbreakobject_" + unique_output)
previous_step_filenames = [
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
    decision_ver,
    vaccination=True,  # I can just vaccinate for all of them anyway
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

        # new_job_manager = management.JobManager(spatial_only_parameters["n"], **job_parameters)
        # new_job_manager.jobs_queue = diseaseoutbreak.job_manager.jobs_queue
        # new_job_manager.local_movement_restrictions = diseaseoutbreak.job_manager.local_movement_restrictions
        # diseaseoutbreak.job_manager = new_job_manager

        properties, movement_records, time, total_culled_animals, job_manager = (
            diseaseoutbreak.simulate_outbreak_management(
                properties,
                management_parameters,
                days_to_run_for,
                resource_setting,
                vaccination=vaccination,
                decision=decision_ver,
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


days_to_run_for = 4 * 7
management_parameters = []

for properties_filename, diseaseoutbreak_filename, identifier in previous_step_filenames:
    unique_output = f"05_after_decision_{decision_ver}_{local_ver}"
    print(unique_output)

    folder_path_local = os.path.join(folder_path_main, unique_output)
    if not os.path.exists(folder_path_local):
        os.makedirs(folder_path_local)
    local_properties_filename = os.path.join(folder_path_local, "properties_" + unique_output)
    local_diseaseoutbreak_filename = os.path.join(folder_path_local, "outbreakobject_" + unique_output)

    # outbreak_step_7_filenames.append(
    #     [local_properties_filename, local_diseaseoutbreak_filename, resource_setting]
    # )  # note, have set identifier = resource_setting

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
        decision_ver,
        vaccination=True,
    )
