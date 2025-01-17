# to be possibly converted into a test

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import datetime
import json
import pickle

import simulator.spatial_setup as spatial_setup
import simulator.output as output


xrange = [130, 155]
yrange = [-39, -24]

set_up_params = {
    "n": 40,  # total number of properties to include
    "r": 25,  # note that this should be in KILOMETERS, the maximum wind dispersal distance
    "xrange": xrange,
    "yrange": yrange,
    "average_property_ha": 3000,
}


folder_path_main = os.path.join(os.path.dirname(__file__), "outputs", "temp")
if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)

(
    property_coordinates,
    adjacency_matrix,
    neighbour_pairs,
    neighbourhoods,
    property_polygons,
    property_polygons_puffed,
    property_areas,
) = spatial_setup.generate_properties_with_land(
    set_up_params["n"], set_up_params["r"], xrange, yrange, set_up_params["average_property_ha"]
)


output.plot_map_land(property_polygons, property_polygons_puffed, xrange, yrange, folder_path_main)
