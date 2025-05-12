import sys
import os
import json
import pickle

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import numpy as np

# from shapely.geometry import Point
# import csv
# import math
import matplotlib.pyplot as plt
import simulator.spatial_setup as spatial_setup
import simulator.management as management
import simulator.premises as premises
import simulator.SEIR as SEIR
import simulator.output as output
import simulator.animal_movement as animal_movement
import simulator.spatial_functions as spatial_functions
from shapely.ops import transform, unary_union
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, MultiPoint
import geopandas as gpd
import contextily as ctx
from matplotlib_scalebar.scalebar import ScaleBar


folder_path_main = os.path.join(os.path.dirname(__file__), "outputs", "v03_trial")

undetected_spread_version = 49
detected_spread_version = 12

unique_output = f"{undetected_spread_version}_03_outbreak_detection_{detected_spread_version}"
folder_path_first_report = os.path.join(folder_path_main, unique_output)

#############################################
# read in relevant data--
day = 68

plotting_data_name = os.path.join(folder_path_first_report, f"plotting_data{day}")
with open(plotting_data_name, "rb") as file:
    properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)


xlims = [137, xlims[1]]
ylims = [-37, ylims[1]]

#############################################
newcontrolzone = {}
# construct the control zones
source_indices = []
for i, premise in enumerate(properties):
    if premise.reported_status == True or premise.clinical_report_outcome == True or premise.status == "DCP":
        source_indices.append(i)

# Get current control/etc zones
# Restricted area
restricted_area = management.define_control_zone_polygons(
    properties,
    source_indices,
    80,  # 5 km
    convex=False,
)  # should be zero movement


newcontrolzone["restricted area"] = restricted_area

# define restricted zone for all of Queensland and add to large_movement_restrictions
Queenslandshape = spatial_setup.get_Queensland_shape()
# restricted_area = unary_union([restricted_area, Queenslandshape])

newcontrolzone["additional movement restrictions"] = Queenslandshape

# Control area: less restricted
control_area = management.define_control_zone_polygons(
    properties,
    source_indices,
    100,  # 100 km
    convex=False,
)

control_area = spatial_functions.expand_polygon_to_SALs(control_area)

newcontrolzone["control area"] = control_area

#############################################
# plot

fig, ax = plt.subplots(1, 1, figsize=(20, 15))  # ,figsize=(10,12)

colour_dictionary = {
    "restricted area": {"face": "#cc0000", "edge": "#660000"},
    "control area": {"face": "#ffcc00", "edge": "#cc6600"},
    "additional movement restrictions": {"face": "#8585ad", "edge": "#3d3d5c"},
}

NT_WA = spatial_setup.get_NT_and_WA_shape()

for control_type in ["additional movement restrictions", "control area", "restricted area"]:

    zone = newcontrolzone[control_type]
    print(control_type)
    zone = zone.difference(NT_WA)

    for subpoly in zone.geoms:
        output.plot_polygon(
            ax,
            subpoly,
            facecolor=colour_dictionary[control_type]["face"],
            edgecolor=colour_dictionary[control_type]["edge"],
            alpha=0.4,
            label=control_type,
        )

for control_type in ["restricted area", "control area", "additional movement restrictions"]:

    geometry = [Point(xlims[0] - 0.1, ylims[0] - 0.1)]  # putting the point outside the limits
    # add a fake point to ensure the legend is there
    geo_df = gpd.GeoDataFrame(geometry=geometry)
    geo_df.crs = {"init": "epsg:4326"}
    # plot the marker
    ax = geo_df.plot(
        ax=ax,
        markersize=100,
        color=colour_dictionary[control_type]["face"],
        marker="s",
        label=control_type,
        edgecolor=colour_dictionary[control_type]["edge"],
        aspect=1,
        alpha=0.5,
    )

# will only have these points
geometry_confirmed_infected = []
geometry_DCP = []
geometry_undergoing_testing = []

for index, premise in enumerate(properties):
    long, lat = premise.coordinates
    curr_farm = Point(long, lat)
    if premise.reported_status == True:
        geometry_confirmed_infected.append(curr_farm)
    elif premise.clinical_report_outcome == True or premise.status == "DCP":
        geometry_DCP.append(curr_farm)
    elif premise.undergoing_testing == True:
        geometry_undergoing_testing.append(curr_farm)

# TODO - change these markers potentially
# TODO - add in the legend for the control and restricted areas (unless I use photoshop / powerpoint)
for geometry, colour, marker, markerlabel, markersize, edgecolour in [
    [geometry_confirmed_infected, "black", "X", "infected premises", 120, "black"],
    [geometry_DCP, "#e72918", "v", "dangerous contact premises", 120, "#950000"],
    [geometry_undergoing_testing, "#ffa200", "o", "trace premises", 70, "#ff6600"],
]:

    geo_df = gpd.GeoDataFrame(geometry=geometry)
    geo_df.crs = {"init": "epsg:4326"}
    # plot the marker
    ax = geo_df.plot(
        ax=ax, markersize=markersize, color=colour, marker=marker, label=markerlabel, aspect=1, edgecolor=edgecolour
    )

ctx.add_basemap(
    ax, crs={"init": "epsg:4326"}, source=ctx.providers.CartoDB.Positron
)  # source=ctx.providers.OpenStreetMap.Mapnik


# https://geopandas.org/en/stable/gallery/matplotlib_scalebar.html
points = gpd.GeoSeries([Point(-73.5, 40.5), Point(-74.5, 40.5)], crs=4326)  # Geographic WGS 84 - degrees
points = points.to_crs(32619)  # Projected WGS 84 - meters
distance_meters = points[0].distance(points[1])
ax.add_artist(
    ScaleBar(
        distance_meters,
        box_alpha=0.1,
        location="lower right",
    )
)


ax.axis("off")

ax.set_xlim(xlims)
ax.set_ylim(ylims)

# ax.legend(
#     loc="upper center",
#     bbox_to_anchor=(0.5, 0.0),
#     fancybox=True,
#     shadow=True,
#     ncol=2,
#     fontsize=18,
# )

ax.legend(
    fontsize=18,
)

file_name = f"{time}.png"

file_name = os.path.join(folder_path_first_report, "preworkshop_map_apparent" + file_name)

plt.savefig(file_name, bbox_inches="tight")

plt.close()
