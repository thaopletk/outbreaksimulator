"""vFMDVic | Script for running simulations for an FMD outbreak in Victoria"""

import os
import sys
import json
import pickle
import random
import numpy as np
import shutil
import time
import geopandas as gpd

# import subprocess
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import simulator.fixed_spatial_setup as fixed_spatial_setup
import simulator.HPAI_functions as HPAI_functions
import simulator.output as output
import simulator.auto_job_mode as auto_job_mode
import simulator.spatial_setup as spatial_setup
import simulator.FMD_functions as FMD_functions

# import simulator.simulator as simulator
import simulator.disease_simulation as disease_simulation
import simulator.management as management

# import simulator.management as management
import simulator.premises as premises

import v06_functions


def x_y_ranges(state="VIC"):
    if state == "NSW":
        # Boundaries for NSW
        xrange = [140, 155]
        yrange = [-38, -28]
    elif state == "QLD":
        # Boundaries for QLD
        xrange = [140, 155]
        yrange = [-30, -10]
    elif state == "VIC":
        xrange = [140.0, 151.0]
        yrange = [-39.5, -33.5]
    else:
        raise ValueError(f"{state} state not expected")

    # limits for the figures
    xlims = [
        round(xrange[0], 2) - 0.005,
        round(xrange[1], 2) + 0.005,
    ]
    ylims = [
        round(yrange[0], 1) - 0.05,
        round(yrange[1], 1) + 0.05,
    ]

    return xrange, yrange, xlims, ylims


###################################################
# ---- Code run set up ---------------------------#
###################################################

state = "VIC"
xrange, yrange, xlims, ylims = x_y_ranges(state)
wind_radius = 20
create_download_folder = False
download_parent_folder = None

folder_path_main = os.path.join(os.path.dirname(__file__), f"vFMD{state}")

###################################################
# ---- Set up properties and locations -----------#
###################################################

# generates locations for properties, and makes them into property objects  (which contain information about what type of premises it is)
output_filename = os.path.join(folder_path_main, f"FMD_{state}_setup_locations")


if not os.path.exists(output_filename):
    start_time = time.time()
    if state == "VIC":
        (
            ALL_coordinates,
            ALL_p_polygon,
            ALL_p_area,
            ALL_wind_radius,
            ALL_animal_type,
            ALL_premises_type,
            ALL_num_animals,
            ALL_LGAs,
            ALL_extra_info,
            beef_coordinates,
            sheep_coordinates,
            dairy_coordinates,
            pigs_coordinates,
            facility_coordinates,
            other_coordinates,
        ) = fixed_spatial_setup.FMD_VIC_setup_locations(
            output_filename,
            wind_radius=wind_radius,
        )

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Execution time of fixed_spatial_setup.FMD_{state}_setup_locations(): {execution_time/60} minutes")

else:
    if state == "VIC":
        with open(output_filename, "rb") as file:
            (
                ALL_coordinates,
                ALL_p_polygon,
                ALL_p_area,
                ALL_wind_radius,
                ALL_animal_type,
                ALL_premises_type,
                ALL_num_animals,
                ALL_LGAs,
                ALL_extra_info,
                beef_coordinates,
                sheep_coordinates,
                dairy_coordinates,
                pigs_coordinates,
                facility_coordinates,
                other_coordinates,
            ) = pickle.load(file)


# plot that actually shows the locations of different facilities (aside from backyard ones at the moment)
if not os.path.exists(os.path.join(folder_path_main, f"property_locations_base_map.png")):
    fixed_spatial_setup.plot_map_land_FMD(
        beef_coordinates,
        sheep_coordinates,
        dairy_coordinates,
        pigs_coordinates,
        facility_coordinates,
        other_coordinates,
        xrange,
        yrange,
        folder_path_main,
        plot_suffix="",
    )

output_filename = os.path.join(folder_path_main, f"FMD_{state}_all_properties")
if not os.path.exists(output_filename):
    start_time = time.time()
    all_properties = fixed_spatial_setup.initialise_all_properties(
        ALL_coordinates,
        ALL_p_polygon,
        ALL_p_area,
        ALL_wind_radius,
        ALL_animal_type,
        ALL_premises_type,
        ALL_num_animals,
        ALL_LGAs,
        output_filename,
        ALL_extra_info=ALL_extra_info,
    )
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Execution time of fixed_spatial_setup.initialise_all_properties(): {execution_time/60} minutes")
else:
    with open(output_filename, "rb") as file:
        all_properties = pickle.load(file)

print(f"total facilities started: {len(all_properties)}")

if not os.path.exists(os.path.join(folder_path_main, f"data_underlying.csv")):
    fixed_spatial_setup.save_FMD_property_csv(all_properties, 0, folder_path_main, "")

if not os.path.exists(os.path.join(folder_path_main, f"property_locations_base_map_types.png")):
    fixed_spatial_setup.plot_map_land_HPAI_2(
        all_properties,
        xrange,
        yrange,
        folder_path_main,
        plot_suffix="",
        property_type_list=[
            "beef extensive",
            "beef intensive",
            "feedlot",
            "mixed beef",
            "mixed sheep",
            "dairy",
            "pigs small",
            "pigs large",
            "sheep",
            "smallholder",
            "abattoir",
            "saleyard",
            "export_facility",
            "milk_processing",
        ],
    )


if not os.path.exists(os.path.join(folder_path_main, f"approx_known_data_.csv")):
    FMD_functions.save_approx_known_data(all_properties, folder_path_main, "")

properties_filename = os.path.join(folder_path_main, f"FMD_{state}_properties")
if not os.path.exists(properties_filename):

    start_time = time.time()

    properties = fixed_spatial_setup.FMD_movement_network_setup(
        all_properties,
        max_movement_km=200,  # 200km max movement
        state=state,
    )

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Execution time of fixed_spatial_setup.FMD_movement_network_setup(): {execution_time/60} minutes")

    with open(properties_filename, "wb") as file:
        pickle.dump(properties, file)
else:
    with open(properties_filename, "rb") as file:
        properties = pickle.load(file)

# TAKES WAY TOO LONG is there a way for this to take less time?
# # plot the neighbours (not wind-neighbours)
# if not os.path.exists(os.path.join(folder_path_main, f"map_underlying0_neighbours.png")):
#     output.plot_map(
#         properties,
#         time=0,
#         xlims=xlims,
#         ylims=ylims,
#         folder_path=folder_path_main,
#         real_situation=True,
#         controlzone=None,
#         infectionpoly=False,
#         contacts_for_plotting={},
#         show_movement_neighbours=True,
#         save_suffix="_neighbours",
#     )


trucks_df = FMD_functions.construct_trucks(properties)
trucks_df.to_csv(os.path.join(folder_path_main, f"trucks_df_.csv"))

exit(1)

###################################################
# ---- "Burn in" movement -------------------------#
###################################################

start_time = 0

random.seed(10)
np.random.seed(10)
burn_in_time = 1
minimum_spread_time = start_time + burn_in_time
target_infected_properties = 0

unique_output = f"0_burn_in_movement"
folder_path_burn_in_movement = os.path.join(folder_path_main, unique_output)
if not os.path.exists(folder_path_burn_in_movement):
    os.makedirs(folder_path_burn_in_movement)

initial_movement_properties_filename = os.path.join(folder_path_burn_in_movement, "properties_" + unique_output)
initial_movement_diseaseoutbreak_filename = os.path.join(folder_path_burn_in_movement, "outbreakobject_" + unique_output)
initial_movement_trucks_filename = os.path.join(folder_path_burn_in_movement, "trucks_df_" + unique_output)

# parameters
with open(os.path.join(folder_path_main, "disease_parameters.json"), "r") as file:
    disease_parameters = json.load(file)
with open(os.path.join(folder_path_main, "job_parameters.json"), "r") as file:
    job_parameters = json.load(file)
with open(os.path.join(folder_path_main, "scenario_parameters.json"), "r") as file:
    scenario_parameters = json.load(file)

spatial_only_parameters = {
    "n": len(properties),
    "r_wind": wind_radius,
    "xrange": xrange,
    "yrange": yrange,
}

if not os.path.exists(initial_movement_properties_filename) or not os.path.exists(initial_movement_diseaseoutbreak_filename):

    # initiate various things that start from empty:
    diseaseoutbreak = disease_simulation.DiseaseSimulation(
        time=start_time,
        movement_records=FMD_functions.create_movement_records_df(),
        disease_parameters=disease_parameters,
        spatial_only_parameters=spatial_only_parameters,
        job_parameters=job_parameters,
        scenario_parameters=scenario_parameters,
    )

    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path_burn_in_movement,
        unique_output=unique_output,
    )

    properties, movement_records, current_time, trucks_df = diseaseoutbreak.simulate_outbreak_spread_only(
        properties=properties,
        stop_time=minimum_spread_time,
        reporting_region_check=[xrange, yrange],
        min_infected_premises=target_infected_properties,
        outbreak_sim="FMD",
        max_spread_time=minimum_spread_time,
        trucks_df=trucks_df,
    )

    # and then resave the end state
    with open(initial_movement_properties_filename, "wb") as file:
        pickle.dump(properties, file)

    # and save the diseaseoutbreak object
    with open(initial_movement_diseaseoutbreak_filename, "wb") as file:
        pickle.dump(diseaseoutbreak, file)

    # and save the trucks
    with open(initial_movement_trucks_filename, "wb") as file:
        pickle.dump(trucks_df, file)

else:
    with open(initial_movement_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(initial_movement_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)
    with open(initial_movement_trucks_filename, "rb") as file:
        trucks_df = pickle.load(file)

HPAI_functions.save_approx_known_data(properties, folder_path_burn_in_movement, unique_output)

if create_download_folder:
    if download_parent_folder != None:
        v06_functions.create_separate_download_folder(folder_path_burn_in_movement, download_parent_folder, unique_output)
    else:
        v06_functions.create_separate_download_folder(folder_path_burn_in_movement, folder_path_main, "download_" + unique_output)


###################################################
# ---- Seed the first infection ------------------#
###################################################

# up to line 407

folder_path_seed = os.path.join(folder_path_main, "01_seed")
if not os.path.exists(folder_path_seed):
    os.makedirs(folder_path_seed)

properties_seeded_filename = os.path.join(folder_path_seed, f"properties_seeded")

seed_herd_id = 125520


if not os.path.exists(properties_seeded_filename):
    # seed property
    unique_output = "day0"
    properties, seed_property = FMD_functions.seed_FMD_infection(
        seed_herd_id,
        properties,
        diseaseoutbreak.time,
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

random.seed(3)
np.random.seed(3)
minimum_spread_time = minimum_spread_time + 27
target_infected_properties = 18

# area for first report - anywhere for now
reportingregion_x = xrange
reportingregion_y = yrange


unique_output = f"02_undetected_spread"
folder_path_undetected_spread = os.path.join(folder_path_main, unique_output)
if not os.path.exists(folder_path_undetected_spread):
    os.makedirs(folder_path_undetected_spread)

undetected_spread_properties_filename = os.path.join(folder_path_undetected_spread, "properties_" + unique_output)
undetected_spread_diseaseoutbreak_filename = os.path.join(folder_path_undetected_spread, "outbreakobject_" + unique_output)

spatial_only_parameters["n"] = len(properties)

if not os.path.exists(undetected_spread_properties_filename) or not os.path.exists(undetected_spread_diseaseoutbreak_filename):

    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path_undetected_spread,
        unique_output=unique_output,
    )

    # print(diseaseoutbreak.job_manager.jobs_queue)

    properties, movement_records, current_time, trucks_df = diseaseoutbreak.simulate_outbreak_spread_only(
        properties=properties,
        stop_time=minimum_spread_time,
        reporting_region_check=[reportingregion_x, reportingregion_y],
        min_infected_premises=target_infected_properties,
        outbreak_sim="FMD",
        max_spread_time=30,
        trucks_df=trucks_df,
    )

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

FMD_functions.save_approx_known_data(properties, folder_path_undetected_spread, unique_output)

if create_download_folder:
    if download_parent_folder != None:
        v06_functions.create_separate_download_folder(folder_path_undetected_spread, download_parent_folder, unique_output)
    else:
        v06_functions.create_separate_download_folder(folder_path_undetected_spread, folder_path_main, "download_" + unique_output)
        # line 516

# notes for next steps:continue following the v0.6 and continue set up of properties.
# then take a closer look at (1) the original FMD parameters to try and match them; and (2) the initial outbreak data to try and fit it; and (3) ABC method to more roughly fit it.
