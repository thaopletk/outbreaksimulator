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

# import simulator.simulator as simulator
import simulator.disease_simulation as disease_simulation
import simulator.management as management

# import simulator.management as management
import simulator.premises as premises


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
        ) = fixed_spatial_setup.FMD_VIC_setup_locations(output_filename)

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
