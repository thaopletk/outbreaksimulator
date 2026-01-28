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

# Boundaries for QLD
xrange = [140, 155]
yrange = [-30, -10]

# limits for the figures
xlims = [
    round(xrange[0], 2) - 0.005,
    round(xrange[1], 2) + 0.005,
]
ylims = [
    round(yrange[0], 1) - 0.05,
    round(yrange[1], 1) + 0.05,
]

folder_path_main = os.path.join(os.path.dirname(__file__), "v06_QLD")
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
output_filename = os.path.join(folder_path_main, f"HPAI_QLD_setup_locations{suffix}")
if not os.path.exists(output_filename):
    (
        all_properties,
        chicken_meat_property_coordinates,
        processing_chicken_meat_property_coordinates,
        chicken_egg_property_coordinates,
        processing_chicken_egg_property_coordinates,
    ) = fixed_spatial_setup.HPAI_QLD_setup_locations(output_filename, testing)
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
