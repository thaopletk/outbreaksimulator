import sys
import os
import json
import pickle
import random
import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.simulator as simulator
import simulator.output as output
import simulator.disease_simulation as disease_simulation
import simulator.management as management
import simulator.premises as premises
import simulator.spatial_functions as spatial_functions

from scipy.stats import gaussian_kde
import simulator.spatial_setup as spatial_setup
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, MultiPoint
import shapely.plotting
import contextily as ctx
import pickle
from moviepy.editor import ImageSequenceClip
import geopandas as gpd
from matplotlib_scalebar.scalebar import ScaleBar

from matplotlib.path import Path
from shapely.ops import transform, unary_union


def plot_combined_daily_and_total_notifications(
    xlims, ylims, dates_list, masked_dates_list, daily_notifs, folder_path, save_name
):
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    x_points = list(range(len(dates_list)))
    masked_x_points = list(range(len(masked_dates_list)))

    cumulative = np.cumsum(daily_notifs)

    ax.bar(masked_x_points, daily_notifs)
    # ax.set_xlabel('date', fontsize =14)
    # ax.set_ylabel('cases',fontsize= 14)

    ax.plot(masked_x_points, cumulative, marker="o", markersize=15)

    ax.set_title("Confirmed infected premises", fontsize=16)

    # labels = [item.get_text() for item in ax.get_xticklabels()]
    # labels = [dates_list[x] for x in labels]

    day_spacing = 14
    # if len(daily_notifs) > 20:
    #     day_spacing = 7
    #     if len(daily_notifs) > 50:
    #         day_spacing = 14
    # else:
    #     day_spacing = 2

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    ax.set_xticks(x_points[::day_spacing])
    ax.set_xticklabels([x[:-5] for x in dates_list[::day_spacing]], fontsize=14)  # remove the "/2024"
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=14)

    ax.grid()

    file_name = os.path.join(folder_path, f"{save_name}.png")

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()


def construct_control_zones(properties, source_indices):

    newcontrolzone = {}

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

    # Control area
    control_area = management.define_control_zone_polygons(
        properties,
        source_indices,
        100,  # 100 km
        convex=False,
    )

    control_area = spatial_functions.expand_polygon_to_SALs(control_area)

    control_area = control_area.intersection(Australiashape)

    newcontrolzone["control area"] = control_area

    return newcontrolzone


def plot_premises_with_controls(
    folder_path,
    savename,
    newcontrolzone,
    xlims,
    ylims,
    geometry_culled,
    geometry_confirmed_infected,
    geometry_DCP,
    TPs_undergoing_testing,
    geometry_vaccinated,
    geometry_infected,
    final_vaccination,
):
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

    control_list = ["control area", "restricted area"]
    control_list_plotting = ["restricted area", "control area"]

    for control_type in control_list:

        if control_type in newcontrolzone:
            zone = newcontrolzone[control_type]
            # print(control_type)
            zone = zone.difference(NT_WA)
            try:
                for subpoly in zone.geoms:
                    output.plot_polygon(
                        ax,
                        subpoly,
                        facecolor=colour_dictionary[control_type]["face"],
                        edgecolor=colour_dictionary[control_type]["edge"],
                        alpha=1,
                        label=control_type,
                    )
                # print("subpoly in zone.geoms")
            except:
                output.plot_polygon(
                    ax,
                    zone,
                    facecolor=colour_dictionary[control_type]["face"],
                    edgecolor=colour_dictionary[control_type]["edge"],
                    alpha=1,
                    label=control_type,
                )

    for control_type in control_list_plotting:
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

    if final_vaccination:
        new_geometry_vaccinated = []
        for curr_farm in geometry_vaccinated:
            # curr_farm = Point(long, lat)
            long, lat = curr_farm.xy
            puff_p1 = Polygon(spatial_functions.geodesic_point_buffer(lat, long, km=10))
            new_geometry_vaccinated.append(puff_p1)
        geometry_vaccinated = new_geometry_vaccinated

        geometry_vaccinated = unary_union(geometry_vaccinated)
        geometry_vaccinated = geometry_vaccinated.difference(NT_WA)

        for subpoly in geometry_vaccinated.geoms:
            output.plot_polygon(
                ax,
                subpoly,
                facecolor="#7852a4",
                edgecolor="#4d004d",
                alpha=0.7,
                label="vaccinated premises",
            )

        geometry = [Point(xlims[0] - 0.2, ylims[0] - 0.2)]  # putting the point outside the limits
        # add a fake point to ensure the legend is there
        geo_df = gpd.GeoDataFrame(geometry=geometry)
        geo_df.crs = {"init": "epsg:4326"}
        # plot the marker
        ax = geo_df.plot(
            ax=ax,
            markersize=100,
            color="#7852a4",
            marker="o",
            label="vaccinated premises",
            edgecolor="#4d004d",
            aspect=1,
            alpha=0.7,
        )

    dummy_geometry_beyond_lims = [
        Point(xlims[0], ylims[0]),
        Point(xlims[1], ylims[0]),
        Point(xlims[1], ylims[1]),
        Point(xlims[0], ylims[1]),
    ]

    for geometry, colour, marker, markerlabel, markersize, edgecolour, alpha in [
        [geometry_culled, "cornflowerblue", "P", "resolved premises", 100, "royalblue", 1],
        [geometry_confirmed_infected, "black", "X", "infected premises", 110, "black", 1],
        [geometry_DCP, "#e72918", "v", "dangerous contact premises and suspect premises", 110, "#950000", 1],
        [TPs_undergoing_testing, "#ffa200", "o", "trace premises waiting to be tested", 50, "#ff6600", 1],
        [geometry_infected, "#00ff42", "*", "undetected infected premises", 700, "#0fbc3c", 1],
        [dummy_geometry_beyond_lims, "black", ".", "", 0.00001, "black", 0],
        # [geometry_vaccinated, "#7852a4", "P", "vaccinated premsies", 70,"#7852a4",1],
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

    file_name = os.path.join(folder_path, savename + ".png")
    plt.savefig(file_name, bbox_inches="tight")

    plt.close()
