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
from shapely.ops import unary_union

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


def setup(state="VIC", wind_radius=20):
    ###################################################
    # ---- Code run set up ---------------------------#
    ###################################################

    xrange, yrange, xlims, ylims = x_y_ranges(state)

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

    trucks_filename = os.path.join(folder_path_main, f"FMD_{state}_trucks_df")
    if not os.path.exists(trucks_filename):
        trucks_df = FMD_functions.construct_trucks(properties)
        trucks_df.to_csv(os.path.join(folder_path_main, f"trucks_df_.csv"))
        with open(trucks_filename, "wb") as file:
            pickle.dump(trucks_df, file)

    return (folder_path_main, properties_filename, trucks_filename)


def run_burn_in_movement(
    properties,
    trucks_df,
    start_time,
    burn_in_time,
    folder_path_main,
    disease_parameters,
    spatial_only_parameters,
    job_parameters,
    scenario_parameters,
    xlims,
    ylims,
    xrange,
    yrange,
    create_download_folder,
    download_parent_folder,
):
    random.seed(10)
    np.random.seed(10)

    minimum_spread_time = start_time + burn_in_time
    target_infected_properties = 0

    unique_output = f"0_burn_in_movement"
    folder_path_burn_in_movement = os.path.join(folder_path_main, unique_output)
    if not os.path.exists(folder_path_burn_in_movement):
        os.makedirs(folder_path_burn_in_movement)

    initial_movement_properties_filename = os.path.join(folder_path_burn_in_movement, "properties_" + unique_output)
    initial_movement_diseaseoutbreak_filename = os.path.join(folder_path_burn_in_movement, "outbreakobject_" + unique_output)
    initial_movement_trucks_filename = os.path.join(folder_path_burn_in_movement, "trucks_df_" + unique_output)

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

    FMD_functions.save_approx_known_data(properties, folder_path_burn_in_movement, unique_output)

    if create_download_folder:
        if download_parent_folder != None:
            v06_functions.create_separate_download_folder(folder_path_burn_in_movement, download_parent_folder, unique_output)
        else:
            v06_functions.create_separate_download_folder(folder_path_burn_in_movement, folder_path_main, "download_" + unique_output)

    return properties, diseaseoutbreak, trucks_df


def run_seeding_undetected_spread(state="VIC", burn_in_time=0, create_download_folder=False, download_parent_folder=None, wind_radius=20):
    ###################################################
    # ---- Code run set up ---------------------------#
    ###################################################

    xrange, yrange, xlims, ylims = x_y_ranges(state)

    folder_path_main = os.path.join(os.path.dirname(__file__), f"vFMD{state}")

    properties_filename = os.path.join(folder_path_main, f"FMD_{state}_properties")
    with open(properties_filename, "rb") as file:
        properties = pickle.load(file)

    trucks_filename = os.path.join(folder_path_main, f"FMD_{state}_trucks_df")
    with open(trucks_filename, "rb") as file:
        trucks_df = pickle.load(file)

    start_time = 0

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

    # area for first report - anywhere for now
    reportingregion_x = xrange
    reportingregion_y = yrange

    ###################################################
    # ---- "Burn in" movement ------------------------#
    ###################################################

    if burn_in_time > 0:
        properties, diseaseoutbreak, trucks_df = run_burn_in_movement(
            properties,
            trucks_df,
            start_time,
            burn_in_time,
            folder_path_main,
            disease_parameters,
            spatial_only_parameters,
            job_parameters,
            scenario_parameters,
            xlims,
            ylims,
            xrange,
            yrange,
            create_download_folder,
            download_parent_folder,
        )
    else:
        # initiate various things that start from empty:
        diseaseoutbreak = disease_simulation.DiseaseSimulation(
            time=start_time,
            movement_records=FMD_functions.create_movement_records_df(),
            disease_parameters=disease_parameters,
            spatial_only_parameters=spatial_only_parameters,
            job_parameters=job_parameters,
            scenario_parameters=scenario_parameters,
        )

    ###################################################
    # ---- Seed the first infection ------------------#
    ###################################################

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
        )
    else:
        with open(properties_seeded_filename, "rb") as file:
            properties = pickle.load(file)

    ###################################################
    # ---- Undetected spread -------------------------#
    ###################################################
    # spread and then detection after a fixed number of properties infected...

    random.seed(10)
    np.random.seed(10)
    minimum_spread_time = diseaseoutbreak.time + 27
    target_infected_properties = 18

    unique_output = f"02_undetected_spread"
    folder_path_undetected_spread = os.path.join(folder_path_main, unique_output)
    if not os.path.exists(folder_path_undetected_spread):
        os.makedirs(folder_path_undetected_spread)

    undetected_spread_properties_filename = os.path.join(folder_path_undetected_spread, "properties_" + unique_output)
    undetected_spread_diseaseoutbreak_filename = os.path.join(folder_path_undetected_spread, "outbreakobject_" + unique_output)
    undetected_spread_trucks_filename = os.path.join(folder_path_undetected_spread, "trucks_df_" + unique_output)

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

        # and save the trucks
        with open(undetected_spread_trucks_filename, "wb") as file:
            pickle.dump(trucks_df, file)

        FMD_functions.save_approx_known_data(properties, folder_path_undetected_spread, unique_output)

        if create_download_folder:
            if download_parent_folder != None:
                v06_functions.create_separate_download_folder(folder_path_undetected_spread, download_parent_folder, unique_output)
            else:
                v06_functions.create_separate_download_folder(folder_path_undetected_spread, folder_path_main, "download_" + unique_output)

    else:
        with open(undetected_spread_properties_filename, "rb") as file:
            properties = pickle.load(file)
    #     with open(undetected_spread_diseaseoutbreak_filename, "rb") as file:
    #         diseaseoutbreak = pickle.load(file)
    #     with open(undetected_spread_trucks_filename, "rb") as file:
    #         trucks_df = pickle.load(file)

    total_infected = 0
    for property_i in properties:
        if property_i.exposure_date != "NA":
            total_infected += 1

    print(f"Total number of infected premises: {total_infected}")

    return total_infected, undetected_spread_properties_filename, undetected_spread_diseaseoutbreak_filename, undetected_spread_trucks_filename


def trigger_first_report(
    undetected_spread_properties_filename,
    undetected_spread_diseaseoutbreak_filename,
    undetected_spread_trucks_filename,
    state="VIC",
    create_download_folder=False,
    download_parent_folder=None,
):
    ###################################################
    # ---- Code run set up ---------------------------#
    ###################################################

    xrange, yrange, xlims, ylims = x_y_ranges(state)
    # area for first report - anywhere for now
    reportingregion_x = xrange
    reportingregion_y = yrange

    folder_path_main = os.path.join(os.path.dirname(__file__), f"vFMD{state}")

    with open(undetected_spread_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(undetected_spread_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)
    with open(undetected_spread_trucks_filename, "rb") as file:
        trucks_df = pickle.load(file)

    ###################################################
    # ---- Trigger first report ----------------------#
    ###################################################

    # try this herd first, otherwise I'll just trigger any other report
    first_report_herd_id = 25435

    # trigger first report and stop / output
    unique_output = "03_outbreak_detection"
    folder_path_first_report = os.path.join(folder_path_main, unique_output)

    if not os.path.exists(folder_path_first_report):
        os.makedirs(folder_path_first_report)

    spread_properties_filename = os.path.join(folder_path_first_report, "properties_" + unique_output)
    spread_diseaseoutbreak_filename = os.path.join(folder_path_first_report, "outbreakobject_" + unique_output)
    spread_trucks_filename = os.path.join(folder_path_first_report, "trucks_df_" + unique_output)

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
            properties,
            reportingregion_x,
            reportingregion_y,
            output_suffix=output_suffix,
            first_report_herd_id=first_report_herd_id,
            outbreak_sim="FMD",
        )

        # and then resave the end state
        with open(spread_properties_filename, "wb") as file:
            pickle.dump(properties, file)

        # and save the diseaseoutbreak object
        with open(spread_diseaseoutbreak_filename, "wb") as file:
            pickle.dump(diseaseoutbreak, file)

        # though there wouldn't have been any change here
        with open(spread_trucks_filename, "wb") as file:
            pickle.dump(trucks_df, file)

    else:
        with open(spread_properties_filename, "rb") as file:
            properties = pickle.load(file)
        with open(spread_diseaseoutbreak_filename, "rb") as file:
            diseaseoutbreak = pickle.load(file)
        with open(spread_trucks_filename, "rb") as file:
            trucks_df = pickle.load(file)

    FMD_functions.save_approx_known_data(properties, folder_path_first_report, unique_output)

    if create_download_folder:
        if download_parent_folder != None:
            v06_functions.create_separate_download_folder(folder_path_first_report, download_parent_folder, unique_output)
        else:
            v06_functions.create_separate_download_folder(folder_path_first_report, folder_path_main, "download_" + unique_output)

    # ========== LINE 572 - end of the v06_functions.setup_to_outbreak_detection() function =============== #

    approx_data_filename = os.path.join(folder_path_first_report, "approx_known_data_01.csv")

    return (
        folder_path_main,
        folder_path_first_report,
        spread_properties_filename,
        spread_diseaseoutbreak_filename,
        spread_trucks_filename,
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

    VIC = Australia_gdf.loc[Australia_gdf["STE_NAME21"] == "Victoria", :]

    VIC_shape = list(VIC["geometry"])[0]

    return enhanced_passive_surveillance_area.intersection(VIC_shape), enhanced_reporting_factor


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
    ###################################################
    # ---- Code run set up ---------------------------#
    ###################################################

    folder_path_main = os.path.join(os.path.dirname(__file__), f"vFMD{state}")
    xrange, yrange, xlims, ylims = x_y_ranges(state)

    # read in previous state
    previous_spread_properties_filename = os.path.join(folder_path_main, previous_unique_output, "properties_" + previous_unique_output)
    previous_spread_diseaseoutbreak_filename = os.path.join(folder_path_main, previous_unique_output, "outbreakobject_" + previous_unique_output)
    previous_truck_filename = os.path.join(folder_path_main, previous_unique_output, "trucks_df_" + previous_unique_output)

    with open(previous_spread_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(previous_spread_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)
    with open(previous_truck_filename, "rb") as file:
        trucks_df = pickle.load(file)

    # set up for new simulation portion
    folder_path = os.path.join(folder_path_main, unique_output)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    spread_properties_filename = os.path.join(folder_path, "properties_" + unique_output)
    spread_diseaseoutbreak_filename = os.path.join(folder_path, "outbreakobject_" + unique_output)
    spread_trucks_filename = os.path.join(folder_path, "trucks_df_" + unique_output)

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

        properties, movement_records, current_time, total_culled_animals, job_manager, trucks_df = diseaseoutbreak.simulate_HPAI_outbreak_management(
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
            trucks_df=trucks_df,
            outbreak_sim="FMD",
        )

        FMD_functions.save_approx_known_data(properties, folder_path, unique_output="", output_suffix=output_suffix)

        # and then resave the end state
        with open(spread_properties_filename, "wb") as file:
            pickle.dump(properties, file)

        # and save the diseaseoutbreak object
        with open(spread_diseaseoutbreak_filename, "wb") as file:
            pickle.dump(diseaseoutbreak, file)

        # and save the trucks
        with open(spread_trucks_filename, "wb") as file:
            pickle.dump(trucks_df, file)

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
        with open(spread_trucks_filename, "rb") as file:
            trucks_df = pickle.load(file)

    if create_download_folder:
        if download_parent_folder == None:
            download_parent_folder = folder_path_main
        if download_folder_name == None:
            download_folder_name = "download_" + unique_output

        v06_functions.create_separate_download_folder(folder_path, download_parent_folder, download_folder_name)

    approx_data_filename = os.path.join(folder_path, f"approx_known_data{output_suffix}.csv")

    return (
        folder_path_main,
        folder_path,
        spread_properties_filename,
        spread_diseaseoutbreak_filename,
        spread_trucks_filename,
        approx_data_filename,
    )
