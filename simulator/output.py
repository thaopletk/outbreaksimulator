""" Data visualisation and pickle outputs

    Based on FMD_modelling plotting_code.py, but adapted for "real locations" (i.e. spatially located).

    This script produces output plots (static, gifs and mp4 animations) of the outbreak.

"""

from matplotlib.path import Path
from matplotlib.patches import PathPatch
from matplotlib.collections import PatchCollection
from matplotlib_scalebar.scalebar import ScaleBar
from matplotlib import markers
import numpy as np
import os
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, MultiPoint
import geopandas as gpd
import contextily as ctx
import pickle
from moviepy.editor import ImageSequenceClip
from simulator.premises import convert_time_to_date


def plot_polygon(ax, poly, **kwargs):
    """Plot a polygon

    Based on code from https://coderslegacy.com/python/plotting-shapely-polygons-with-interiors-holes/

    """
    path = Path.make_compound_path(
        Path(np.asarray(poly.exterior.coords)[:, :2]),
        *[Path(np.asarray(ring.coords)[:, :2]) for ring in poly.interiors],
    )

    patch = PathPatch(path, **kwargs)
    collection = PatchCollection([patch], **kwargs)

    ax.add_collection(collection, autolim=True)
    ax.autoscale_view()
    return collection


def plot_property_coordinates(
    property_coordinates,
    xlims,
    ylims,
    folder_path,
    file_name="base_map.png",
    colour="orange",
):
    """Plot properties' coordinates (centers) only"""

    fig, ax = plt.subplots(1, 1, figsize=(20, 15))  # ,figsize=(10,12)

    farms = []
    for coords in property_coordinates:
        long, lat = coords
        curr_farm = Point(long, lat)
        farms.append(curr_farm)

    markersize = 30

    marker = "o"
    markerlabel = "susceptible"

    geo_df = gpd.GeoDataFrame(geometry=farms)
    geo_df.crs = {"init": "epsg:4326"}
    ax = geo_df.plot(ax=ax, markersize=markersize, color=colour, marker=marker, label=markerlabel)

    ctx.add_basemap(ax, crs={"init": "epsg:4326"}, source=ctx.providers.OpenStreetMap.Mapnik)

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

    ax.set_title("Map", fontsize=18)

    ax.set_ylabel("latitude", fontsize=16)
    ax.set_xlabel("longitude", fontsize=16)

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
    #       fancybox=True, shadow=True, ncol=5,fontsize=18)

    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    file_name = os.path.join(folder_path, file_name)

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()


def plot_map_land(property_polygons, property_polygons_puffed, xlims, ylims, folder_path):
    """Plot property boundaries"""
    fig, ax = plt.subplots(1, 1, figsize=(20, 15))  # ,figsize=(10,12)

    for poly in property_polygons_puffed:
        plot_polygon(ax, poly, facecolor="tomato", edgecolor="maroon", alpha=0.01)

    for poly in property_polygons:
        plot_polygon(ax, poly, facecolor="tomato", edgecolor="maroon", alpha=1)

    ctx.add_basemap(ax, crs={"init": "epsg:4326"}, source=ctx.providers.OpenStreetMap.Mapnik)

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

    ax.set_title("Map", fontsize=18)

    ax.set_ylabel("latitude", fontsize=16)
    ax.set_xlabel("longitude", fontsize=16)

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
    #       fancybox=True, shadow=True, ncol=5,fontsize=18)

    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    file_name = "base_map.png"

    file_name = os.path.join(folder_path, file_name)

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()


def plot_map(
    properties,
    time,
    xlims,
    ylims,
    folder_path,
    real_situation=True,
    controlzone=None,
    infectionpoly=False,
    contacts_for_plotting={},
):
    """Plot map during an outbreak

    Parameters
    ----------
    properties : list of premises
        list of properties (Premises objects)
    time : int
        current simulation time (will be converted into a date)
    xlims : list
        the figure's x-limits
    ylims : list
        the figure's y-limits
    folder_path : str
        save location for the image
    controlzone : dict of polygons
        Dictionary containing any control zones to be plotted. Currently accepts control zones for movement restrictions, ring vaccination, and ring culling
    infectionpoly : bool
        determines whether to plot an extra polygon to show the 'shape' of infected properties
    contacts_for_plotting : dict of property indices
        in form [source-property] : [properties that it had sent animals to recently], to plot the results of contact tracing


    """
    fig, ax = plt.subplots(1, 1, figsize=(20, 15))  # ,figsize=(10,12)

    colour_dictionary = {
        "movement restrictions": "tomato",
        "ring vaccination": "deepskyblue",
        "ring culling": "black",
        "ring testing": "green",
    }

    if controlzone != None and controlzone != {}:
        for control_type, zone in controlzone.items():
            if zone != None:
                try:
                    plot_polygon(
                        ax,
                        zone,
                        facecolor=colour_dictionary[control_type],
                        edgecolor="maroon",
                        alpha=0.2,
                        label=control_type,
                    )

                except:
                    for subpoly in zone:
                        plot_polygon(
                            ax,
                            subpoly,
                            facecolor=colour_dictionary[control_type],
                            edgecolor="maroon",
                            alpha=0.2,
                            label=control_type,
                        )

    geometry_infected = []
    geometry_confirmed_infected = []
    geometry_culled = []
    geometry_vaccinated = []
    geometry_susceptible = []
    geometry_culled_on_suspicion = []
    geomtry_culled_on_suspicion_actually_infected = []
    geometry_undergoing_testing = []

    for key, value in contacts_for_plotting.items():
        premise = properties[key]
        for contact_index in value:
            contact = properties[contact_index]
            plt.plot(
                [premise.coordinates[0], contact.coordinates[0]],
                [premise.coordinates[1], contact.coordinates[1]],
                alpha=0.5,
                color="black",
            )

    if real_situation == True:  # i.e. plotting the underlying situation
        network_label_switch = False

        infected_coords = []

        # for index, premise in enumerate(properties):
        #     long, lat = premise.coordinates
        #     curr_farm = Point(long, lat)

        #     # plot neighbours using edges
        #     for farm in premise.neighbourhood:
        #         # neigh = Point(property_coordinates[farm[0], 0],property_coordinates[farm[0], 1])
        #         # network.append(LineString(curr_farm,neigh))

        #         # plots the lines between locations
        #         if network_label_switch == False:
        #             plt.plot(
        #                 [premise.coordinates[0], property_coordinates[farm[0], 0]],
        #                 [premise.coordinates[1], property_coordinates[farm[0], 1]],
        #                 alpha=0.01,
        #                 color="black",
        #                 label="network",
        #             )
        #             network_label_switch = (
        #                 True  # to make sure that the labelling only occurs once
        #             )
        #         else:
        #             plt.plot(
        #                 [premise.coordinates[0], property_coordinates[farm[0], 0]],
        #                 [premise.coordinates[1], property_coordinates[farm[0], 1]],
        #                 alpha=0.01,
        #                 color="black",
        #             )

        for index, premise in enumerate(properties):
            long, lat = premise.coordinates
            curr_farm = Point(long, lat)
            if premise.culled_status:
                if premise.reported_status:
                    geometry_culled.append(curr_farm)
                    infected_coords.append(premise.coordinates)
                elif premise.culled_on_suspicion:

                    if premise.cumulative_infections > 0:
                        geomtry_culled_on_suspicion_actually_infected.append(curr_farm)
                    else:
                        geometry_culled_on_suspicion.append(curr_farm)

                else:
                    raise Exception("Culled yet neither reported nor culled on suspicion")
            elif premise.reported_status == True:
                geometry_confirmed_infected.append(curr_farm)
                infected_coords.append(premise.coordinates)
            elif premise.infection_status:
                geometry_infected.append(curr_farm)
                infected_coords.append(premise.coordinates)
            elif premise.vaccination_status:
                geometry_vaccinated.append(curr_farm)
            else:
                geometry_susceptible.append(curr_farm)
        if infectionpoly == True:
            if len(infected_coords) > 2:
                infection_hull = MultiPoint(infected_coords).convex_hull
                plot_polygon(
                    ax,
                    infection_hull,
                    facecolor="purple",
                    edgecolor="purple",
                    alpha=0.2,
                    label="infection polygon",
                )
            # TODO should consider the case of when it's smaller...

    else:  # Apparent situation

        infected_coords = []

        for index, premise in enumerate(properties):
            long, lat = premise.coordinates
            curr_farm = Point(long, lat)

            if premise.culled_status:
                if premise.reported_status:
                    geometry_culled.append(curr_farm)
                    infected_coords.append(premise.coordinates)

                elif premise.culled_on_suspicion:
                    geometry_culled_on_suspicion.append(curr_farm)
                else:
                    raise Exception("Culled yet neither reported nor culled on suspicion")
            elif premise.reported_status == True:
                geometry_confirmed_infected.append(curr_farm)
                infected_coords.append(premise.coordinates)
            elif premise.undergoing_testing == True:
                geometry_undergoing_testing.append(curr_farm)
            elif premise.vaccination_status:
                geometry_vaccinated.append(curr_farm)
            else:
                geometry_susceptible.append(curr_farm)

        if infectionpoly == True:
            if len(infected_coords) > 2:
                infection_hull = MultiPoint(infected_coords).convex_hull
                plot_polygon(
                    ax,
                    infection_hull,
                    facecolor="purple",
                    edgecolor="purple",
                    alpha=0.2,
                    label="infection polygon",
                )

    for geometry, colour, marker, markerlabel, markersize in [
        [geometry_infected, "purple", "x", "infected", 30],
        [geometry_confirmed_infected, "firebrick", markers.CARETDOWN, "confirmed infection", 150],
        [geometry_culled, "firebrick", "X", "culled on confirmation", 150],
        [geometry_culled_on_suspicion, "black", "X", "culled on suspicion", 150],
        [
            geomtry_culled_on_suspicion_actually_infected,
            "purple",
            "X",
            "culled on suspicion, actually infected",
            150,
        ],
        [geometry_undergoing_testing, "orange", r"$?$", "undergoing testing", 200],
        [geometry_vaccinated, "deepskyblue", "s", "vaccinated", 100],
        [geometry_susceptible, "orange", "o", "susceptible", 30],
    ]:
        if geometry == []:
            if (
                markerlabel == "infected" or markerlabel == "culled on suspicion, actually infected"
            ):  # only for the real situation case plotting
                if real_situation == True:
                    geometry = [Point(xlims[0] - 0.1, ylims[0] - 0.1)]  # putting the point outside the limits
            else:
                geometry = [Point(xlims[0] - 0.1, ylims[0] - 0.1)]  # putting the point outside the limits

            # add a fake point to ensure the legend is there
        geo_df = gpd.GeoDataFrame(geometry=geometry)
        geo_df.crs = {"init": "epsg:4326"}
        # plot the marker
        ax = geo_df.plot(ax=ax, markersize=markersize, color=colour, marker=marker, label=markerlabel)

    ctx.add_basemap(ax, crs={"init": "epsg:4326"}, source=ctx.providers.OpenStreetMap.Mapnik)

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

    # ax.set_title("Outbreak day " + str(time), fontsize=18)
    ax.set_title(convert_time_to_date(time), fontsize=18)

    ax.set_ylabel("latitude", fontsize=16)
    ax.set_xlabel("longitude", fontsize=16)

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.05),
        fancybox=True,
        shadow=True,
        ncol=5,
        fontsize=18,
    )

    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    file_name = str(time) + ".png"

    if real_situation:
        file_name = os.path.join(folder_path, "map_underlying" + file_name)
    else:
        file_name = os.path.join(folder_path, "map_apparent" + file_name)

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()

    return


def plot_initial_report(
    properties,
    time,
    xlims,
    ylims,
    folder_path,
    contacts_for_plotting={},
):
    fig, ax = plt.subplots(1, 1, figsize=(20, 15))

    # geometry_undergoing_testing = [] # this should include both the reported property and the two contacts
    geometry_susceptible = []

    reported_farm_point = None
    geometry_contact_traced = []

    for key, value in contacts_for_plotting.items():
        premise = properties[key]
        long, lat = premise.coordinates
        curr_farm = Point(long, lat)
        reported_farm_point = curr_farm
        for contact_index in value:
            contact = properties[contact_index]
            long, lat = contact.coordinates
            curr_farm = Point(long, lat)
            geometry_contact_traced.append(curr_farm)

    for premise in properties:
        long, lat = premise.coordinates
        curr_farm = Point(long, lat)
        if curr_farm != reported_farm_point and curr_farm not in geometry_contact_traced:
            geometry_susceptible.append(curr_farm)

    for geometry, colour, marker, markerlabel, markersize in [
        [geometry_susceptible, "#5284b3", "o", "susceptible", 30],
        [geometry_contact_traced, "#ffa200", "d", "traced", 60],
        [[reported_farm_point], "#ffa200", "d", "reported", 60],
    ]:
        geo_df = gpd.GeoDataFrame(geometry=geometry)
        geo_df.crs = {"init": "epsg:4326"}
        # plot the marker
        ax = geo_df.plot(ax=ax, markersize=markersize, color=colour, marker=marker)  # , label=markerlabel) # no label

    ctx.add_basemap(ax, crs={"init": "epsg:4326"}, source=ctx.providers.OpenStreetMap.Mapnik)

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

    file_name = os.path.join(folder_path, f"plot_initial_report_{time}.png")

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()

    return


def plot_simex(
    properties,
    time,
    xlims,
    ylims,
    folder_path,
    contacts_for_plotting={},
    xylabels=False,
    save_suffix="",
    controlzone=None,
    plot_name="standstill",
):
    fig, ax = plt.subplots(1, 1, figsize=(20, 15))

    colour_dictionary = {
        "movement restrictions": "tomato",
        "ring vaccination": "#7800ff",
        "ring culling": "black",
        "ring testing": "green",
    }

    if controlzone != None and controlzone != {}:
        for control_type, zone in controlzone.items():
            if zone != None:
                try:
                    plot_polygon(
                        ax,
                        zone,
                        facecolor=colour_dictionary[control_type],
                        edgecolor=colour_dictionary[control_type],
                        alpha=0.2,
                        label=control_type,
                    )

                except:
                    for subpoly in zone:
                        plot_polygon(
                            ax,
                            subpoly,
                            facecolor=colour_dictionary[control_type],
                            edgecolor=colour_dictionary[control_type],
                            alpha=0.2,
                            label=control_type,
                        )

    geometry_confirmed_infected = []
    geometry_culled = []
    geometry_susceptible = []
    geometry_undergoing_testing = []
    geometry_vaccinated = []

    for key, value in contacts_for_plotting.items():
        premise = properties[key]
        for contact_index in value:
            contact = properties[contact_index]
            plt.plot(
                [premise.coordinates[0], contact.coordinates[0]],
                [premise.coordinates[1], contact.coordinates[1]],
                alpha=0.4,
                color="black",
            )

    for premise in properties:
        long, lat = premise.coordinates
        curr_farm = Point(long, lat)

        if premise.culled_status:
            geometry_culled.append(curr_farm)
        elif premise.reported_status == True:
            geometry_confirmed_infected.append(curr_farm)
        elif premise.undergoing_testing == True:
            geometry_undergoing_testing.append(curr_farm)
        elif premise.vaccination_status:
            geometry_vaccinated.append(curr_farm)
        else:
            geometry_susceptible.append(curr_farm)

    for geometry, colour, marker, markerlabel, markersize in [
        [geometry_susceptible, "#5284b3", "o", "susceptible", 30],
        [geometry_vaccinated, "#7852a4", "P", "vaccinated", 70],
        [geometry_undergoing_testing, "#ffa200", "d", "testing", 120],
        [geometry_confirmed_infected, "#ea4335", "X", "confirmed", 150],
        [geometry_culled, "black", "X", "culled", 150],
    ]:
        geo_df = gpd.GeoDataFrame(geometry=geometry)
        geo_df.crs = {"init": "epsg:4326"}
        # plot the marker
        ax = geo_df.plot(ax=ax, markersize=markersize, color=colour, marker=marker)  # , label=markerlabel) # no label

    ctx.add_basemap(ax, crs={"init": "epsg:4326"}, source=ctx.providers.OpenStreetMap.Mapnik)

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

    ax.text(xlims[0] + 0.002, ylims[1] - 0.03, convert_time_to_date(time), size=18, color="black")

    if xylabels == False:
        ax.axis("off")
    else:
        ax.set_ylabel("latitude", fontsize=16)
        ax.set_xlabel("longitude", fontsize=16)
        ax.tick_params(axis="x", labelsize=14)
        ax.tick_params(axis="y", labelsize=14)

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    file_name = os.path.join(folder_path, f"plot_{plot_name}_{time}{save_suffix}.png")

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()

    return


def plot_daily_notifications_over_time(dates_list, daily_notifs, folder_path, save_name):
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    x_points = list(range(len(dates_list)))

    ax.plot(x_points, daily_notifs, marker="o", markersize=15)
    # ax.set_xlabel('date', fontsize =14)
    # ax.set_ylabel('cases',fontsize= 14)
    ax.set_title("Daily confirmed cases", fontsize=16)
    ax.grid()

    # labels = [item.get_text() for item in ax.get_xticklabels()]
    # labels = [dates_list[x] for x in labels]

    if len(daily_notifs) > 20:
        day_spacing = 7
        if len(daily_notifs) > 50:
            day_spacing = 14
    else:
        day_spacing = 2

    ax.set_xticks(x_points[::day_spacing])
    ax.set_xticklabels([x[:-5] for x in dates_list[::day_spacing]], fontsize=14)  # remove the "/2024"
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=14)

    file_name = os.path.join(folder_path, f"{save_name}.png")

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()

    return


def save_pickle(to_save, filename):
    with open(filename, "wb") as file:
        pickle.dump(to_save, file)
    return 0


def save_data_properties(properties, folder_path):

    to_save = properties

    with open(os.path.join(folder_path, "properties_initialised.pickle"), "wb") as file:
        pickle.dump(to_save, file)

    return


def save_data(properties, property_coordinates, time, controlzone, folder_path):

    to_save = [properties, property_coordinates, time, controlzone]

    with open(os.path.join(folder_path, "data" + str(time)), "wb") as file:
        pickle.dump(to_save, file)

    return


def make_video(folder_path="outputs", prefix="map", times=None, save_name_prefix=""):
    """Outputs a gif and mp4 of the outbreak, based on saved png images"""

    image_files = []
    if times == None:
        time = 1
        file_path = os.path.join(folder_path, f"{prefix}{time}.png")
        while os.path.exists(file_path):
            image_files.append(file_path)
            time += 1
            file_path = os.path.join(folder_path, f"{prefix}{time}.png")
    else:
        for time in times:
            file_path = os.path.join(folder_path, f"{prefix}{time}.png")
            image_files.append(file_path)

    fps = 1
    clip = ImageSequenceClip(image_files, fps=fps)

    output_file = os.path.join(folder_path, save_name_prefix + prefix + "plot_video.mp4")

    value = clip.size

    if value[0] % 2 == 0:
        new_height = value[0]  # even
    else:
        new_height = value[0] + 1  # odd

    if value[1] % 2 == 0:
        new_width = value[1]  # even
    else:
        new_width = value[1] + 1  # odd

    clip_resized = clip.resize((new_height, new_width))

    clip_resized.write_videofile(output_file, codec="mpeg4")

    clip.write_gif(os.path.join(folder_path, save_name_prefix + prefix + "plot_video.gif"))

    return
