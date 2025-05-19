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
import pandas as pd

# from matplotlib.patches import Rectangle
from matplotlib.path import Path


folder_path_main = os.path.join(os.path.dirname(__file__), "outputs", "v03_trial")

undetected_spread_version = 49
detected_spread_version = 12


unique_output = f"{undetected_spread_version}_04_two_weeks_{detected_spread_version}"
folder_path = os.path.join(folder_path_main, unique_output)

#############################################
# read in relevant data--
day = 82

plotting_data_name = os.path.join(folder_path, f"plotting_data{day}")
with open(plotting_data_name, "rb") as file:
    properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

diseaseoutbreak_filename = os.path.join(folder_path, f"outbreakobject_{unique_output}")
with open(diseaseoutbreak_filename, "rb") as file:
    diseaseoutbreak = pickle.load(file)

narrative = pd.read_csv(os.path.join(folder_path, "combinated_narrative.csv"))

reported = narrative[narrative["type"] == "report"]

reported_narrative = reported[reported["report"].str.contains("has been reported possible infection")]

self_reported_list = reported_narrative["property"].values.tolist()
self_reported_list = [int(x) for x in self_reported_list]

print(self_reported_list)

# xlims = [137, xlims[1]]
# ylims = [-37, ylims[1]]

#############################################
newcontrolzone = {}
# construct the control zones
source_indices = []
for i, premise in enumerate(properties):
    if premise.reported_status == True or premise.clinical_report_outcome == True or premise.status == "DCP":
        source_indices.append(i)
    else:
        if i in self_reported_list:
            source_indices.append(i)

# Get current control/etc zones
# Restricted area
restricted_area = management.define_control_zone_polygons(
    properties,
    source_indices,
    80,  # 5 km
    convex=False,
)  # should be zero movement

Australiashape = spatial_setup.Australia_shape()

newcontrolzone["restricted area"] = restricted_area.intersection(Australiashape)

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

# colour_dictionary = {
#     "restricted area": {"face": "#cc0000", "edge": "#660000"},
#     "control area": {"face": "#ffcc00", "edge": "#cc6600"},
#     "additional movement restrictions": {"face": "#8585ad", "edge": "#3d3d5c"},
# }

colour_dictionary = {
    "restricted area": {"face": "#e07b7b", "edge": "#660000"},
    "control area": {"face": "#fce27b", "edge": "#cc6600"},
    "additional movement restrictions": {"face": "#bdbdd1", "edge": "#3d3d5c"},
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
            alpha=1,
            label=control_type,
        )

for control_type in ["restricted area", "control area", "additional movement restrictions"]:

    # geometry = [Point(xlims[0] - 0.1, ylims[0] - 0.1)]  # putting the point outside the limits
    # # add a fake point to ensure the legend is there
    # geo_df = gpd.GeoDataFrame(geometry=geometry)
    # geo_df.crs = {"init": "epsg:4326"}
    # # plot the marker
    # ax = geo_df.plot(
    #     ax=ax,
    #     markersize=100,
    #     color=colour_dictionary[control_type]["face"],
    #     marker="s",
    #     label=control_type,
    #     edgecolor=colour_dictionary[control_type]["edge"],
    #     aspect=1,
    #     alpha=0.5,
    # )
    # ax.add_patch(Rectangle((xlims[0] - 1, ylims[0] - 1), 0.9, 0.5,
    #          edgecolor = colour_dictionary[control_type]["edge"],
    #          facecolor = colour_dictionary[control_type]["face"],
    #          fill=True,
    #          label=control_type,
    #          alpha=0.5,
    #          lw=0.05))

    verts = [
        (-1, -0.5),  # left, bottom
        (-1, 0.5),  # left, top
        (1.0, 0.5),  # right, top
        (1.0, -0.5),  # right, bottom
        (-1.0, -0.5),  # back to left, bottom
    ]

    codes = [
        Path.MOVETO,  # begin drawing
        Path.LINETO,  # straight line
        Path.LINETO,
        Path.LINETO,
        Path.CLOSEPOLY,  # close shape. This is not required for this shape but is "good form"
    ]

    path = Path(verts, codes)

    geometry = [Point(xlims[0] - 0.2, ylims[0] - 0.2)]  # putting the point outside the limits
    # add a fake point to ensure the legend is there
    geo_df = gpd.GeoDataFrame(geometry=geometry)
    geo_df.crs = {"init": "epsg:4326"}
    ax = geo_df.plot(
        ax=ax,
        markersize=400,
        color=colour_dictionary[control_type]["face"],
        marker=path,
        label=control_type,
        edgecolor=colour_dictionary[control_type]["edge"],
        aspect=1,
        alpha=1,
    )

# will only have these points
geometry_culled = []
geometry_confirmed_infected = []
geometry_DCP = []
geometry_undergoing_testing = []

TPs = []

for index, premise in enumerate(properties):
    long, lat = premise.coordinates
    curr_farm = Point(long, lat)
    if premise.culled_status == True:
        geometry_culled.append(curr_farm)

        contact_tracing_report, traced_property_indices = management.contact_tracing(
            properties, index, diseaseoutbreak.movement_records, time
        )
        TPs.extend(traced_property_indices)

    elif premise.reported_status == True:
        geometry_confirmed_infected.append(curr_farm)

        contact_tracing_report, traced_property_indices = management.contact_tracing(
            properties, index, diseaseoutbreak.movement_records, time
        )
        TPs.extend(traced_property_indices)

    elif premise.clinical_report_outcome == True or premise.status == "DCP" or index in self_reported_list:
        geometry_DCP.append(curr_farm)

        contact_tracing_report, traced_property_indices = management.contact_tracing(
            properties, index, diseaseoutbreak.movement_records, time
        )
        TPs.extend(traced_property_indices)

    elif premise.undergoing_testing == True:
        geometry_undergoing_testing.append(curr_farm)


TPs = list(set(TPs))

final_TPs = []
TPs_undergoing_testing = []
TPs_false_result = []
for index in TPs:
    if index in geometry_culled or index in geometry_confirmed_infected or index in geometry_DCP:
        pass
    else:
        long, lat = properties[index].coordinates
        curr_farm = Point(long, lat)
        final_TPs.append(curr_farm)
        if properties[index].clinical_report_outcome == False:
            if properties[index].undergoing_testing == True:
                TPs_undergoing_testing.append(curr_farm)  # aka, it's still waiting for a lab test...
            else:
                TPs_false_result.append(curr_farm)
        elif (
            properties[index].undergoing_testing == True
        ):  # clinical_report_outcome == None; means that it's waiting for a clinical team AND a lab test
            TPs_undergoing_testing.append(curr_farm)


print(f"TPs_undergoing_testing: {len(TPs_undergoing_testing)}")
print(f"TPs_false_result: {len(TPs_false_result)}")

# TODO - change these markers potentially
# TODO - add in the legend for the control and restricted areas (unless I use photoshop / powerpoint)
for geometry, colour, marker, markerlabel, markersize, edgecolour, alpha in [
    [geometry_culled, "cornflowerblue", "P", "resolved premises", 110, "royalblue", 1],
    [geometry_confirmed_infected, "black", "X", "infected premises", 110, "black", 1],
    [geometry_DCP, "#e72918", "v", "dangerous contact premises and suspect premises", 110, "#950000", 1],
    # [geometry_undergoing_testing, "#ffa200", "o", "TPs, PORs, ARPs, PSS scheduled for testing", 5, "#ff6600",0.3],
    # [final_TPs, "#ffa200", "o", "trace premises", 50, "#ff6600",1],
]:

    geo_df = gpd.GeoDataFrame(geometry=geometry)
    geo_df.crs = {"init": "epsg:4326"}
    # plot the marker
    ax = geo_df.plot(
        ax=ax,
        markersize=markersize,
        color=colour,
        marker=marker,
        label=markerlabel,
        aspect=1,
        edgecolor=edgecolour,
        alpha=alpha,
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

file_name_ending = f"{time}.png"

file_name = os.path.join(folder_path, "workshop_p1_map_apparent" + file_name_ending)
plt.savefig(file_name, bbox_inches="tight")


plt.close()


# what about a close up with just the trace premises?

fig, ax = plt.subplots(1, 1, figsize=(20, 15))  # ,figsize=(10,12)


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
            alpha=1,
            label=control_type,
        )

for control_type in ["restricted area", "control area", "additional movement restrictions"]:

    # geometry = [Point(xlims[0] - 0.1, ylims[0] - 0.1)]  # putting the point outside the limits
    # # add a fake point to ensure the legend is there
    # geo_df = gpd.GeoDataFrame(geometry=geometry)
    # geo_df.crs = {"init": "epsg:4326"}
    # # plot the marker
    # ax = geo_df.plot(
    #     ax=ax,
    #     markersize=100,
    #     color=colour_dictionary[control_type]["face"],
    #     marker="s",
    #     label=control_type,
    #     edgecolor=colour_dictionary[control_type]["edge"],
    #     aspect=1,
    #     alpha=0.5,
    # )
    # ax.add_patch(Rectangle((xlims[0] - 1, ylims[0] - 1), 0.9, 0.5,
    #          edgecolor = colour_dictionary[control_type]["edge"],
    #          facecolor = colour_dictionary[control_type]["face"],
    #          fill=True,
    #          label=control_type,
    #          alpha=0.5,
    #          lw=0.05))

    verts = [
        (-1, -0.5),  # left, bottom
        (-1, 0.5),  # left, top
        (1.0, 0.5),  # right, top
        (1.0, -0.5),  # right, bottom
        (-1.0, -0.5),  # back to left, bottom
    ]

    codes = [
        Path.MOVETO,  # begin drawing
        Path.LINETO,  # straight line
        Path.LINETO,
        Path.LINETO,
        Path.CLOSEPOLY,  # close shape. This is not required for this shape but is "good form"
    ]

    path = Path(verts, codes)

    geometry = [Point(xlims[0] - 0.2, ylims[0] - 0.2)]  # putting the point outside the limits
    # add a fake point to ensure the legend is there
    geo_df = gpd.GeoDataFrame(geometry=geometry)
    geo_df.crs = {"init": "epsg:4326"}
    ax = geo_df.plot(
        ax=ax,
        markersize=400,
        color=colour_dictionary[control_type]["face"],
        marker=path,
        label=control_type,
        edgecolor=colour_dictionary[control_type]["edge"],
        aspect=1,
        alpha=1,
    )


for geometry, colour, marker, markerlabel, markersize, edgecolour, alpha in [
    [TPs_undergoing_testing, "#ffa200", "o", "trace premises waiting to be tested", 50, "#ff6600", 1],
    # [TPs_false_result, "#ffa200", "o", "trace premises with negative result", 50, "#ff6600",1],
]:

    geo_df = gpd.GeoDataFrame(geometry=geometry)
    geo_df.crs = {"init": "epsg:4326"}
    # plot the marker
    ax = geo_df.plot(
        ax=ax,
        markersize=markersize,
        color=colour,
        marker=marker,
        label=markerlabel,
        aspect=1,
        edgecolor=edgecolour,
        alpha=alpha,
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

ax.legend(
    fontsize=18,
)

ax.set_xlim([137, 154])
ax.set_ylim([-29, -10])
file_name = os.path.join(folder_path, "workshop_p1_map_apparent_QLD_" + file_name_ending)
plt.savefig(file_name, bbox_inches="tight")

ax.set_xlim([xlims[0], 142])
ax.set_ylim([-39, -25])
file_name = os.path.join(folder_path, "workshop_p1_map_apparent_SA_" + file_name_ending)
plt.savefig(file_name, bbox_inches="tight")

ax.legend(
    loc="lower left",
)

ax.set_xlim([140, 154])
ax.set_ylim([-38, -28])
file_name = os.path.join(folder_path, "workshop_p1_map_apparent_NSW_" + file_name_ending)
plt.savefig(file_name, bbox_inches="tight")


ax.set_xlim([140, 152])
ax.set_ylim([-40, -33])
file_name = os.path.join(folder_path, "workshop_p1_map_apparent_VIC_" + file_name_ending)
plt.savefig(file_name, bbox_inches="tight")


plt.close()
