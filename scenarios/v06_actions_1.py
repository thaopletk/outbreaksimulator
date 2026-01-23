import os
import sys
import json
import pickle
import random
import numpy as np

# import subprocess
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import simulator.fixed_spatial_setup as fixed_spatial_setup
import simulator.HPAI_functions as HPAI_functions
import simulator.output as output

# import simulator.simulator as simulator
import simulator.disease_simulation as disease_simulation

###################################################
# ---- Code run set up ---------------------------#
###################################################

# Boundaries for NSW
xrange = [136, 155]
yrange = [-40, -26]

# limits for the figures
xlims = [
    round(xrange[0], 2) - 0.005,
    round(xrange[1], 2) + 0.005,
]
ylims = [
    round(yrange[0], 1) - 0.05,
    round(yrange[1], 1) + 0.05,
]

folder_path_main = os.path.join(os.path.dirname(__file__), "v06")

suffix = ""
testing = True  # TODO: adjust this if running the true simulation / vs testing sims
if testing:
    suffix = "_test"


###################################################
# ---- Previous output files ---------------------#
###################################################

unique_output = "03_outbreak_detection"
folder_path_first_report = os.path.join(folder_path_main, unique_output)

spread_properties_filename = os.path.join(folder_path_first_report, "properties_" + unique_output)
spread_diseaseoutbreak_filename = os.path.join(folder_path_first_report, "outbreakobject_" + unique_output)

with open(spread_properties_filename, "rb") as file:
    properties = pickle.load(file)
with open(spread_diseaseoutbreak_filename, "rb") as file:
    diseaseoutbreak = pickle.load(file)


###################################################
# ---- Run first set of actions ------------------#
###################################################

# TODOs: need to be able to read in things....!

# # Step 1: generate a list of scheduled management actions
# # actions, basic: date, property_id, action-to-take-on-date, extra deets for action if necessary (e.g., if culling, the number of animals culled on that day)

actions_input = os.path.join(folder_path_main, f"actions_1.xlsx")
property_jobs = pd.read_excel(actions_input, sheet_name="jobs")
property_based_zones = pd.read_excel(
    actions_input, sheet_name="zones"
)  # could consider "expanding to SAL, LGA" or something like that
days_to_run_for = 3

unique_output = f"04_actioning_actions_1"
folder_path = os.path.join(folder_path_main, unique_output)

if not os.path.exists(folder_path):
    os.makedirs(folder_path)

spread_properties_filename = os.path.join(folder_path, "properties_" + unique_output)
spread_diseaseoutbreak_filename = os.path.join(folder_path, "outbreakobject_" + unique_output)

if not os.path.exists(spread_properties_filename) or not os.path.exists(spread_diseaseoutbreak_filename):
    # adjust the plotting parameters for this new scenario
    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path,
        unique_output=unique_output,
    )

    # TODO
    properties, movement_records, time, total_culled_animals, job_manager = (
        diseaseoutbreak.simulate_HPAI_outbreak_management(
            properties, property_jobs, property_based_zones, days_to_run_for
        )
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
