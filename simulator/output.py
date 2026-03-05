"""Data visualisation and pickle outputs

Based on FMD_modelling plotting_code.py, but adapted for "real locations" (i.e. spatially located).

This script produces output plots (static, gifs and mp4 animations) of the outbreak.

"""

from matplotlib.path import Path
from matplotlib.patches import PathPatch
from matplotlib.collections import PatchCollection
from matplotlib_scalebar.scalebar import ScaleBar
import matplotlib.cm as cm
from matplotlib import markers
import numpy as np
import os
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, MultiPoint
import shapely.plotting
import geopandas as gpd
import contextily as ctx
import pickle
from moviepy.editor import ImageSequenceClip

import pointpats
from scipy.stats import gaussian_kde

from simulator.premises import convert_time_to_date
from simulator.spatial_functions import *
import simulator.spatial_setup as spatial_setup
import pandas as pd
import PIL

PIL.Image.ANTIALIAS = PIL.Image.LANCZOS


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
    fig, ax = plt.subplots(1, 1, figsize=(20, 20))  # ,figsize=(10,12)

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
    show_movement_neighbours=False,
    xylabels=False,
    save_suffix="",
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
        "ring vaccination": "#7800ff",
        "ring culling": "black",
        "ring testing": "green",
        "restricted area": "red",
        "control area": "yellow",
        "surveillance area": "lime",
    }

    NT_WA = spatial_setup.get_NT_and_WA_shape()

    if controlzone != None and controlzone != {}:
        for control_type, zone in controlzone.items():
            if control_type == "surveillance area":
                continue  # for now, not plotting this area
            if control_type == "control area":
                zone = zone.difference(NT_WA)
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
                    try:
                        for subpoly in zone:
                            plot_polygon(
                                ax,
                                subpoly,
                                facecolor=colour_dictionary[control_type],
                                edgecolor=colour_dictionary[control_type],
                                alpha=0.2,
                                label=control_type,
                            )
                    except:
                        for subpoly in zone.geoms:
                            plot_polygon(
                                ax,
                                subpoly,
                                facecolor=colour_dictionary[control_type],
                                edgecolor=colour_dictionary[control_type],
                                alpha=0.2,
                                label=control_type,
                            )

    geometry_infected = []
    geometry_confirmed_infected = []
    geometry_culled = []
    geometry_vaccinated = []
    geometry_susceptible = []
    geometry_selfreport = []
    # geometry_culled_on_suspicion = [] # TODO/NOTE: currently removed because we don't expect ring culling to actually be implemented
    # geomtry_culled_on_suspicion_actually_infected = []
    geometry_undergoing_testing = []

    for key, value in contacts_for_plotting.items():
        premise = properties[key]
        for contact_index in value:
            contact = properties[contact_index]
            plt.plot(
                [premise.coordinates[0], contact.coordinates[0]],
                [premise.coordinates[1], contact.coordinates[1]],
                alpha=0.2,
                color="black",
            )

    if real_situation == True:  # i.e. plotting the underlying situation
        network_label_switch = False

        infected_coords = []

        if show_movement_neighbours:
            for index, property_i in enumerate(properties):
                propertyx, propertyy = property_i.coordinates

                # plot neighbours using edges
                for neighbour_property_type in property_i.movement_neighbours:
                    for j in property_i.movement_neighbours[neighbour_property_type]:
                        neighbour = properties[j]
                        neighbourx, neighboury = neighbour.coordinates
                        # plots the lines between locations
                        if network_label_switch == False:
                            plt.plot(
                                [propertyx, neighbourx],
                                [propertyy, neighboury],
                                alpha=0.01,
                                color="black",
                                label="network",
                            )
                            network_label_switch = True  # to make sure that the labelling only occurs once
                        else:
                            plt.plot(
                                [propertyx, neighbourx],
                                [propertyy, neighboury],
                                alpha=0.01,
                                color="black",
                            )

        for index, premise in enumerate(properties):
            long, lat = premise.coordinates
            curr_farm = Point(long, lat)
            if premise.culled_status:
                if premise.reported_status:
                    geometry_culled.append(curr_farm)
                    infected_coords.append(premise.coordinates)
                # elif premise.culled_on_suspicion:

                #     if premise.cumulative_infections > 0:
                #         geomtry_culled_on_suspicion_actually_infected.append(curr_farm)
                #     else:
                #         geometry_culled_on_suspicion.append(curr_farm)
                else:
                    raise Exception("Culled yet not reported")  # nor culled on suspicion")
            elif premise.reported_status == True:
                geometry_confirmed_infected.append(curr_farm)
                infected_coords.append(premise.coordinates)
            elif premise.infection_status:
                geometry_infected.append(curr_farm)
                infected_coords.append(premise.coordinates)
            elif premise.vaccination_status:
                geometry_vaccinated.append(curr_farm)
            elif premise.status == "SP":
                geometry_selfreport.append(curr_farm)
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

                # elif premise.culled_on_suspicion:
                #     geometry_culled_on_suspicion.append(curr_farm)
                else:
                    raise Exception("Culled yet not reported")  # nor culled on suspicion")
            elif premise.reported_status == True:
                geometry_confirmed_infected.append(curr_farm)
                infected_coords.append(premise.coordinates)
            elif premise.undergoing_testing == True:
                geometry_undergoing_testing.append(curr_farm)
            elif premise.vaccination_status:
                geometry_vaccinated.append(curr_farm)
            elif premise.status == "SP":
                geometry_selfreport.append(curr_farm)
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
        [
            geometry_susceptible,
            "#5284b3",
            "o",
            "susceptible",
            20,
        ],  # TODO: can take out susceptible plotting to make it clearer to see what's happening
        [geometry_selfreport, "grey", "s", "self-reported", 70],
        [geometry_vaccinated, "#7852a4", "P", "vaccinated", 70],
        [geometry_undergoing_testing, "#ffa200", "d", "TP/testing", 100],
        [geometry_infected, "purple", "x", "infected", 30],
        [geometry_confirmed_infected, "#ea4335", "X", "confirmed", 120],
        # [geometry_culled_on_suspicion, "black", "X", "culled on suspicion", 150],
        # [
        #     geomtry_culled_on_suspicion_actually_infected,
        #     "purple",
        #     "X",
        #     "culled on suspicion, actually infected",
        #     150,
        # ],
        [geometry_culled, "black", "X", "culled", 120],
    ]:
        if geometry == []:
            if markerlabel == "infected" or markerlabel == "culled on suspicion, actually infected":  # only for the real situation case plotting
                if real_situation == True:
                    geometry = [Point(xlims[0] - 0.1, ylims[0] - 0.1)]  # putting the point outside the limits
            else:
                geometry = [Point(xlims[0] - 0.1, ylims[0] - 0.1)]  # putting the point outside the limits

            # add a fake point to ensure the legend is there
        geo_df = gpd.GeoDataFrame(geometry=geometry)
        geo_df.crs = {"init": "epsg:4326"}
        # plot the marker
        ax = geo_df.plot(ax=ax, markersize=markersize, color=colour, marker=marker, label=markerlabel, aspect=1)

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
    # ax.set_title(convert_time_to_date(time), fontsize=18)
    ax.text(xlims[0] + 0.002, ylims[1] - 1.5, convert_time_to_date(time), size=18, color="black")

    if xylabels == False:
        ax.axis("off")
    else:
        ax.set_ylabel("latitude", fontsize=16)
        ax.set_xlabel("longitude", fontsize=16)
        ax.tick_params(axis="x", labelsize=14)
        ax.tick_params(axis="y", labelsize=14)

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 0.0),
        fancybox=True,
        shadow=True,
        ncol=3,
        fontsize=18,
    )

    file_name = str(time) + f"{save_suffix}.png"

    if real_situation:
        file_name = os.path.join(folder_path, "map_underlying" + file_name)
    else:
        file_name = os.path.join(folder_path, "map_apparent" + file_name)

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()

    return


def plot_animal_density(
    properties,
    xlims,
    ylims,
    folder_path,
    file_name="animal_density.png",
):
    """Aim: to plot a map of animal density across space"""

    fig, ax = plt.subplots(1, 1, figsize=(20, 15))

    x = []
    y = []

    for index, premise in enumerate(properties):
        property_polygon = premise.polygon
        # num_animals = len(premise.animals)
        num_animals = premise.size
        # Generates random points inside polygon
        animal_points = pointpats.random.poisson(property_polygon, size=num_animals)
        # what format is this in? an array of points?
        x.extend(animal_points[:, 0])
        y.extend(animal_points[:, 1])

    # https://python-graph-gallery.com/85-density-plot-with-matplotlib/
    nbins = 50

    k = gaussian_kde([x, y])
    xi, yi = np.mgrid[min(xlims) : max(xlims) : nbins * 1j, min(ylims) : max(ylims) : nbins * 1j]
    zi = k(np.vstack([xi.flatten(), yi.flatten()])).reshape(xi.shape)

    Australiashape = spatial_setup.Australia_shape()
    Australiashape = shapely.plotting.patch_from_polygon(Australiashape, facecolor="white")
    ax.add_patch(Australiashape)

    pcm = ax.pcolormesh(xi, yi, zi, alpha=1, cmap="YlOrRd", clip_path=(Australiashape))
    # pcm.set_clip_path(Australiashape)

    # ax.add_patch(Australiashape)

    # for subpoly in Australiashape.geoms:
    #     path = Path.make_compound_path(
    #         Path(np.asarray(subpoly.exterior.coords)[:, :2]),
    #         *[Path(np.asarray(ring.coords)[:, :2]) for ring in subpoly.interiors],
    #     )
    #     pcm = ax.pcolormesh(xi, yi, zi, alpha=0.5, cmap="YlOrRd",clip_path=(path, ax.transAxes))

    fig.colorbar(pcm, ax=ax)

    ctx.add_basemap(ax, crs={"init": "epsg:4326"}, source=ctx.providers.CartoDB.Positron)

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

    ax.set_title("Animal density map", fontsize=18)

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


def plot_animals(
    properties,
    xlims,
    ylims,
    folder_path,
):
    """Aim: to plot a map of animal density across space - just plot the dots (i.e., the individual cows) directly here"""

    fig, ax = plt.subplots(1, 1, figsize=(20, 15))

    x = []
    y = []

    for index, premise in enumerate(properties):
        property_polygon = premise.polygon
        lat = premise.y  # y
        lon = premise.x  # x
        puff_p1 = geodesic_polygon_buffer(lat, lon, property_polygon, 50)  # mild expansion 10 km to make it look more full

        num_animals = max(int(len(premise.animals) / 50), 2)
        # Generates random points inside polygon
        animal_points = pointpats.random.poisson(puff_p1, size=num_animals)
        # what format is this in? an array of points?
        x.extend(animal_points[:, 0])
        y.extend(animal_points[:, 1])

    geometry = [Point(long, lat) for long, lat in zip(x, y)]

    geo_df = gpd.GeoDataFrame(geometry=geometry)
    geo_df.crs = {"init": "epsg:4326"}
    # plot the marker
    ax = geo_df.plot(ax=ax, markersize=40, color="orange", marker="s", alpha=0.1)  # , label=markerlabel) # no label

    # ctx.add_basemap(ax, crs={"init": "epsg:4326"}, source=ctx.providers.OpenStreetMap.Mapnik)
    ctx.add_basemap(ax, crs={"init": "epsg:4326"}, source=ctx.providers.CartoDB.Positron)
    # Stadia.StamenTonerLite

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

    ax.set_title("Cattle distribution", fontsize=18)

    ax.set_ylabel("latitude", fontsize=16)
    ax.set_xlabel("longitude", fontsize=16)

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
    #       fancybox=True, shadow=True, ncol=5,fontsize=18)

    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    file_name = "animals.png"

    file_name = os.path.join(folder_path, file_name)

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()


def plot_animal_density_hist2d(
    properties,
    xlims,
    ylims,
    folder_path,
):
    """Aim: to plot a map of animal density across space"""

    fig, ax = plt.subplots(1, 1, figsize=(20, 15))

    x = []
    y = []

    for index, premise in enumerate(properties):
        property_polygon = premise.polygon
        num_animals = len(premise.animals)
        # Generates random points inside polygon
        animal_points = pointpats.random.poisson(property_polygon, size=num_animals)
        # what format is this in? an array of points?
        x.extend(animal_points[:, 0])
        y.extend(animal_points[:, 1])

    pcm = ax.hist2d(x, y, bins=(50, 50), cmap="YlOrRd")
    Australiashape = spatial_setup.Australia_shape()

    Australiashape = shapely.plotting.patch_from_polygon(Australiashape)
    ax.add_patch(Australiashape)

    pcm[3].set_clip_path(Australiashape)
    fig.colorbar(pcm[3], ax=ax)

    ctx.add_basemap(ax, crs={"init": "epsg:4326"}, source=ctx.providers.CartoDB.Positron)

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

    ax.set_title("Animal density map", fontsize=18)

    ax.set_ylabel("latitude", fontsize=16)
    ax.set_xlabel("longitude", fontsize=16)

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
    #       fancybox=True, shadow=True, ncol=5,fontsize=18)

    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    file_name = "animal_density_hist2D.png"

    file_name = os.path.join(folder_path, file_name)

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()


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

    ax.bar(x_points, daily_notifs, color="#16ACA4")
    # ax.set_xlabel('date', fontsize =14)
    # ax.set_ylabel('cases',fontsize= 14)
    ax.set_title("Daily confirmed infected premises", fontsize=16)
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

    # code grabbed from plot_column_figures.py by martin
    max_y_ticks = 5
    y_scale = max(daily_notifs)
    if y_scale <= 5:
        y_spacing = 1
    else:
        y_spacing = int(5 * np.ceil((y_scale / max_y_ticks) / 5))
    ax.set_yticks(np.arange(0, max(ax.get_yticks()) + y_spacing, step=y_spacing))
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=14)

    file_name = os.path.join(folder_path, f"{save_name}.png")

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()

    return


def plot_total_notifs_over_time(dates_list, daily_notifs, folder_path, save_name):
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    x_points = list(range(len(dates_list)))
    cumulative = np.cumsum(daily_notifs)

    ax.bar(x_points, cumulative, color="#16ACA4")
    # ax.set_xlabel('date', fontsize =14)
    # ax.set_ylabel('cases',fontsize= 14)
    ax.set_title("Total confirmed infected premises over time", fontsize=16)
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

    # code grabbed from plot_column_figures.py by martin
    max_y_ticks = 5
    y_scale = max(daily_notifs)
    if y_scale <= 5:
        y_spacing = 1
    else:
        y_spacing = int(5 * np.ceil((y_scale / max_y_ticks) / 5))
    ax.set_yticks(np.arange(0, max(ax.get_yticks()) + y_spacing, step=y_spacing))
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

    if new_height == value[0] and new_width == value[1]:
        clip_resized = clip
    else:

        try:
            clip_resized = clip.resize((new_height, new_width))
        except:
            try:
                clip_resized = clip.resize((new_height, new_width), PIL.Image.Resampling.LANCZOS)
            except:
                print("unable to resize and thus unable to make video")
                return

    clip_resized.write_videofile(output_file, codec="mpeg4")

    clip.write_gif(os.path.join(folder_path, save_name_prefix + prefix + "plot_video.gif"))

    return


def plot_infection_pressure(
    time,
    xlims,
    ylims,
    folder_path,
):
    fig, ax = plt.subplots(1, 1, figsize=(20, 15))  # ,figsize=(10,12)

    df = pd.read_csv(os.path.join(folder_path, "infection_pressure_output.csv"))

    markersize = 20
    marker = "o"

    cmap = cm.get_cmap("bwr")
    median = np.median(df["infection_pressure"].to_list())

    for index, row in df.iterrows():
        long = row["lon"]
        lat = row["lat"]
        geometry = [Point(long, lat)]

        geo_df = gpd.GeoDataFrame(geometry=geometry)
        geo_df.crs = {"init": "epsg:4326"}
        # TODO well if I want to do this, then this needs to be done properly
        ax = geo_df.plot(
            ax=ax,
            markersize=markersize,
            color=cmap((row["infection_pressure"] - median) * 3 + 0.5),
            marker=marker,
            aspect=1,
        )

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

    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    file_name = os.path.join(folder_path, "map_infection_pressure.png")

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()

    return


def plot_HPAI_outbreak_apparent(properties, restricted_area, control_area, enhanced_passive_surveillance, xlims, ylims, folder_path, time):
    fig, ax = plt.subplots(1, 1, figsize=(30, 25))  # ,figsize=(10,12)

    control_zones = {"restricted area": restricted_area, "control area": control_area, "Enhanced Passive Surveillance": enhanced_passive_surveillance}

    colour_dictionary = {
        "restricted area": {"face": "#e07b7b", "edge": "#660000"},
        "control area": {"face": "#fce27b", "edge": "#cc6600"},
        "Enhanced Passive Surveillance": {"face": "#7fe8f0", "edge": "#3d3d5c"},
    }

    for control_type in ["Enhanced Passive Surveillance", "control area", "restricted area"]:
        zone = control_zones[control_type]

        if zone != None:
            try:

                for subpoly in zone.geoms:
                    plot_polygon(
                        ax,
                        subpoly,
                        facecolor=colour_dictionary[control_type]["face"],
                        edgecolor=colour_dictionary[control_type]["edge"],
                        alpha=1,
                        label=control_type,
                    )
            except:

                plot_polygon(
                    ax,
                    zone,
                    facecolor=colour_dictionary[control_type]["face"],
                    edgecolor=colour_dictionary[control_type]["edge"],
                    alpha=1,
                    label=control_type,
                )

    for control_type in ["restricted area", "control area", "Enhanced Passive Surveillance"]:
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
    geometry_IP = []
    geometry_DCP = []
    geometry_DCP_AN = []
    geometry_SP = []
    geomtry_TP = []
    geometry_ARP = []
    geometry_POR = []
    geometry_UP = []
    geometry_NA = []
    geometry_other = []

    max_x = 140
    min_x = 154
    min_y = -28
    max_y = -38

    for index, premise in enumerate(properties):
        long, lat = premise.coordinates
        curr_farm = Point(long, lat)
        if premise.culled_status == True:
            geometry_culled.append(curr_farm)
        elif premise.status == "IP":
            geometry_IP.append(curr_farm)
        elif premise.status == "DCP":
            geometry_DCP.append(curr_farm)
        elif premise.status == "DCP-AN":
            geometry_DCP_AN.append(curr_farm)
        elif premise.status == "SP":
            geometry_SP.append(curr_farm)
        elif premise.status == "TP":
            geomtry_TP.append(curr_farm)
        elif premise.status == "ARP":
            geometry_ARP.append(curr_farm)
        elif premise.status == "POR":
            geometry_POR.append(curr_farm)
        elif premise.status == "UP":
            geometry_UP.append(curr_farm)
        elif premise.status == "NA":
            geometry_NA.append(curr_farm)
        else:
            print(f"status wasn't expected: {premise.status}")
            geometry_other.append(curr_farm)
            geometry_NA.append(curr_farm)

        if premise.status != "NA":
            if long > max_x:
                max_x = long
            if long < min_x:
                min_x = long
            if lat > max_y:
                max_y = lat
            if lat < min_y:
                min_y = lat

    for geometry, colour, marker, markerlabel, markersize, edgecolour, alpha in [
        [geometry_culled, "cornflowerblue", "P", "resolved premises", 110, "royalblue", 1],
        [geometry_IP, "black", "X", "infected premises", 110, "black", 1],
        [geometry_DCP, "#e72918", "v", "dangerous contact premises", 110, "#950000", 1],
        [geometry_DCP_AN, "#d38484ee", "v", "DCP-assessed negative", 100, "#df2929", 1],
        [geometry_SP, "#ffa200", "v", "SP", 100, "#ff6600", 0.3],
        [geomtry_TP, "#fffb00ef", "o", "TP", 70, "#cfa32a", 1],
        [geometry_ARP, "#dc68ffed", "s", "ARP", 40, "#383838", 1],
        [geometry_POR, "#fc1e4eeb", "s", "POR", 40, "#383838", 1],
        [geometry_UP, "#1eddf7ec", "$?$", "UP", 50, "#00A2FF", 1],
        [geometry_NA, "#444444eb", ".", "NA, ZP", 25, "#3D3D3D", 0.2],
        # geometry_other = []
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

    ctx.add_basemap(ax, crs={"init": "epsg:4326"}, source=ctx.providers.CartoDB.Positron)  # source=ctx.providers.OpenStreetMap.Mapnik

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

    # ax.axis("off")

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

    ax.legend(fontsize=18)

    file_name_ending = f"{time}.png"

    file_name = os.path.join(folder_path, "nice_map_" + file_name_ending)
    plt.savefig(file_name, bbox_inches="tight")

    ax.set_xlim([min_x - 0.1, max_x + 0.1])  # making a more zoomed in version
    ax.set_ylim([min_y - 0.05, max_y + 0.05])

    file_name = os.path.join(folder_path, "nice_map_zoomed_in" + file_name_ending)
    plt.savefig(file_name, bbox_inches="tight")

    plt.close()
