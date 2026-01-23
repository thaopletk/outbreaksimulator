""" v06 | Script for running simulations for HASTE NSW HPAI simulation

"""

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

# import simulator.management as management
# import simulator.premises as premises
# import simulator.spatial_functions as spatial_functions
# import simulator.spatial_setup as spatial_setup

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
# make main folder if it doesn't exist
if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)

suffix = ""
testing = True  # TODO: adjust this if running the true simulation / vs testing sims
if testing:
    suffix = "_test"

###################################################
# ---- Set up properties and locations -----------#
###################################################

# generates locations for properties, and makes them into property objects  (which contain information about what type of premises it is)
output_filename = os.path.join(folder_path_main, f"HPAI_NSW_setup_locations{suffix}")
if not os.path.exists(output_filename):
    (
        all_properties,
        chicken_meat_property_coordinates,
        processing_chicken_meat_property_coordinates,
        chicken_egg_property_coordinates,
        processing_chicken_egg_property_coordinates,
    ) = fixed_spatial_setup.HPAI_NSW_setup_locations(output_filename, testing)
else:
    with open(output_filename, "rb") as file:
        (
            all_properties,
            chicken_meat_property_coordinates,
            processing_chicken_meat_property_coordinates,
            chicken_egg_property_coordinates,
            processing_chicken_egg_property_coordinates,
        ) = pickle.load(file)

print(f"total facilities started: {len(all_properties)}")

# for p in all_properties:
#     print(p)

fixed_spatial_setup.save_chicken_property_csv(all_properties, 0, folder_path_main, suffix)

# plot that actually shows the locations of different facilities
fixed_spatial_setup.plot_map_land_HPAI(
    chicken_meat_property_coordinates,
    processing_chicken_meat_property_coordinates,
    chicken_egg_property_coordinates,
    processing_chicken_egg_property_coordinates,
    xrange,
    yrange,
    folder_path_main,
    plot_suffix=suffix,
)

fixed_spatial_setup.plot_map_land_HPAI_2(
    all_properties,
    xrange,
    yrange,
    folder_path_main,
    plot_suffix=suffix,
)

HPAI_functions.save_approx_known_data(all_properties, folder_path_main, suffix)

properties_filename = os.path.join(folder_path_main, f"HPAI_properties{suffix}")
if not os.path.exists(properties_filename):

    properties = fixed_spatial_setup.HPAI_movement_network_setup(
        all_properties,
        max_movement_km=500,  # 500km max movement
    )

    with open(properties_filename, "wb") as file:
        pickle.dump(properties, file)
else:
    with open(properties_filename, "rb") as file:
        properties = pickle.load(file)

# plot the neighbours (not wind-neighbours)
if not os.path.exists(os.path.join(folder_path_main, f"map_underlying0{suffix}_neighbours.png")):
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
        save_suffix=suffix + "_neighbours",
    )

# plot the animal density
if not os.path.exists(os.path.join(folder_path_main, f"animal_density{suffix}.png")):
    output.plot_animal_density(
        properties, xlims, ylims, folder_path=folder_path_main, file_name=f"animal_density{suffix}.png"
    )


###################################################
# ---- Seed the first infection ------------------#
###################################################

time = 0

folder_path_seed = os.path.join(folder_path_main, "01_seed")
if not os.path.exists(folder_path_seed):
    os.makedirs(folder_path_seed)

# parameters
with open(os.path.join(folder_path_main, "disease_parameters.json"), "r") as file:
    disease_parameters = json.load(file)

properties_seeded_filename = os.path.join(folder_path_seed, f"properties_0{suffix}")

seedlocationx = xrange
seedlocationy = yrange

random.seed(52)
np.random.seed(23)
if not os.path.exists(properties_seeded_filename):
    # seed property
    unique_output = "day0"
    properties, seed_property = HPAI_functions.seed_HPAI_infection(
        seedlocationx,
        seedlocationy,
        properties,
        time,
        xlims,
        ylims,
        folder_path_seed,
        unique_output,
        None,  # disease_parameters["latent_period"],
        disease_parameters,
    )
else:
    with open(properties_seeded_filename, "rb") as file:
        properties = pickle.load(file)


###################################################
# ---- Undetected spread -------------------------#
###################################################
# spread and then detection after a fixed number of properties infected...

random.seed(5)
np.random.seed(5)
minimum_spread_time = 7
target_infected_properties = 5

# area for first report - anywhere for now
reportingregion_x = xrange
reportingregion_y = yrange


unique_output = f"02_undetected_spread"
folder_path_undetected_spread = os.path.join(folder_path_main, unique_output)
if not os.path.exists(folder_path_undetected_spread):
    os.makedirs(folder_path_undetected_spread)

undetected_spread_properties_filename = os.path.join(folder_path_undetected_spread, "properties_" + unique_output)
undetected_spread_diseaseoutbreak_filename = os.path.join(
    folder_path_undetected_spread, "outbreakobject_" + unique_output
)


with open(os.path.join(folder_path_main, f"spatial_only_parameters.json"), "r") as file:
    spatial_only_parameters = json.load(file)
with open(os.path.join(folder_path_main, "job_parameters.json"), "r") as file:
    job_parameters = json.load(file)
with open(os.path.join(folder_path_main, "scenario_parameters.json"), "r") as file:
    scenario_parameters = json.load(file)


spatial_only_parameters["n"] = len(properties)

if not os.path.exists(undetected_spread_properties_filename) or not os.path.exists(
    undetected_spread_diseaseoutbreak_filename
):

    # initiate various things that start from empty:
    diseaseoutbreak = disease_simulation.DiseaseSimulation(
        time=time,
        disease_parameters=disease_parameters,
        spatial_only_parameters=spatial_only_parameters,
        job_parameters=job_parameters,
        scenario_parameters=scenario_parameters,
    )

    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path_undetected_spread,
        unique_output=unique_output,
    )

    print(diseaseoutbreak.job_manager.jobs_queue)

    properties, movement_records, time = diseaseoutbreak.simulate_outbreak_spread_only(
        properties=properties,
        time=time,
        stop_time=minimum_spread_time,
        reporting_region_check=[reportingregion_x, reportingregion_y],
        min_infected_premises=target_infected_properties,
        outbreak_sim="HPAI",
    )

    first_detection_day = time + 1

    # and then resave the end state
    with open(undetected_spread_properties_filename, "wb") as file:
        pickle.dump(properties, file)

    # and save the diseaseoutbreak object
    with open(undetected_spread_diseaseoutbreak_filename, "wb") as file:
        pickle.dump(diseaseoutbreak, file)

    total_infected = 0
    for property_i in properties:
        if property_i.exposure_date != "NA":
            total_infected += 1

    print(f"Total number of infected premises: {total_infected}")

else:
    with open(undetected_spread_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(undetected_spread_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)

HPAI_functions.save_approx_known_data(properties, folder_path_undetected_spread, unique_output)

###################################################
# ---- Trigger first report ----------------------#
###################################################

# trigger first report and stop / output
unique_output = "03_outbreak_detection"
folder_path_first_report = os.path.join(folder_path_main, unique_output)

if not os.path.exists(folder_path_first_report):
    os.makedirs(folder_path_first_report)

spread_properties_filename = os.path.join(folder_path_first_report, "properties_" + unique_output)
spread_diseaseoutbreak_filename = os.path.join(folder_path_first_report, "outbreakobject_" + unique_output)

random.seed(15)
np.random.seed(16)
if not os.path.exists(spread_properties_filename) or not os.path.exists(spread_diseaseoutbreak_filename):

    # adjust the plotting parameters for this new scenario
    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path_first_report,
        unique_output=unique_output,
    )

    properties, movement_records, time, total_culled_animals, job_manager = diseaseoutbreak.simulate_first_report(
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

HPAI_functions.save_approx_known_data(properties, folder_path_first_report, unique_output)
