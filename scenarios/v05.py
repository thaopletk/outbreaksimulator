""" v0.5

    This script runs code to simulate an FMD outbreak seeded in Victoria

"""

import sys
import os
import json
import pickle
import random
import numpy as np
import subprocess


sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.simulator as simulator
import simulator.output as output
import simulator.disease_simulation as disease_simulation
import simulator.management as management
import simulator.premises as premises
import simulator.spatial_functions as spatial_functions

folder_path_main = os.path.join(os.path.dirname(__file__), "v05")
folder_path_seed = os.path.join(folder_path_main, "01_seed")

# make main folder if it doesn't exist
if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)

# generate map and properties
# extension: generate a random map using, e.g., perlin noise

small_ver = "_small"  # for testing purposes
# small_ver = ""  # for running on the cluster


properties_filename = os.path.join(folder_path_main, "properties_init")

random.seed(1)
np.random.seed(1)

if not os.path.exists(properties_filename):
    # set up properties
    pass
else:
    # load properties
    with open(properties_filename, "rb") as file:
        properties = pickle.load(file)
