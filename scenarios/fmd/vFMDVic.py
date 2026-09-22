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

# # ABC stuff
# import arviz as az
# import pymc as pm


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


def run_seeding_undetected_spread(
    state="VIC",
    burn_in_time=0,
    create_download_folder=False,
    download_parent_folder=None,
    wind_radius=20,
    ABC_mode=False,
    disease_parameters=None,
    max_infected_premises=10000,
    target_infected_properties=18,
):
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
    with open(os.path.join(folder_path_main, "job_parameters.json"), "r") as file:
        job_parameters = json.load(file)
    with open(os.path.join(folder_path_main, "scenario_parameters.json"), "r") as file:
        scenario_parameters = json.load(file)

    if ABC_mode == True or disease_parameters != None:
        pass
        # folder_path_main = os.path.join(os.path.dirname(__file__), f"vFMD{state}", "ABC")
        # if not os.path.exists(folder_path_main):
        #     os.makedirs(folder_path_main)

    else:
        with open(os.path.join(folder_path_main, "disease_parameters.json"), "r") as file:
            disease_parameters = json.load(file)

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
    if ABC_mode == False:
        if not os.path.exists(folder_path_seed):
            os.makedirs(folder_path_seed)

    properties_seeded_filename = os.path.join(folder_path_seed, f"properties_seeded")

    seed_herd_id = 125520
    unique_output = "day0"
    if ABC_mode == False:
        if not os.path.exists(properties_seeded_filename):
            # seed property
            properties, seed_property = FMD_functions.seed_FMD_infection(
                seed_herd_id,
                properties,
                diseaseoutbreak.time,
                xlims,
                ylims,
                folder_path_seed,
                unique_output,
            )
            # and then resave the end state
            with open(properties_seeded_filename, "wb") as file:
                pickle.dump(properties, file)
        else:
            with open(properties_seeded_filename, "rb") as file:
                properties = pickle.load(file)
    else:
        properties, seed_property = FMD_functions.seed_FMD_infection(
            seed_herd_id,
            properties,
            diseaseoutbreak.time,
            xlims,
            ylims,
            folder_path_seed,
            unique_output,
            ABC_mode=ABC_mode,
        )

    ###################################################
    # ---- Undetected spread -------------------------#
    ###################################################
    # spread and then detection after a fixed number of properties infected...

    random.seed(10)
    np.random.seed(10)
    minimum_spread_time = diseaseoutbreak.time + 28

    unique_output = f"02_undetected_spread"
    folder_path_undetected_spread = os.path.join(folder_path_main, unique_output)
    if ABC_mode == False:
        if not os.path.exists(folder_path_undetected_spread):
            os.makedirs(folder_path_undetected_spread)

    undetected_spread_properties_filename = os.path.join(folder_path_undetected_spread, "properties_" + unique_output)
    undetected_spread_diseaseoutbreak_filename = os.path.join(folder_path_undetected_spread, "outbreakobject_" + unique_output)
    undetected_spread_trucks_filename = os.path.join(folder_path_undetected_spread, "trucks_df_" + unique_output)

    spatial_only_parameters["n"] = len(properties)

    total_infected = 0

    if ABC_mode or not os.path.exists(undetected_spread_properties_filename) or not os.path.exists(undetected_spread_diseaseoutbreak_filename):

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
            max_spread_time=minimum_spread_time,
            trucks_df=trucks_df,
            max_infected_premises=max_infected_premises,
            ABC_mode=ABC_mode,
        )

        if ABC_mode == False:
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

        total_infected = 0
        for property_i in properties:
            if property_i.exposure_date != "NA":
                total_infected += 1

        total_infected_properties_with_infected_animals = 0
        total_infected_animals = 0
        for property_i in properties:
            if property_i.number_infected > 0:
                total_infected_properties_with_infected_animals += 1
                total_infected_animals += property_i.number_infected

    else:
        if ABC_mode == False:
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

            total_infected_properties_with_infected_animals = 0
            total_infected_animals = 0
            for property_i in properties:
                if property_i.number_infected > 0:
                    total_infected_properties_with_infected_animals += 1
                    total_infected_animals += property_i.number_infected

    print(f"Total number of infected premises: {total_infected}")
    print(f"Total number of infected premises with infected animals: {total_infected_properties_with_infected_animals}")
    print(f"Total number of infected animals: {total_infected_animals}")

    if ABC_mode:
        first_report_herd_id = 25435

        first_report_i = None
        for i, property in enumerate(properties):
            if "herd_id" in property.FMD_extra_info:
                if first_report_herd_id == property.FMD_extra_info["herd_id"]:
                    first_report_i = i
                    break
        if first_report_i != None:
            # check if it's actually infected or not
            if properties[first_report_i].clinical_date != "NA":
                print("first detected herd successfully found and currently showing clinical signs")
                pass  # good
            elif properties[first_report_i].exposure_date != "NA":
                print("first detected herd is exposed but no clinical signs")
            else:
                print("ideal first detected herd not actually infected")

    if ABC_mode == False:
        return total_infected, undetected_spread_properties_filename, undetected_spread_diseaseoutbreak_filename, undetected_spread_trucks_filename
    else:
        return total_infected, current_time, total_infected_properties_with_infected_animals, total_infected_animals


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


def run_auto_actions(
    state,
    previous_unique_output,
    previous_output_suffix_int=1,
    total_days_to_run_for=7,
    start_action_number_int=1,
    unique_output_starting_int=4,
    create_download_folder=False,
    download_parent_folder=None,
    download_folder_name=None,
    strategy="default",
    shapefile_path=None,
):
    ###################################################
    # ---- Code run set up ---------------------------#
    ###################################################

    folder_path_main = os.path.join(os.path.dirname(__file__), f"vFMD{state}")
    xrange, yrange, xlims, ylims = x_y_ranges(state)

    previous_folder = os.path.join(folder_path_main, previous_unique_output)
    previous_output_suffix = f"_{previous_output_suffix_int:02d}"

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

    RA_shape = None
    CA_shape = None
    EPS_shape = None
    EPS_factor = None
    if shapefile_path != None:
        try:
            shp_zones = gpd.read_file(shapefile_path)
        except:
            shp_zones = gpd.read_file(os.path.join(folder_path_main, shapefile_path))

        # restricted area
        try:
            shp_zones_RA = shp_zones.loc[shp_zones["EMZ"] == "REZ", :]
        except:
            shp_zones_RA = shp_zones.loc[shp_zones["ZoneTitle"] == "Restricted Area", :]
        RA_shape = list(shp_zones_RA["geometry"])[0]

        # control area
        try:
            shp_zones_CA = shp_zones.loc[shp_zones["EMZ"] == "CEZ", :]
        except:
            shp_zones_CA = shp_zones.loc[shp_zones["ZoneTitle"] == "Control Area", :]
        CA_shape = list(shp_zones_CA["geometry"])[0]

        # enhanced passive surveillance area
        try:
            shp_zones_EPS = shp_zones.loc[shp_zones["EMZ_1"] == "Enhanced Passive Surveillance", :]
            EPS_shape = list(shp_zones_EPS["geometry"])[0]  # enhanced passive surveillance shape, assuming it's the same as the RA for now
        except:
            shp_zones_EPS = None

    days_to_run_for = 1

    action_number = start_action_number_int
    running_day = 1
    while running_day <= total_days_to_run_for:
        # get previous info
        approx_data_csv = os.path.join(previous_folder, f"approx_known_data{previous_output_suffix}.csv")
        # set up for new simulation portion
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
        spread_trucks_filename = os.path.join(folder_path, "trucks_df_" + unique_output)

        # assign jobs
        scheduled_date = premises.convert_time_to_date(diseaseoutbreak.time + 1)
        if (
            not os.path.exists(os.path.join(folder_path, f"jobs_{action_number}.csv"))
            or not os.path.exists(os.path.join(folder_path, f"zone_jobs_{action_number}.csv"))
            or not os.path.exists(os.path.join(folder_path, f"zones_{action_number}.csv"))
        ):
            auto_job_mode.generate_jobs_teams_FMD(folder_path, approx_data_csv, scheduled_date, action_number, strategy)

        property_jobs = pd.read_csv(os.path.join(folder_path, f"jobs_{action_number}.csv"))
        zones_based_jobs = pd.read_csv(os.path.join(folder_path, f"zone_jobs_{action_number}.csv"))
        property_based_zones = pd.read_csv(os.path.join(folder_path, f"zones_{action_number}.csv"))

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

            properties, movement_records, current_time, total_culled_animals, job_manager, trucks_df = (
                diseaseoutbreak.simulate_HPAI_outbreak_management(
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

        action_number += 1
        previous_folder = folder_path
        previous_output_suffix = output_suffix
        unique_output_starting_int += 1

        running_day += 1

    return 0


def run_auto_strategies(
    state,
    previous_unique_output,
    previous_output_suffix_int=1,
    total_days_to_run_for=7,
    create_download_folder=False,
    download_parent_folder=None,
    download_folder_name=None,
    strategy="default",
    shapefile_path=None,
):
    ###################################################
    # ---- Code run set up ---------------------------#
    ###################################################

    folder_path_main = os.path.join(os.path.dirname(__file__), f"vFMD{state}")
    xrange, yrange, xlims, ylims = x_y_ranges(state)

    previous_folder = os.path.join(folder_path_main, previous_unique_output)
    previous_output_suffix = f"_{previous_output_suffix_int:02d}"

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

    RA_shape = None
    CA_shape = None
    EPS_shape = None
    EPS_factor = None
    if shapefile_path != None:
        try:
            shp_zones = gpd.read_file(shapefile_path)
        except:
            shp_zones = gpd.read_file(os.path.join(folder_path_main, shapefile_path))

        # restricted area
        try:
            shp_zones_RA = shp_zones.loc[shp_zones["EMZ"] == "REZ", :]
        except:
            shp_zones_RA = shp_zones.loc[shp_zones["ZoneTitle"] == "Restricted Area", :]
        RA_shape = list(shp_zones_RA["geometry"])[0]

        # control area
        try:
            shp_zones_CA = shp_zones.loc[shp_zones["EMZ"] == "CEZ", :]
        except:
            shp_zones_CA = shp_zones.loc[shp_zones["ZoneTitle"] == "Control Area", :]
        CA_shape = list(shp_zones_CA["geometry"])[0]

        # enhanced passive surveillance area
        try:
            shp_zones_EPS = shp_zones.loc[shp_zones["EMZ_1"] == "Enhanced Passive Surveillance", :]
            EPS_shape = list(shp_zones_EPS["geometry"])[0]  # enhanced passive surveillance shape, assuming it's the same as the RA for now
        except:
            shp_zones_EPS = None

    days_to_run_for = 1

    # get previous info
    approx_data_csv = os.path.join(previous_folder, f"approx_known_data_{previous_unique_output}.csv")

    # set up for new simulation portion
    # set up new info
    outputnumber = previous_output_suffix_int + 1
    output_suffix = f"_{outputnumber:02d}"

    unique_output = f"{outputnumber:02d}_{strategy}"
    folder_path = os.path.join(folder_path_main, unique_output)

    print(folder_path)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    spread_properties_filename = os.path.join(folder_path, "properties_" + unique_output)
    spread_diseaseoutbreak_filename = os.path.join(folder_path, "outbreakobject_" + unique_output)
    spread_trucks_filename = os.path.join(folder_path, "trucks_df_" + unique_output)

    running_day = 1
    save_data = False
    while running_day <= total_days_to_run_for:
        if running_day == total_days_to_run_for:
            save_data = True

        if strategy in ["large_CA", "small_CA", "large_CA_1", "small_CA_1"]:
            EPS_factor = 10

            # large CA: 29 IPs; small CA: 31 IPs.
            random.seed(31)
            np.random.seed(53)

            # # large CA: 37
            # random.seed(1)
            # np.random.seed(1)

            # small CA: 35 IPs, large CA: 34 IPs - no EPS factor change
            # random.seed(6131)
            # np.random.seed(1261653)
        elif "surveillance_focus" in strategy or "cull_focus" in strategy:
            EPS_factor = 20

            # random.seed(1331)
            # np.random.seed(3153)

            # small CA 70 IPs, large CA like 96 IPS...
            # random.seed(113413)
            # np.random.seed(534522)

            # small CA 100 ip;  large CA 47 IP
            # after increasing resourcing; 75 IPs for small CA, 55 IPs for large CA...  [for culling focus]
            random.seed(31)
            np.random.seed(53)

            # small CA cull focus: 76 IPs, large CA: 82 IPs ???
            # random.seed(631)
            # np.random.seed(1261)

            # large CA surveillance: 82 IPs, smal lCA surveillance focus: 92 IPs..., small CA cull focus: 74 IPs... (before increase in teams)
            # random.seed(6131)
            # np.random.seed(1261653)

        elif "initial_investigation" in strategy:
            random.seed(1235)
            np.random.seed(1116)
        elif "national_standstill" in strategy:
            EPS_factor = 10

            #  24 IPs
            random.seed(472)
            np.random.seed(6092)

            # # 26 IPS
            # random.seed(12532)
            # np.random.seed(11326)

            # 27 IPs
            # random.seed(125)
            # np.random.seed(116)
        else:
            EPS_factor = 10
            random.seed(1235)
            np.random.seed(1116)
        # assign jobs
        scheduled_date = premises.convert_time_to_date(diseaseoutbreak.time + 1)
        auto_job_mode.generate_jobs_teams_FMD(folder_path, approx_data_csv, scheduled_date, running_day, strategy)

        property_jobs = pd.read_csv(os.path.join(folder_path, f"jobs_{running_day}.csv"))
        zones_based_jobs = pd.read_csv(os.path.join(folder_path, f"zone_jobs_{running_day}.csv"))
        property_based_zones = pd.read_csv(os.path.join(folder_path, f"zones_{running_day}.csv"))

        # construct zones
        enhanced_passive_surveillance_area, enhanced_reporting_factor = get_enhanced_passive_surveillance_area(property_based_zones, properties)

        if EPS_shape != None:
            enhanced_passive_surveillance_area = unary_union([enhanced_passive_surveillance_area, EPS_shape])
        if EPS_factor != None:
            enhanced_reporting_factor = EPS_factor

        # adjust the plotting parameters for this new scenario
        diseaseoutbreak.set_plotting_parameters(
            xlims=xlims,
            ylims=ylims,
            plotting=True,
            folder_path=folder_path,
            unique_output=unique_output,
        )

        if "national_standstill" in strategy:
            diseaseoutbreak.clinical_reporting_threshold = 0.01  # reducing the reporting threshold

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
            save_data=save_data,
            strategy=strategy,
        )

        if running_day == total_days_to_run_for:
            FMD_functions.save_approx_known_data(properties, folder_path, unique_output=unique_output)
            approx_data_csv = os.path.join(folder_path, f"approx_known_data_{unique_output}.csv")
        else:
            FMD_functions.save_approx_known_data(properties, folder_path, unique_output="", output_suffix=f"{output_suffix}_{running_day}")
            approx_data_csv = os.path.join(folder_path, f"approx_known_data{output_suffix}_{running_day}.csv")

        running_day += 1

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

    total_infected_properties_with_infected_animals = 0
    total_infected_animals = 0
    for property_i in properties:
        if property_i.number_infected > 0:
            total_infected_properties_with_infected_animals += 1
            total_infected_animals += property_i.number_infected

    print(f"Total number of infected premises: {total_infected}")
    print(f"Total number of infected premises with infected animals: {total_infected_properties_with_infected_animals}")
    print(f"Total number of infected animals: {total_infected_animals}")

    if create_download_folder:
        if download_parent_folder == None:
            download_parent_folder = folder_path_main
        if download_folder_name == None:
            download_folder_name = "download_" + unique_output

        v06_functions.create_separate_download_folder(folder_path, download_parent_folder, download_folder_name)

    return 0


# def undetected_spread_sim(rng, cattle_wind, cattle_beta, pigs_wind, pigs_beta, sheep_wind, sheep_beta,size=None):

#     disease_parameters = {
#             "cattle": {"beta_wind": cattle_wind,
#             "beta_animal": cattle_beta,
#             "latent_period": 2,
#             "infectious_period": 10,
#             "preclinical_period": 3,
#             "pre-clinical_period": 3
#         },
#             "pigs":{"beta_wind": pigs_wind,
#             "beta_animal": pigs_beta,
#             "latent_period": 1,
#             "infectious_period": 10,
#             "preclinical_period":3,
#             "pre-clinical_period": 3
#         },
#             "sheep": {"beta_wind": sheep_wind,
#             "beta_animal": sheep_beta,
#             "latent_period": 5,
#             "infectious_period": 10,
#             "preclinical_period": 3,
#             "pre-clinical_period": 3
#         }
#     }
#     total_infected, undetected_spread_properties_filename, undetected_spread_diseaseoutbreak_filename, undetected_spread_trucks_filename =run_seeding_undetected_spread(state="VIC", burn_in_time=0, create_download_folder=False, download_parent_folder=None, wind_radius=20,ABC_mode = True,disease_parameters = disease_parameters)

#     return total_infected


def ABC(state="VIC", grid_size=5):
    # total_runs=100,
    total_infected_aim = 18  # or something like this - double check

    successful_saves = 0

    folder_path_main = os.path.join(os.path.dirname(__file__), f"vFMD{state}")
    folder_path_main_ABC_params = os.path.join(folder_path_main, "ABC_params")
    if not os.path.exists(folder_path_main_ABC_params):
        os.makedirs(folder_path_main_ABC_params)

    # for run in range(total_runs):
    data_space = []
    for beta_wind in np.linspace(0.009, 0.012, grid_size):
        for beta_animal in np.linspace(0.18, 0.22, grid_size):
            for pig_multiplier in np.linspace(1.6, 1.7, grid_size):
                for sheep_multiplier in np.linspace(0.15, 0.25, grid_size):

                    start_time = time.time()
                    # hmmm maybe rather than random, I should actually be stepping down/up in the parameter space
                    # beta_wind = np.random.uniform(0.0001, 0.4)
                    # beta_animal = np.random.uniform(0.01, 0.5)
                    # pig_multiplier = np.random.uniform(1, 3)
                    # sheep_multiplier = np.random.uniform(0.2, 1.2)

                    disease_parameters = {
                        "cattle": {
                            "beta_wind": beta_wind,
                            "beta_animal": beta_animal,
                            "latent_period": 2,
                            "infectious_period": 10,
                            "preclinical_period": 3,
                            "pre-clinical_period": 3,
                        },
                        "pigs": {
                            "beta_wind": beta_wind * pig_multiplier,
                            "beta_animal": beta_animal * pig_multiplier,
                            "latent_period": 1,
                            "infectious_period": 10,
                            "preclinical_period": 3,
                            "pre-clinical_period": 3,
                        },
                        "sheep": {
                            "beta_wind": beta_wind * sheep_multiplier,
                            "beta_animal": beta_animal * sheep_multiplier,
                            "latent_period": 5,
                            "infectious_period": 10,
                            "preclinical_period": 3,
                            "pre-clinical_period": 3,
                        },
                    }

                    print(disease_parameters)

                    (
                        total_infected,
                        undetected_spread_properties_filename,
                        undetected_spread_diseaseoutbreak_filename,
                        undetected_spread_trucks_filename,
                    ) = run_seeding_undetected_spread(
                        state="VIC",
                        burn_in_time=0,
                        create_download_folder=False,
                        download_parent_folder=None,
                        wind_radius=20,
                        ABC_mode=True,
                        disease_parameters=disease_parameters,
                        max_infected_premises=total_infected_aim + 1,
                    )

                    data_space.append([beta_wind, beta_animal, pig_multiplier, sheep_multiplier, total_infected])

                    if total_infected >= total_infected_aim - 1 and total_infected <= total_infected_aim + 1:
                        # accept the parameters ; delete the runs ; and start again
                        with open(os.path.join(folder_path_main_ABC_params, f"disease_parameters_{successful_saves}.json"), "w") as f:
                            json.dump(disease_parameters, f)

                        successful_saves += 1

                    for filename in os.listdir(os.path.join(os.path.dirname(__file__), f"vFMD{state}", "ABC")):
                        file_path = os.path.join(os.path.join(os.path.dirname(__file__), f"vFMD{state}", "ABC"), filename)
                        try:
                            if os.path.isfile(file_path) or os.path.islink(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                        except Exception as e:
                            print("Failed to delete %s. Reason: %s" % (file_path, e))

                    end_time = time.time()
                    execution_time = end_time - start_time
                    print(f"Execution time of an ABC run: {execution_time/60} minutes")
    data_space = pd.DataFrame(data_space, columns=["beta_wind", "beta_animal", "pig_multiplier", "sheep_multiplier", "total_infected"])
    data_space.to_csv(os.path.join(folder_path_main_ABC_params, f"data_space.csv"), index=False)


# if __name__ == "__main__":
# # def ABC_pyMC():
#     with pm.Model() as model_lv:
#         # Priors
#         cattle_wind = pm.HalfNormal("cattle_wind", 1.0)
#         cattle_beta  = pm.HalfNormal("cattle_beta", 1.0)
#         pigs_wind = pm.HalfNormal("pigs_wind", 1.0)
#         pigs_beta = pm.HalfNormal("pigs_beta", 1.0)
#         sheep_wind = pm.HalfNormal("sheep_wind", 1.0)
#         sheep_beta = pm.HalfNormal("sheep_beta", 1.0)

#         observed = 18
#         # Likelihood (ABC). Epsilon is the initial tolerance
#         sim = pm.Simulator("sim", undetected_spread_sim, params=(cattle_wind, cattle_beta, pigs_wind, pigs_beta, sheep_wind, sheep_beta), epsilon=10, observed=observed)
#         # Inference
#         samples = pm.sample_smc(draws=500, chains=4, threshold=0.3, correlation_threshold=0.1)
#         # Convert to ArviZ InferenceData
#         posterior = samples.posterior.stack(samples=("draw", "chain"))
#         # post = posterior.to_pandas()

#     az.summary(samples, hdi_prob=0.95)
