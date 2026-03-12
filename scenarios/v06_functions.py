"""v06 | Script with functions to run simulation (I guess I could put this into simulator.py or something)"""

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

# import simulator.simulator as simulator
import simulator.disease_simulation as disease_simulation

# import simulator.management as management
import simulator.premises as premises


def setup_to_outbreak_detection(state="NSW", testing=False, create_download_folder=False):
    ###################################################
    # ---- Code run set up ---------------------------#
    ###################################################
    if state == "NSW":
        # Boundaries for NSW
        xrange = [140, 155]
        yrange = [-38, -28]
    elif state == "QLD":
        # Boundaries for QLD
        xrange = [140, 155]
        yrange = [-30, -10]
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

    folder_path_main = os.path.join(os.path.dirname(__file__), f"v06_{state}")

    suffix = ""
    if testing:
        suffix = "_test"

    ###################################################
    # ---- Set up properties and locations -----------#
    ###################################################

    # generates locations for properties, and makes them into property objects  (which contain information about what type of premises it is)
    output_filename = os.path.join(folder_path_main, f"HPAI_{state}_setup_locations{suffix}")

    if not os.path.exists(output_filename):
        start_time = time.time()
        if state == "NSW":
            (
                ALL_coordinates,
                ALL_p_polygon,
                ALL_p_area,
                ALL_wind_radius,
                ALL_animal_type,
                ALL_premises_type,
                ALL_num_animals,
                ALL_LGAs,
                chicken_meat_property_coordinates,
                processing_chicken_meat_property_coordinates,
                chicken_egg_property_coordinates,
                processing_chicken_egg_property_coordinates,
            ) = fixed_spatial_setup.HPAI_NSW_setup_locations(output_filename, testing)
        elif state == "QLD":
            raise RuntimeError("QLD not yet coded!")
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Execution time of fixed_spatial_setup.HPAI_{state}_setup_locations(): {execution_time/60} minutes")
    else:
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
                chicken_meat_property_coordinates,
                processing_chicken_meat_property_coordinates,
                chicken_egg_property_coordinates,
                processing_chicken_egg_property_coordinates,
            ) = pickle.load(file)

    # plot that actually shows the locations of different facilities (aside from backyard ones at the moment)
    if not os.path.exists(os.path.join(folder_path_main, f"property_locations_base_map{suffix}.png")):
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

    output_filename = os.path.join(folder_path_main, f"HPAI_{state}_all_properties{suffix}")
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
        )
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Execution time of fixed_spatial_setup.initialise_all_properties(): {execution_time/60} minutes")
    else:
        with open(output_filename, "rb") as file:
            all_properties = pickle.load(file)

    print(f"total facilities started: {len(all_properties)}")

    if not os.path.exists(os.path.join(folder_path_main, f"data_underlying_{suffix}.csv")):
        fixed_spatial_setup.save_chicken_property_csv(all_properties, 0, folder_path_main, suffix)

    if not os.path.exists(os.path.join(folder_path_main, f"property_locations_base_map_types{suffix}.png")):
        fixed_spatial_setup.plot_map_land_HPAI_2(
            all_properties,
            xrange,
            yrange,
            folder_path_main,
            plot_suffix=suffix,
        )

    if not os.path.exists(os.path.join(folder_path_main, f"approx_known_data_{suffix}.csv")):
        HPAI_functions.save_approx_known_data(all_properties, folder_path_main, suffix)

    properties_filename = os.path.join(folder_path_main, f"HPAI_properties{suffix}")
    if not os.path.exists(properties_filename):

        start_time = time.time()

        properties = fixed_spatial_setup.HPAI_movement_network_setup(
            all_properties,
            max_movement_km=200,  # 200km max movement
        )

        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Execution time of fixed_spatial_setup.HPAI_movement_network_setup(): {execution_time/60} minutes")

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

    ###################################################
    # ---- "Burn in" movement -------------------------#
    ###################################################

    start_time = 0

    random.seed(10)
    np.random.seed(10)
    minimum_spread_time = 10
    target_infected_properties = 0

    unique_output = f"0_burn_in_movement"
    folder_path_burn_in_movement = os.path.join(folder_path_main, unique_output)
    if not os.path.exists(folder_path_burn_in_movement):
        os.makedirs(folder_path_burn_in_movement)

    initial_movement_properties_filename = os.path.join(folder_path_burn_in_movement, "properties_" + unique_output)
    initial_movement_diseaseoutbreak_filename = os.path.join(folder_path_burn_in_movement, "outbreakobject_" + unique_output)

    # parameters
    with open(os.path.join(folder_path_main, "disease_parameters.json"), "r") as file:
        disease_parameters = json.load(file)
    with open(os.path.join(folder_path_main, f"spatial_only_parameters.json"), "r") as file:
        spatial_only_parameters = json.load(file)
    with open(os.path.join(folder_path_main, "job_parameters.json"), "r") as file:
        job_parameters = json.load(file)
    with open(os.path.join(folder_path_main, "scenario_parameters.json"), "r") as file:
        scenario_parameters = json.load(file)

    spatial_only_parameters["n"] = len(properties)

    if not os.path.exists(initial_movement_properties_filename) or not os.path.exists(initial_movement_diseaseoutbreak_filename):

        # initiate various things that start from empty:
        diseaseoutbreak = disease_simulation.DiseaseSimulation(
            time=start_time,
            movement_records=HPAI_functions.create_movement_records_df(),
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

        # print(diseaseoutbreak.job_manager.jobs_queue)

        properties, movement_records, current_time = diseaseoutbreak.simulate_outbreak_spread_only(
            properties=properties,
            stop_time=minimum_spread_time,
            reporting_region_check=[xrange, yrange],
            min_infected_premises=target_infected_properties,
            outbreak_sim="HPAI",
            max_spread_time=minimum_spread_time,
        )

        # and then resave the end state
        with open(initial_movement_properties_filename, "wb") as file:
            pickle.dump(properties, file)

        # and save the diseaseoutbreak object
        with open(initial_movement_diseaseoutbreak_filename, "wb") as file:
            pickle.dump(diseaseoutbreak, file)

    else:
        with open(initial_movement_properties_filename, "rb") as file:
            properties = pickle.load(file)
        with open(initial_movement_diseaseoutbreak_filename, "rb") as file:
            diseaseoutbreak = pickle.load(file)

    HPAI_functions.save_approx_known_data(properties, folder_path_burn_in_movement, unique_output)

    if create_download_folder:
        download_folder_path = os.path.join(folder_path_main, "download_" + unique_output)

        if not os.path.exists(download_folder_path):
            os.makedirs(download_folder_path)

            # Loop through the files in the source directory and copy just the png or csv files
            for file in os.listdir(folder_path_burn_in_movement):
                if file.endswith(".png") or file.endswith(".csv"):
                    source_path = os.path.join(folder_path_burn_in_movement, file)
                    destination_path = os.path.join(download_folder_path, file)
                    shutil.copy(source_path, destination_path)

    ###################################################
    # ---- Seed the first infection ------------------#
    ###################################################

    folder_path_seed = os.path.join(folder_path_main, "01_seed")
    if not os.path.exists(folder_path_seed):
        os.makedirs(folder_path_seed)

    properties_seeded_filename = os.path.join(folder_path_seed, f"properties_seeded{suffix}")

    seedlocationx = xrange
    seedlocationy = yrange

    random.seed(2)
    np.random.seed(2)
    if not os.path.exists(properties_seeded_filename):
        # seed property
        unique_output = "day0"
        properties, seed_property = HPAI_functions.seed_HPAI_infection(
            seedlocationx,
            seedlocationy,
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
    minimum_spread_time = minimum_spread_time + 7
    target_infected_properties = 4

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

        properties, movement_records, current_time = diseaseoutbreak.simulate_outbreak_spread_only(
            properties=properties,
            stop_time=minimum_spread_time,
            reporting_region_check=[reportingregion_x, reportingregion_y],
            min_infected_premises=target_infected_properties,
            outbreak_sim="HPAI",
            max_spread_time=30,
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

    HPAI_functions.save_approx_known_data(properties, folder_path_undetected_spread, unique_output)

    if create_download_folder:
        download_folder_path = os.path.join(folder_path_main, "download_" + unique_output)

        if not os.path.exists(download_folder_path):
            os.makedirs(download_folder_path)

            # Loop through the files in the source directory and copy just the png or csv files
            for file in os.listdir(folder_path_undetected_spread):
                if file.endswith(".png") or file.endswith(".csv"):
                    source_path = os.path.join(folder_path_undetected_spread, file)
                    destination_path = os.path.join(download_folder_path, file)
                    shutil.copy(source_path, destination_path)

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

    output_suffix = "_01"

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

        properties, movement_records, current_time, total_culled_animals, job_manager = diseaseoutbreak.simulate_first_report(
            properties, reportingregion_x, reportingregion_y, output_suffix=output_suffix
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

    HPAI_functions.save_approx_known_data(properties, folder_path_first_report, unique_output="", output_suffix=output_suffix)

    if create_download_folder:
        download_folder_path = os.path.join(folder_path_main, "download_" + unique_output)

        if not os.path.exists(download_folder_path):
            os.makedirs(download_folder_path)

            # Loop through the files in the source directory and copy just the png or csv files
            for file in os.listdir(folder_path_first_report):
                if file.endswith(".png") or file.endswith(".csv"):
                    source_path = os.path.join(folder_path_first_report, file)
                    destination_path = os.path.join(download_folder_path, file)
                    shutil.copy(source_path, destination_path)

    approx_data_filename = os.path.join(folder_path_first_report, "approx_known_data_01.csv")

    return (
        xrange,
        yrange,
        xlims,
        ylims,
        folder_path_main,
        folder_path_first_report,
        spread_properties_filename,
        spread_diseaseoutbreak_filename,
        approx_data_filename,
    )
