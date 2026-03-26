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
from shapely.ops import unary_union

# import subprocess
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import simulator.fixed_spatial_setup as fixed_spatial_setup
import simulator.HPAI_functions as HPAI_functions
import simulator.output as output
import simulator.auto_job_mode as auto_job_mode
import simulator.spatial_setup as spatial_setup

# import simulator.simulator as simulator
import simulator.disease_simulation as disease_simulation
import simulator.management as management

# import simulator.management as management
import simulator.premises as premises


def x_y_ranges(state="NSW"):
    if state == "NSW":
        # Boundaries for NSW
        xrange = [140, 155]
        yrange = [-38, -28]
    elif state == "QLD" or state == "QLD-provided":
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

    return xrange, yrange, xlims, ylims


def create_separate_download_folder(folder_path_of_run, download_folder_path_main, download_folder_name):
    download_folder_path = os.path.join(download_folder_path_main, download_folder_name)

    if not os.path.exists(download_folder_path):
        os.makedirs(download_folder_path)

        # Loop through the files in the source directory and copy just the png or csv files
        for file in os.listdir(folder_path_of_run):
            if file.endswith(".png") or file.endswith(".csv"):
                if "underlying" not in file and "fake_data" not in file and "movement_records" not in file and "exposure" not in file:
                    source_path = os.path.join(folder_path_of_run, file)
                    destination_path = os.path.join(download_folder_path, file)
                    shutil.copy(source_path, destination_path)


def setup_to_outbreak_detection(state="NSW", burn_in_movement=10, testing=False, create_download_folder=False, download_parent_folder=None):
    ###################################################
    # ---- Code run set up ---------------------------#
    ###################################################
    xrange, yrange, xlims, ylims = x_y_ranges(state)

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
            ) = fixed_spatial_setup.HPAI_QLD_setup_locations(output_filename, testing)

            fixed_spatial_setup.HPAI_QLD_setup_locations_provided(output_filename)
        elif state == "QLD-provided":
            (
                ALL_coordinates,
                ALL_p_polygon,
                ALL_p_area,
                ALL_wind_radius,
                ALL_animal_type,
                ALL_premises_type,
                ALL_num_animals,
                ALL_LGAs,
                ALL_property_type,
                ALL_housing_type,
                chicken_meat_property_coordinates,
                processing_chicken_meat_property_coordinates,
                chicken_egg_property_coordinates,
                processing_chicken_egg_property_coordinates,
            ) = fixed_spatial_setup.HPAI_QLD_setup_locations_provided(output_filename)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Execution time of fixed_spatial_setup.HPAI_{state}_setup_locations(): {execution_time/60} minutes")

    else:
        if state == "NSW" or state == "QLD":
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
        elif state == "QLD-provided":
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
                    ALL_property_type,
                    ALL_housing_type,
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
        if state == "NSW" or state == "QLD":
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
        elif state == "QLD-provided":
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
                ALL_property_type,
                ALL_housing_type,
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
        if state in ["NSW", "QLD"]:
            fixed_spatial_setup.plot_map_land_HPAI_2(
                all_properties,
                xrange,
                yrange,
                folder_path_main,
                plot_suffix=suffix,
            )
        elif state == "QLD-provided":
            fixed_spatial_setup.plot_map_land_HPAI_2(
                all_properties,
                xrange,
                yrange,
                folder_path_main,
                plot_suffix=suffix,
                property_type_list=[
                    "Egg production; ",
                    "Mixed; ",
                    "Other; ",
                    "Meat production; ",
                    "pullet farm",
                    "egg processing",
                    "abbatoir",
                    "hatchery",
                    "breeder",
                    "backyard",
                ],
            )

    if not os.path.exists(os.path.join(folder_path_main, f"approx_known_data_{suffix}.csv")):
        HPAI_functions.save_approx_known_data(all_properties, folder_path_main, suffix)

    properties_filename = os.path.join(folder_path_main, f"HPAI_properties{suffix}")
    if not os.path.exists(properties_filename):

        start_time = time.time()

        properties = fixed_spatial_setup.HPAI_movement_network_setup(
            all_properties,
            max_movement_km=200,  # 200km max movement
            state=state,
        )

        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Execution time of fixed_spatial_setup.HPAI_movement_network_setup(): {execution_time/60} minutes")

        start_time = time.time()
        # pre-finds all addressess - takes 1 second per property
        for property_i in properties:
            loc = property_i.get_location()
        print(f"Execution time of finding all property addressess: {execution_time/60} minutes")

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
    minimum_spread_time = burn_in_movement
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
        if download_parent_folder != None:
            create_separate_download_folder(folder_path_burn_in_movement, download_parent_folder, unique_output)
        else:
            create_separate_download_folder(folder_path_burn_in_movement, folder_path_main, "download_" + unique_output)

    ###################################################
    # ---- Seed the first infection ------------------#
    ###################################################

    folder_path_seed = os.path.join(folder_path_main, "01_seed")
    if not os.path.exists(folder_path_seed):
        os.makedirs(folder_path_seed)

    properties_seeded_filename = os.path.join(folder_path_seed, f"properties_seeded{suffix}")

    seedlocationx = xrange
    seedlocationy = yrange

    if state == "NSW":
        random.seed(2)
        np.random.seed(2)
    elif state == "QLD":
        random.seed(1086)
        np.random.seed(3243)
    elif state == "QLD-provided":
        random.seed(1086)
        np.random.seed(3243)
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
        if download_parent_folder != None:
            create_separate_download_folder(folder_path_undetected_spread, download_parent_folder, unique_output)
        else:
            create_separate_download_folder(folder_path_undetected_spread, folder_path_main, "download_" + unique_output)

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
        if download_parent_folder != None:
            create_separate_download_folder(folder_path_first_report, download_parent_folder, unique_output)
        else:
            create_separate_download_folder(folder_path_first_report, folder_path_main, "download_" + unique_output)

    approx_data_filename = os.path.join(folder_path_first_report, "approx_known_data_01.csv")

    return (
        folder_path_main,
        folder_path_first_report,
        spread_properties_filename,
        spread_diseaseoutbreak_filename,
        approx_data_filename,
    )


def get_enhanced_passive_surveillance_area(property_based_zones, properties):
    EPS_df = property_based_zones[property_based_zones["zone_type"] == "Enhanced Passive Surveillance"]
    EPS_geo_list = []
    enhanced_reporting_factor = 1
    for i, row in EPS_df.iterrows():

        enhanced_passive_surveillance_area = management.define_control_zone_polygons(
            properties,
            [row["ID"]],
            row["radius_km"],
            convex=False,
        )  # should be zero movement
        EPS_geo_list.append(enhanced_passive_surveillance_area)
        if isinstance(row["zone_parameter"], float):
            enhanced_reporting_factor = row["zone_parameter"]
        elif row["zone_parameter"].isnull() and enhanced_reporting_factor == 1:
            enhanced_reporting_factor = 2
        else:
            pass

    enhanced_passive_surveillance_area = unary_union(EPS_geo_list)

    Australia_gdf = spatial_setup.get_Australia_shape()

    NSW = Australia_gdf.loc[Australia_gdf["STE_NAME21"] == "New South Wales", :]

    NSW_shape = list(NSW["geometry"])[0]

    return enhanced_passive_surveillance_area.intersection(NSW_shape), enhanced_reporting_factor


def run_actions_excel(
    state,
    previous_unique_output,
    actions_filename_excel,
    days_to_run_for=1,
    unique_output="04_actions_1",
    output_suffix="_02",
    create_download_folder=False,
    RA_shape=None,
    CA_shape=None,
    EPS_shape=None,
    EPS_factor=None,
    download_parent_folder=None,
    download_folder_name=None,
):

    folder_path_main = os.path.join(os.path.dirname(__file__), f"v06_{state}")

    # read in previous state
    previous_spread_properties_filename = os.path.join(folder_path_main, previous_unique_output, "properties_" + previous_unique_output)
    previous_spread_diseaseoutbreak_filename = os.path.join(folder_path_main, previous_unique_output, "outbreakobject_" + previous_unique_output)

    with open(previous_spread_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(previous_spread_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)

    # set up for new simulation portion
    folder_path = os.path.join(folder_path_main, unique_output)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    spread_properties_filename = os.path.join(folder_path, "properties_" + unique_output)
    spread_diseaseoutbreak_filename = os.path.join(folder_path, "outbreakobject_" + unique_output)

    xrange, yrange, xlims, ylims = x_y_ranges(state)

    # read in jobs and zones
    actions_input = os.path.join(folder_path_main, actions_filename_excel)
    property_jobs = pd.read_excel(actions_input, sheet_name="jobs")
    zones_based_jobs = pd.read_excel(actions_input, sheet_name="zone_jobs")  # could consider "expanding to SAL, LGA" or something like that
    property_based_zones = pd.read_excel(actions_input, sheet_name="zones")  # could consider "expanding to SAL, LGA" or something like that

    # construct zones
    enhanced_passive_surveillance_area, enhanced_reporting_factor = get_enhanced_passive_surveillance_area(property_based_zones, properties)

    if EPS_shape != None:
        enhanced_passive_surveillance_area = unary_union([enhanced_passive_surveillance_area, EPS_shape])
    if EPS_factor != None:
        enhanced_reporting_factor = EPS_factor

    random.seed(1235)
    np.random.seed(1116)
    if not os.path.exists(spread_properties_filename) or not os.path.exists(spread_diseaseoutbreak_filename):
        # adjust the plotting parameters for this new scenario
        diseaseoutbreak.set_plotting_parameters(
            xlims=xlims,
            ylims=ylims,
            plotting=True,
            folder_path=folder_path,
            unique_output=unique_output,
        )

        properties, movement_records, current_time, total_culled_animals, job_manager = diseaseoutbreak.simulate_HPAI_outbreak_management(
            properties,
            property_jobs,
            zones_based_jobs,
            property_based_zones,
            days_to_run_for,
            restricted_emergency_zone=RA_shape,
            control_emergency_zone=CA_shape,
            enhanced_passive_surveillance_area=enhanced_passive_surveillance_area,
            enhanced_reporting_factor=enhanced_reporting_factor,
            output_suffix=output_suffix,
        )

        HPAI_functions.save_approx_known_data(properties, folder_path, unique_output="", output_suffix=output_suffix)

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
    else:
        with open(spread_properties_filename, "rb") as file:
            properties = pickle.load(file)
        with open(spread_diseaseoutbreak_filename, "rb") as file:
            diseaseoutbreak = pickle.load(file)

    if create_download_folder:
        if download_parent_folder == None:
            download_parent_folder = folder_path_main
        if download_folder_name == None:
            download_folder_name = "download_" + unique_output

        create_separate_download_folder(folder_path, download_parent_folder, download_folder_name)

    approx_data_filename = os.path.join(folder_path, f"approx_known_data{output_suffix}.csv")

    return (
        folder_path_main,
        folder_path,
        spread_properties_filename,
        spread_diseaseoutbreak_filename,
        approx_data_filename,
    )


def run_actions_excel_shapefile(
    state,
    previous_unique_output,
    actions_filename_excel,
    shapefile_path,
    days_to_run_for=1,
    unique_output="04_actions_1",
    output_suffix="_02",
    create_download_folder=False,
    download_parent_folder=None,
    download_folder_name=None,
):

    # folder_path_main = os.path.join(os.path.dirname(__file__), f"v06_{state}")

    # shp_zones = gpd.read_file(os.path.join(folder_path_main, shapefile_path))
    shp_zones = gpd.read_file(shapefile_path)

    # restricted area
    shp_zones_RA = shp_zones.loc[shp_zones["EMZ_1"] == "REZ", :]
    RA_shape = list(shp_zones_RA["geometry"])[0]

    # control area
    shp_zones_CA = shp_zones.loc[shp_zones["EMZ_1"] == "CEZ", :]
    CA_shape = list(shp_zones_CA["geometry"])[0]

    # enhanced passive surveillance area
    shp_zones_EPS = shp_zones.loc[shp_zones["EMZ_1"] == "Enhanced Passive Surveillance", :]
    EPS_shape = list(shp_zones_EPS["geometry"])[0]  # enhanced passive surveillance shape, assuming it's the same as the RA for now
    # EPS_factor = 1.1

    # could also read in enhanced surveillance area here

    return run_actions_excel(
        state,
        previous_unique_output,
        actions_filename_excel,
        days_to_run_for=days_to_run_for,
        unique_output=unique_output,
        output_suffix=output_suffix,
        create_download_folder=create_download_folder,
        RA_shape=RA_shape,
        CA_shape=CA_shape,
        EPS_shape=EPS_shape,
        # EPS_factor=EPS_factor,
        download_parent_folder=download_parent_folder,
        download_folder_name=download_folder_name,
    )


def run_status_update_only_excel_shapefile(
    state,
    previous_unique_output,
    actions_filename_excel=None,
    shapefile_path=None,
    unique_output="04_actions_1_updated",
    output_suffix="_02_updated",
    create_download_folder=False,
    download_parent_folder=None,
    download_folder_name=None,
):

    RA_shape = None
    CA_shape = None
    EPS_shape = None
    if shapefile_path != None:
        shp_zones = gpd.read_file(shapefile_path)

        # restricted area
        shp_zones_RA = shp_zones.loc[shp_zones["EMZ"] == "REZ", :]
        RA_shape = list(shp_zones_RA["geometry"])[0]

        # control area
        shp_zones_CA = shp_zones.loc[shp_zones["EMZ"] == "CEZ", :]
        CA_shape = list(shp_zones_CA["geometry"])[0]

        # enhanced passive surveillance area
        shp_zones_EPS = shp_zones.loc[shp_zones["EMZ"] == "Enhanced Passive Surveillance", :]
        EPS_shape = list(shp_zones_EPS["geometry"])[0]  # enhanced passive surveillance shape, assuming it's the same as the RA for now

    folder_path_main = os.path.join(os.path.dirname(__file__), f"v06_{state}")

    # read in previous state
    previous_spread_properties_filename = os.path.join(folder_path_main, previous_unique_output, "properties_" + previous_unique_output)
    previous_spread_diseaseoutbreak_filename = os.path.join(folder_path_main, previous_unique_output, "outbreakobject_" + previous_unique_output)

    with open(previous_spread_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(previous_spread_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)

    # set up for new simulation portion
    folder_path = os.path.join(folder_path_main, unique_output)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    spread_properties_filename = os.path.join(folder_path, "properties_" + unique_output)
    spread_diseaseoutbreak_filename = os.path.join(folder_path, "outbreakobject_" + unique_output)

    xrange, yrange, xlims, ylims = x_y_ranges(state)

    # read in jobs and zones
    property_based_zones = None
    enhanced_passive_surveillance_area = None
    if actions_filename_excel != None:
        actions_input = os.path.join(folder_path_main, actions_filename_excel)
        property_based_zones = pd.read_excel(actions_input, sheet_name="zones")

        # construct zones
        enhanced_passive_surveillance_area, enhanced_reporting_factor = get_enhanced_passive_surveillance_area(property_based_zones, properties)

    if EPS_shape != None and enhanced_passive_surveillance_area != None:
        enhanced_passive_surveillance_area = unary_union([enhanced_passive_surveillance_area, EPS_shape])
    elif EPS_shape == None:
        pass
    elif enhanced_passive_surveillance_area == None:
        enhanced_passive_surveillance_area = EPS_shape

    random.seed(1235)
    np.random.seed(1116)
    if not os.path.exists(spread_properties_filename) or not os.path.exists(spread_diseaseoutbreak_filename):
        # adjust the plotting parameters for this new scenario
        diseaseoutbreak.set_plotting_parameters(
            xlims=xlims,
            ylims=ylims,
            plotting=True,
            folder_path=folder_path,
            unique_output=unique_output,
        )

        properties, movement_records, current_time, total_culled_animals, job_manager = diseaseoutbreak.assign_statuses_based_on_zones_only(
            properties,
            property_based_zones,
            restricted_emergency_zone=RA_shape,
            control_emergency_zone=CA_shape,
            enhanced_passive_surveillance_area=enhanced_passive_surveillance_area,
            output_suffix=output_suffix,
        )

        HPAI_functions.save_approx_known_data(properties, folder_path, unique_output="", output_suffix=output_suffix)

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
    else:
        with open(spread_properties_filename, "rb") as file:
            properties = pickle.load(file)
        with open(spread_diseaseoutbreak_filename, "rb") as file:
            diseaseoutbreak = pickle.load(file)

    if create_download_folder:
        if download_parent_folder == None:
            download_parent_folder = folder_path_main
        if download_folder_name == None:
            download_folder_name = "download_" + unique_output

        create_separate_download_folder(folder_path, download_parent_folder, download_folder_name)

    approx_data_filename = os.path.join(folder_path, f"approx_known_data{output_suffix}.csv")

    return (
        folder_path_main,
        folder_path,
        spread_properties_filename,
        spread_diseaseoutbreak_filename,
        approx_data_filename,
    )


def run_auto_actions(
    state,
    previous_unique_output,
    previous_output_suffix_int=1,
    total_days_to_run_for=7,
    start_action_number_int=1,
    unique_output_starting_int=4,
    create_download_folder=False,
    max_resource_units=100,
    download_parent_folder=None,
    download_folder_name=None,
    strategy="default",
):
    folder_path_main = os.path.join(os.path.dirname(__file__), f"v06_{state}")
    xrange, yrange, xlims, ylims = x_y_ranges(state)

    previous_folder = os.path.join(folder_path_main, previous_unique_output)
    previous_output_suffix = f"_{previous_output_suffix_int:02d}"

    previous_spread_properties_filename = os.path.join(folder_path_main, previous_unique_output, "properties_" + previous_unique_output)
    previous_spread_diseaseoutbreak_filename = os.path.join(folder_path_main, previous_unique_output, "outbreakobject_" + previous_unique_output)

    with open(previous_spread_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(previous_spread_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)

    # # TEMP ONLY - FIND ALL ADDRESSESS TODO - delete this afterwards
    # for property_i in properties:
    #     loca= property_i.get_location()

    days_to_run_for = 1

    action_number = start_action_number_int
    running_day = 1
    while running_day <= total_days_to_run_for:
        # get previous info
        approx_data_csv = os.path.join(previous_folder, f"approx_known_data{previous_output_suffix}.csv")

        # set up new info
        outputnumber = action_number + 1
        output_suffix = f"_{outputnumber:02d}"

        unique_outputnumber = unique_output_starting_int
        unique_output = f"{unique_outputnumber:02d}_actions_{action_number}_{strategy}"
        folder_path = os.path.join(folder_path_main, unique_output)

        print(folder_path)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        spread_properties_filename = os.path.join(folder_path, "properties_" + unique_output)
        spread_diseaseoutbreak_filename = os.path.join(folder_path, "outbreakobject_" + unique_output)

        # assign jobs
        scheduled_date = premises.convert_time_to_date(diseaseoutbreak.time + 1)
        if (
            not os.path.exists(os.path.join(folder_path, f"jobs_{action_number}.csv"))
            or not os.path.exists(os.path.join(folder_path, f"zone_jobs_{action_number}.csv"))
            or not os.path.exists(os.path.join(folder_path, f"zones_{action_number}.csv"))
        ):
            auto_job_mode.generate_jobs(folder_path, approx_data_csv, scheduled_date, action_number, max_resource_units, strategy)

        property_jobs = pd.read_csv(os.path.join(folder_path, f"jobs_{action_number}.csv"))
        zones_based_jobs = pd.read_csv(os.path.join(folder_path, f"zone_jobs_{action_number}.csv"))
        property_based_zones = pd.read_csv(os.path.join(folder_path, f"zones_{action_number}.csv"))

        enhanced_passive_surveillance_area, enhanced_reporting_factor = get_enhanced_passive_surveillance_area(property_based_zones, properties)

        random.seed(1235)
        np.random.seed(1116)
        if not os.path.exists(spread_properties_filename) or not os.path.exists(spread_diseaseoutbreak_filename):
            # adjust the plotting parameters for this new scenario
            diseaseoutbreak.set_plotting_parameters(
                xlims=xlims,
                ylims=ylims,
                plotting=True,
                folder_path=folder_path,
                unique_output=unique_output,
            )

            properties, movement_records, current_time, total_culled_animals, job_manager = diseaseoutbreak.simulate_HPAI_outbreak_management(
                properties,
                property_jobs,
                zones_based_jobs,
                property_based_zones,
                days_to_run_for,
                enhanced_passive_surveillance_area=enhanced_passive_surveillance_area,
                enhanced_reporting_factor=enhanced_reporting_factor,
                output_suffix=output_suffix,
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
        else:
            with open(spread_properties_filename, "rb") as file:
                properties = pickle.load(file)
            with open(spread_diseaseoutbreak_filename, "rb") as file:
                diseaseoutbreak = pickle.load(file)

        HPAI_functions.save_approx_known_data(properties, folder_path, unique_output="", output_suffix=output_suffix)

        if create_download_folder:
            if download_parent_folder == None:
                download_parent_folder = folder_path_main
            if download_folder_name == None:
                download_folder_name = unique_output + "_"

            create_separate_download_folder(folder_path, download_parent_folder, download_folder_name)

        action_number += 1
        previous_folder = folder_path
        previous_output_suffix = output_suffix
        unique_output_starting_int += 1

        running_day += 1


def run_auto_actions_with_shapefile(
    state,
    previous_unique_output,
    shapefile_path,
    previous_output_suffix_int=1,
    total_days_to_run_for=7,
    strategy="fast DDD",
):
    folder_path_main = os.path.join(os.path.dirname(__file__), f"v06_{state}")
    xrange, yrange, xlims, ylims = x_y_ranges(state)

    # shp_zones = gpd.read_file(os.path.join(folder_path_main, shapefile_path))
    shp_zones = gpd.read_file(shapefile_path)

    # restricted area
    shp_zones_RA = shp_zones.loc[shp_zones["EMZ"] == "REZ", :]
    RA_shape = list(shp_zones_RA["geometry"])[0]

    # control area
    shp_zones_CA = shp_zones.loc[shp_zones["EMZ"] == "CEZ", :]
    CA_shape = list(shp_zones_CA["geometry"])[0]

    # enhanced passive surveillance area
    shp_zones_EPS = shp_zones.loc[shp_zones["EMZ"] == "Enhanced Passive Surveillance", :]
    EPS_shape = list(shp_zones_EPS["geometry"])[0]  # enhanced passive surveillance shape, assuming it's the same as the RA for now
    EPS_factor = None

    previous_folder = os.path.join(folder_path_main, previous_unique_output)
    previous_output_suffix = f"_{previous_output_suffix_int:02d}"

    previous_spread_properties_filename = os.path.join(folder_path_main, previous_unique_output, "properties_" + previous_unique_output)
    previous_spread_diseaseoutbreak_filename = os.path.join(folder_path_main, previous_unique_output, "outbreakobject_" + previous_unique_output)

    with open(previous_spread_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(previous_spread_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)

    running_day = 1
    days_to_run_for = 1
    while running_day <= total_days_to_run_for:
        # get previous info
        approx_data_csv = os.path.join(previous_folder, f"approx_known_data{previous_output_suffix}.csv")

        # set up new info
        outputnumber = previous_output_suffix_int + 1
        output_suffix = f"_{outputnumber:02d}"

        unique_output = f"{previous_unique_output}_{running_day:02d}"
        folder_path = os.path.join(folder_path_main, unique_output)

        print(folder_path)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        spread_properties_filename = os.path.join(folder_path, "properties_" + unique_output)
        spread_diseaseoutbreak_filename = os.path.join(folder_path, "outbreakobject_" + unique_output)

        # assign jobs
        scheduled_date = premises.convert_time_to_date(diseaseoutbreak.time + 1)
        if (
            not os.path.exists(os.path.join(folder_path, f"jobs_{running_day}.csv"))
            or not os.path.exists(os.path.join(folder_path, f"zone_jobs_{running_day}.csv"))
            or not os.path.exists(os.path.join(folder_path, f"zones_{running_day}.csv"))
        ):
            auto_job_mode.generate_jobs_teams(folder_path, approx_data_csv, scheduled_date, running_day, strategy)

        property_jobs = pd.read_csv(os.path.join(folder_path, f"jobs_{running_day}.csv"))
        zones_based_jobs = pd.read_csv(os.path.join(folder_path, f"zone_jobs_{running_day}.csv"))
        property_based_zones = pd.read_csv(os.path.join(folder_path, f"zones_{running_day}.csv"))

        enhanced_passive_surveillance_area, enhanced_reporting_factor = get_enhanced_passive_surveillance_area(property_based_zones, properties)
        if EPS_shape != None:
            enhanced_passive_surveillance_area = unary_union([enhanced_passive_surveillance_area, EPS_shape])
        if EPS_factor != None:
            enhanced_reporting_factor = EPS_factor

        random.seed(1235)
        np.random.seed(1116)
        if not os.path.exists(spread_properties_filename) or not os.path.exists(spread_diseaseoutbreak_filename):
            # adjust the plotting parameters for this new scenario
            diseaseoutbreak.set_plotting_parameters(
                xlims=xlims,
                ylims=ylims,
                plotting=True,
                folder_path=folder_path,
                unique_output=unique_output,
            )

            properties, movement_records, current_time, total_culled_animals, job_manager = diseaseoutbreak.simulate_HPAI_outbreak_management(
                properties,
                property_jobs,
                zones_based_jobs,
                property_based_zones,
                days_to_run_for,
                restricted_emergency_zone=RA_shape,
                control_emergency_zone=CA_shape,
                enhanced_passive_surveillance_area=enhanced_passive_surveillance_area,
                enhanced_reporting_factor=enhanced_reporting_factor,
                output_suffix=output_suffix,
            )

            HPAI_functions.save_approx_known_data(properties, folder_path, unique_output="", output_suffix=output_suffix)

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
        else:
            with open(spread_properties_filename, "rb") as file:
                properties = pickle.load(file)
            with open(spread_diseaseoutbreak_filename, "rb") as file:
                diseaseoutbreak = pickle.load(file)

        previous_folder = folder_path
        previous_output_suffix_int = outputnumber
        previous_output_suffix = output_suffix

        running_day += 1
