# to be possibly converted into a test

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import datetime
import json
import pickle

import simulator.spatial_setup as spatial_setup
import simulator.output as output


xrange = [148, 152]
yrange = [-31.9, -29]

folder_path_main = os.path.join(
    os.path.dirname(__file__), "outputs", "October_2024_options"
)
if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)

for n in [100, 500, 1000]:

    set_up_params = {
        "n": n,  # total number of properties to include
        "r": 25,  # note that this should be in KILOMETERS, the maximum wind dispersal distance
        "xrange": xrange,
        "yrange": yrange,
        "average_property_ha": 300,
    }

    # for this, I only need to plot property coordinates, not property size
    property_coordinates, property_polygons, property_areas = (
        spatial_setup.assign_property_locations(
            set_up_params["n"], xrange, yrange, set_up_params["average_property_ha"]
        )
    )

    output.plot_property_coordinates(
        property_coordinates,
        xrange,
        yrange,
        folder_path_main,
        file_name=f"base_map_n_{n}.png",
        colour="black",
    )
