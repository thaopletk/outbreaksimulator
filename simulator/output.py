""" Data visualisation and pickle outputs

    Based on FMD_modelling plotting_code.py, but adapted for "real locations" (i.e. spatially located)

"""

from matplotlib.path import Path
from matplotlib.patches import PathPatch
from matplotlib.collections import PatchCollection
from matplotlib_scalebar.scalebar import ScaleBar
import numpy as np
import os
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, MultiPoint
import geopandas as gpd
import contextily as ctx
import pickle
from moviepy.editor import ImageSequenceClip
from simulator.premises import convert_time_to_date


# https://coderslegacy.com/python/plotting-shapely-polygons-with-interiors-holes/
def plot_polygon(ax, poly, **kwargs):
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
    ax = geo_df.plot(
        ax=ax, markersize=markersize, color=colour, marker=marker, label=markerlabel
    )

    ctx.add_basemap(
        ax, crs={"init": "epsg:4326"}, source=ctx.providers.OpenStreetMap.Mapnik
    )

    # https://geopandas.org/en/stable/gallery/matplotlib_scalebar.html
    points = gpd.GeoSeries(
        [Point(-73.5, 40.5), Point(-74.5, 40.5)], crs=4326
    )  # Geographic WGS 84 - degrees
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


def plot_map_land(
    property_polygons, property_polygons_puffed, xlims, ylims, folder_path
):
    fig, ax = plt.subplots(1, 1, figsize=(20, 15))  # ,figsize=(10,12)

    for poly in property_polygons_puffed:
        plot_polygon(ax, poly, facecolor="tomato", edgecolor="maroon", alpha=0.01)

    for poly in property_polygons:
        plot_polygon(ax, poly, facecolor="tomato", edgecolor="maroon", alpha=1)

    ctx.add_basemap(
        ax, crs={"init": "epsg:4326"}, source=ctx.providers.OpenStreetMap.Mapnik
    )

    # https://geopandas.org/en/stable/gallery/matplotlib_scalebar.html
    points = gpd.GeoSeries(
        [Point(-73.5, 40.5), Point(-74.5, 40.5)], crs=4326
    )  # Geographic WGS 84 - degrees
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

    # if time < 10:
    #     file_name = "0" + str(time)  + ".png"
    # else:
    #     file_name = str(time) + ".png"
    file_name = "base_map.png"

    file_name = os.path.join(folder_path, file_name)

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()


def plot_map(
    properties,
    property_coordinates,
    time,
    xlims,
    ylims,
    folder_path,
    real_situation=True,
    controlzone=None,
    infectionpoly=False,
    contacts_for_plotting={},
):
    """Plot map

    Plots map (with map background)

    """
    fig, ax = plt.subplots(1, 1, figsize=(20, 15))  # ,figsize=(10,12)

    colour_dictionary = {
        "movement restrictions": "tomato",
        "ring vaccination": "deepskyblue",
    }

    if controlzone != None and controlzone != {}:
        for control_type, zone in controlzone.items():
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

    # network = []
    geometry_infected = []
    geometry_culled = []
    geometry_vaccinated = []
    geometry_susceptible = []
    # nodes

    for key, value in contacts_for_plotting.items():
        premise = properties[key]
        for contact_index in value:
            contact = properties[contact_index]
            plt.plot(
                [premise.coordinates[0], contact.coordinates[0]],
                [premise.coordinates[1], contact.coordinates[1]],
                alpha=1,
                color="black",
            )

    if real_situation == True:  # i.e. plotting the underlying situation
        network_label_switch = False

        infected_coords = []

        for index, premise in enumerate(properties):
            long, lat = premise.coordinates
            curr_farm = Point(long, lat)

            # plot neighbours using edges
            for farm in premise.neighbourhood:
                # neigh = Point(property_coordinates[farm[0], 0],property_coordinates[farm[0], 1])
                # network.append(LineString(curr_farm,neigh))

                # plots the lines between locations
                if network_label_switch == False:
                    plt.plot(
                        [premise.coordinates[0], property_coordinates[farm[0], 0]],
                        [premise.coordinates[1], property_coordinates[farm[0], 1]],
                        alpha=0.01,
                        color="black",
                        label="network",
                    )
                    network_label_switch = (
                        True  # to make sure that the labelling only occurs once
                    )
                else:
                    plt.plot(
                        [premise.coordinates[0], property_coordinates[farm[0], 0]],
                        [premise.coordinates[1], property_coordinates[farm[0], 1]],
                        alpha=0.01,
                        color="black",
                    )

        for index, premise in enumerate(properties):
            long, lat = premise.coordinates
            curr_farm = Point(long, lat)

            if premise.infection_status:
                # plt.scatter(premise.coordinates[0], premise.coordinates[1], color = 'purple', label = 'infected')
                geometry_infected.append(curr_farm)
                infected_coords.append(premise.coordinates)
            elif premise.culled_status:
                # plt.scatter(premise.coordinates[0], premise.coordinates[1], color = 'red', label = 'culled')
                geometry_culled.append(curr_farm)
                infected_coords.append(premise.coordinates)

            elif premise.vaccination_status:
                # plt.scatter(premise.coordinates[0], premise.coordinates[1], color = 'green', label = 'vaccinated')
                geometry_vaccinated.append(curr_farm)
            else:
                # plt.scatter(premise.coordinates[0], premise.coordinates[1], color = 'orange', label = 'susceptible')
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

    else:

        infected_coords = []

        for index, premise in enumerate(properties):
            long, lat = premise.coordinates
            curr_farm = Point(long, lat)

            # if premise.infection_status:
            #     # plt.scatter(premise.coordinates[0], premise.coordinates[1], color = 'purple', label = 'infected')
            #     geometry_infected.append(curr_farm)
            if premise.culled_status:
                # plt.scatter(premise.coordinates[0], premise.coordinates[1], color = 'red', label = 'culled')
                geometry_culled.append(curr_farm)
                infected_coords.append(premise.coordinates)

            elif premise.vaccination_status:
                # plt.scatter(premise.coordinates[0], premise.coordinates[1], color = 'green', label = 'vaccinated')
                geometry_vaccinated.append(curr_farm)
            else:
                # plt.scatter(premise.coordinates[0], premise.coordinates[1], color = 'orange', label = 'susceptible')
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
        [geometry_culled, "firebrick", "X", "notified", 150],
        [geometry_vaccinated, "deepskyblue", "s", "vaccinated", 100],
        [geometry_susceptible, "orange", "o", "susceptible", 30],
    ]:
        if geometry == []:
            if markerlabel == "infected":
                if real_situation == True:
                    geometry = [
                        Point(xlims[0] - 0.1, ylims[0] - 0.1)
                    ]  # putting the point outside the limits
            else:
                geometry = [
                    Point(xlims[0] - 0.1, ylims[0] - 0.1)
                ]  # putting the point outside the limits

            # add a fake point to ensure the legend is there
        geo_df = gpd.GeoDataFrame(geometry=geometry)
        geo_df.crs = {"init": "epsg:4326"}
        # plot the marker
        ax = geo_df.plot(
            ax=ax, markersize=markersize, color=colour, marker=marker, label=markerlabel
        )

    ctx.add_basemap(
        ax, crs={"init": "epsg:4326"}, source=ctx.providers.OpenStreetMap.Mapnik
    )

    # https://geopandas.org/en/stable/gallery/matplotlib_scalebar.html
    points = gpd.GeoSeries(
        [Point(-73.5, 40.5), Point(-74.5, 40.5)], crs=4326
    )  # Geographic WGS 84 - degrees
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

    # if time < 10:
    #     file_name = "0" + str(time)  + ".png"
    # else:
    #     file_name = str(time) + ".png"
    file_name = str(time) + ".png"

    if real_situation:
        file_name = os.path.join(folder_path, "map_underlying" + file_name)
    else:
        file_name = os.path.join(folder_path, "map_apparent" + file_name)

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

    # with open(os.path.join(folder_path,"properties"+str(time)), 'wb') as file:
    #     pickle.dump(properties, file)
    # with open(os.path.join(folder_path,"property_coordinates"+str(time)), 'wb') as file:
    #     pickle.dump(property_coordinates, file)

    return


def save_data(properties, property_coordinates, time, controlzone, folder_path):

    # folder_path = os.path.join(os.path.dirname(__file__),save_folder)

    to_save = [properties, property_coordinates, time, controlzone]

    with open(os.path.join(folder_path, "data" + str(time)), "wb") as file:
        pickle.dump(to_save, file)

    # with open(os.path.join(folder_path,"properties"+str(time)), 'wb') as file:
    #     pickle.dump(properties, file)
    # with open(os.path.join(folder_path,"property_coordinates"+str(time)), 'wb') as file:
    #     pickle.dump(property_coordinates, file)

    return


def make_video(folder_path="outputs", prefix="map", times=None, save_name_prefix=""):

    # folder_path = os.path.join(os.path.dirname(__file__),save_folder)

    # current_dir = os.getcwd()
    # parent_dir = os.path.dirname(current_dir)

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

    # image_files = [os.path.join(folder_path, img) for img in sorted(os.listdir(folder_path)) if img.endswith(('png')) and img.startswith((prefix))]

    # file_path = str(parent_dir) + "*.eps"
    fps = 1
    clip = ImageSequenceClip(image_files, fps=fps)
    output_file = os.path.join(
        folder_path, save_name_prefix + prefix + "plot_video.mp4"
    )

    clip.write_videofile(output_file)
    # ffmpeg.input(file_path, pattern_type = 'glob', framerate = 1).output('plot.mp4').run()

    clip.write_gif(
        os.path.join(folder_path, save_name_prefix + prefix + "plot_video.gif")
    )

    # with imageio.get_writer( os.path.join(folder_path,save_name_prefix+prefix+'plot_video.gif'), mode='I',duration=1/fps) as writer:
    #     for filename in image_files:
    #         image = imageio.imread(filename)
    #         writer.append_data(image)

    return
