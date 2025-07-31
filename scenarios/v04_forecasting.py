""" v0.4 "forecasting

    Reads in the outputs of the different simulations and makes a forecast


"""

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
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
import pandas as pd

folder_path_main = os.path.join(os.path.dirname(__file__), "v04")

small_ver = ""
with open(os.path.join(folder_path_main, f"spatial_only_parameters{small_ver}.json"), "r") as file:
    spatial_only_parameters = json.load(file)  # has the total number of properties, hence the {small_ver}
with open(os.path.join(folder_path_main, f"properties_specific_parameters.json"), "r") as file:
    properties_specific_parameters = json.load(file)
with open(os.path.join(folder_path_main, "job_parameters.json"), "r") as file:
    job_parameters = json.load(file)
with open(os.path.join(folder_path_main, "scenario_parameters.json"), "r") as file:
    scenario_parameters = json.load(file)

# limits for the figures
xlims = [
    round(spatial_only_parameters["xrange"][0], 2) - 0.005,
    round(spatial_only_parameters["xrange"][1], 2) + 0.005,
]
ylims = [
    round(spatial_only_parameters["yrange"][0], 1) - 0.05,
    round(spatial_only_parameters["yrange"][1], 1) + 0.05,
]

decision_ver = sys.argv[1]
total_sims = 20
first_detection_day = 48  # UPDATE/FIX THIS
day = 105  # FIX/UPDATE THIS

# set up the list for all the different cases, per day
sims_daily_notified_cases = []
# set up the list for all the culumative cases, per day
sims_daily_total_notified_cases = []
# # set up the list for all (T/F incursion into states), per day
# sims_QLD_incursion = [] # might not need this
# sims_NSW_incursion = []
# sims_VIC_incursion = []
# sims_SA_incursion = []

# set up the list for all  property locations' detection status, per day *
#  * might be infection status or clinical status
sims_location_of_all_notified_premises = []
sims_location_of_daily_notified_premises = []
sims_location_of_all_infected_premises = []

dates_list = [premises.convert_time_to_date(t) for t in range(first_detection_day, day + 1)]
full_dates_list = [premises.convert_time_to_date(t) for t in range(0, day + 1)]

sims_total_IPs = []
sims_total_depopulated = []
sims_total_culled_animals = []

sims_total_inspects = []
sims_total_lab = []


sims_total_vax_premises = []
sims_total_vax_administered = []

# daily_indices_of_all_notified_premises = [{i:0 for i in range(spatial_only_parameters['n'])} for _ in range(len(dates_list))]

# for each simulation number
for i in range(1, total_sims + 1):
    # read in the data
    unique_output = f"05_after_decision_{decision_ver}_{i}"
    print(unique_output)
    folder_path_local = os.path.join(folder_path_main, unique_output)

    plotting_data_name = os.path.join(folder_path_local, f"plotting_data{day}")
    with open(plotting_data_name, "rb") as file:
        properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

        # notified cases, per day
        daily_notifs = [0] * len(dates_list)

        for property_i in properties:
            notif_date = property_i.notification_date
            if notif_date != "NA":
                index = dates_list.index(notif_date)
                daily_notifs[index] += 1

        sims_daily_notified_cases.append(daily_notifs)

        # culumative cases, per day
        cumulative = np.cumsum(daily_notifs)
        sims_daily_total_notified_cases.append(cumulative)

        # TODO later
        # # set up the list for all (T/F incursion into states), per day
        # sims_QLD_incursion = [] # might not need this
        # sims_NSW_incursion = []
        # sims_VIC_incursion = []
        # sims_SA_incursion = []

        # set up the list for all  property locations' detection status, per day *
        #  * might be infection status or clinical status

        daily = [[] for _ in range(len(dates_list))]
        # daily_indices = [[] for _ in range(len(dates_list))]

        for i, property_i in enumerate(properties):
            notif_date = property_i.notification_date
            if notif_date != "NA":
                index = dates_list.index(notif_date)
                daily[index].append(property_i.coordinates)
                # daily_indices[index].append(i)
        sims_location_of_daily_notified_premises.append(daily)

        all_notified_daily = [[] for _ in range(len(dates_list))]
        # all_notified_daily_indices = [[] for _ in range(len(dates_list))]
        for i in range(len(dates_list)):
            for j in range(0, i + 1):
                all_notified_daily[i].extend(daily[j])

        sims_location_of_all_notified_premises.append(all_notified_daily)

        daily_infected = [[] for _ in range(len(full_dates_list))]
        for property_i in properties:
            clinical_date = property_i.clinical_date
            if clinical_date != "NA":
                index = full_dates_list.index(clinical_date)
                daily_infected[index].append(property_i.coordinates)

        total_ips = 0
        for property_i in properties:
            exposure_date = property_i.exposure_date
            if exposure_date != "NA":
                total_ips += 1
        sims_total_IPs.append(total_ips)

        all_infected_daily = [[] for _ in range(len(full_dates_list))]
        for i in range(len(full_dates_list)):
            for j in range(0, i + 1):
                all_infected_daily[i].extend(daily_infected[j])
        sims_location_of_all_infected_premises.append(all_infected_daily)

        total_depopulated = 0
        total_culled_animals = 0
        for i, property_i in enumerate(properties):
            removal_date = property_i.removal_date
            if removal_date != "NA":
                total_depopulated += 1
                total_culled_animals += property_i.size

        sims_total_depopulated.append(total_depopulated)
        sims_total_culled_animals.append(total_culled_animals)

        total_vax = 0
        total_vaccines = 0
        for i, property_i in enumerate(properties):
            vacc_date = property_i.vacc_date
            if vacc_date != "NA":
                total_vax += 1
                total_vaccines += property_i.size

        sims_total_vax_premises.append(total_vax)
        sims_total_vax_administered.append(total_vaccines)

    resource_data_name = os.path.join(folder_path_local, f"resources_used.csv")
    resource = pd.read_csv(resource_data_name)

    sims_total_inspects.append(resource["ClinicalObservation"].sum())
    sims_total_lab.append(resource["LabTesting"].sum())


# plot line graphs with median and intervals
def plot_median_interval_over_time(dates_list, results, plottitle, folder_path, save_name):
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    x_points = list(range(len(dates_list)))

    ax.plot(x_points, results["median"], label="median")
    ax.fill_between(x_points, results["025"], results["975"], alpha=0.5, label="95 interval")
    # ax.set_xlabel('date', fontsize =14)
    # ax.set_ylabel('cases',fontsize= 14)
    ax.set_title(plottitle, fontsize=16)
    ax.grid()

    # labels = [item.get_text() for item in ax.get_xticklabels()]
    # labels = [dates_list[x] for x in labels]

    if len(results) > 20:
        day_spacing = 7
        if len(results) > 50:
            day_spacing = 14
    else:
        day_spacing = 2

    ax.set_xticks(x_points[::day_spacing])
    ax.set_xticklabels([x[:-5] for x in dates_list[::day_spacing]], fontsize=14)  # remove the "/2024"
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=14)
    ax.legend()

    file_name = os.path.join(folder_path, f"{save_name}.png")

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()

    return


# for each representation, get the median, intervals, etc and plot

folder_path_local = os.path.join(folder_path_main, "forecast_plotting_3")
if not os.path.exists(folder_path_local):
    os.makedirs(folder_path_local)

# daily_notified_cases = {}
# daily_notified_cases["median"] = np.median(sims_daily_notified_cases, axis=0)
# daily_notified_cases["025"] = np.quantile(sims_daily_notified_cases, 0.025, axis=0)
# daily_notified_cases["975"] = np.quantile(sims_daily_notified_cases, 0.975, axis=0)
# print(daily_notified_cases)
# plot_median_interval_over_time(
#     dates_list, daily_notified_cases, "Daily notified cases", folder_path_local, f"{decision_ver}_daily_notified_cases"
# )


print("total_IPs:", np.median(sims_total_IPs))

cumulative_notified_cases = {}
cumulative_notified_cases["median"] = np.median(sims_daily_total_notified_cases, axis=0)
cumulative_notified_cases["025"] = np.quantile(sims_daily_total_notified_cases, 0.025, axis=0)
cumulative_notified_cases["975"] = np.quantile(sims_daily_total_notified_cases, 0.975, axis=0)
# plot_median_interval_over_time(
#     dates_list,
#     cumulative_notified_cases,
#     "Total notified cases",
#     folder_path_local,
#     f"{decision_ver}_total_notified_cases",
# )
print("cumulative_notified_cases:", cumulative_notified_cases)

print("total depoped:", np.median(sims_total_depopulated))

print("total culled animals:", np.median(sims_total_culled_animals))

print("total inspects: ", np.median(sims_total_inspects))

print("total lab tests: ", np.median(sims_total_lab))

print("total_vax_premises:", np.median(sims_total_vax_premises))

print("total vaccines administered", np.median(sims_total_vax_administered))

# gif/ video for the spatial one too


def plot_target_property_density(coords_list, xlims, ylims, folder_path, plottitle, plotsavename):
    """Aim: to plot a map of animal density across space"""

    fig, ax = plt.subplots(1, 1, figsize=(20, 15))

    Australiashape = spatial_setup.Australia_shape()
    Australiashape = shapely.plotting.patch_from_polygon(Australiashape, facecolor="white")
    ax.add_patch(Australiashape)

    if coords_list != []:

        x = [l[0] for l in coords_list]
        y = [l[1] for l in coords_list]

        # https://python-graph-gallery.com/85-density-plot-with-matplotlib/
        nbins = 50

        k = gaussian_kde([x, y])
        xi, yi = np.mgrid[min(xlims) : max(xlims) : nbins * 1j, min(ylims) : max(ylims) : nbins * 1j]
        zi = k(np.vstack([xi.flatten(), yi.flatten()])).reshape(xi.shape)

        pcm = ax.pcolormesh(xi, yi, zi, alpha=1, cmap="YlOrRd", clip_path=(Australiashape))

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

    ax.set_title(plottitle, fontsize=18)

    ax.set_ylabel("latitude", fontsize=16)
    ax.set_xlabel("longitude", fontsize=16)

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
    #       fancybox=True, shadow=True, ncol=5,fontsize=18)

    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    file_name = f"{plotsavename}.png"

    file_name = os.path.join(folder_path, file_name)

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()


def plot_target_property_density_v2(coords_list, xlims, ylims, folder_path, plottitle, plotsavename):

    fig, ax = plt.subplots(1, 1, figsize=(20, 15))

    x = [l[0] for l in coords_list]
    y = [l[1] for l in coords_list]

    # https://python-graph-gallery.com/85-density-plot-with-matplotlib/
    nbins = 200

    k = gaussian_kde([x, y])
    xi, yi = np.mgrid[min(xlims) : max(xlims) : nbins * 1j, min(ylims) : max(ylims) : nbins * 1j]
    zi = k(np.vstack([xi.flatten(), yi.flatten()])).reshape(xi.shape)

    # print(zi)
    print(np.max(zi))
    print(len(coords_list))

    Australiashape = spatial_setup.Australia_shape()
    Australiashape = shapely.plotting.patch_from_polygon(Australiashape, facecolor="white")
    ax.add_patch(Australiashape)

    # set desired contour levels.
    clevs = np.linspace(0.0005, np.max(zi) + 0.001, 18)  # 0.16 # the maximum level I've seen so far is around 0.156
    # 0.00005
    levels = [0]
    levels.extend(clevs)

    ax.contour(xi, yi, zi, levels, linewidths=0.5, colors="k")
    cntr1 = ax.contourf(
        xi, yi, zi, levels, cmap="RdBu_r"
    )  # BuPu (better), "PuRd" (worse) , alpha=0.9 # RdBu_r (diverging so technically not good) ; (cool - bad)

    for artist in ax.get_children():
        artist.set_clip_path(Australiashape)

    # fig.colorbar(cntr1, ax=ax)

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

    ax.set_title(plottitle, fontsize=18)

    ax.set_ylabel("latitude", fontsize=16)
    ax.set_xlabel("longitude", fontsize=16)

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
    #       fancybox=True, shadow=True, ncol=5,fontsize=18)

    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    file_name = f"{plotsavename}.png"

    file_name = os.path.join(folder_path, file_name)

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()


def plot_target_property_density_v3(coords_list, xlims, ylims, folder_path, plottitle, plotsavename):
    """Aim: to plot a map of infection"""

    fig, ax = plt.subplots(1, 1, figsize=(20, 15))

    notified_times = {}
    for coords in coords_list:
        x = coords[0]
        y = coords[1]
        if (x, y) not in notified_times:
            notified_times[(x, y)] = 1
        else:
            notified_times[(x, y)] += 1

    x = []
    y = []
    z = []
    for key, value in notified_times.items():
        x.append(key[0])
        y.append(key[1])
        z.append(value)

    Australiashape = spatial_setup.Australia_shape()
    Australiashape = shapely.plotting.patch_from_polygon(Australiashape, facecolor="white")
    ax.add_patch(Australiashape)

    ax.tricontour(x, y, z, levels=14, linewidths=0.5, colors="k")
    cntr = ax.tricontourf(x, y, z, levels=14, cmap="BuPu", alpha=0.9)

    for artist in ax.get_children():
        artist.set_clip_path(Australiashape)

    # fig.colorbar(cntr1, ax=ax)

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

    ax.set_title(plottitle, fontsize=18)

    ax.set_ylabel("latitude", fontsize=16)
    ax.set_xlabel("longitude", fontsize=16)

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
    #       fancybox=True, shadow=True, ncol=5,fontsize=18)

    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    file_name = f"{plotsavename}.png"

    file_name = os.path.join(folder_path, file_name)

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()


def plot_target_property_density_v4(coords_list, xlims, ylims, folder_path, plottitle, plotsavename):

    fig, ax = plt.subplots(1, 1, figsize=(20, 15))

    x = [l[0] for l in coords_list]
    y = [l[1] for l in coords_list]

    # https://python-graph-gallery.com/85-density-plot-with-matplotlib/
    nbins = 200

    k = gaussian_kde([x, y])
    xi, yi = np.mgrid[min(xlims) : max(xlims) : nbins * 1j, min(ylims) : max(ylims) : nbins * 1j]
    zi = k(np.vstack([xi.flatten(), yi.flatten()])).reshape(xi.shape)

    # print(zi)
    print(np.max(zi))
    print(len(coords_list))

    Australiashape = spatial_setup.Australia_shape()
    Australiashape = shapely.plotting.patch_from_polygon(Australiashape, facecolor="white")
    ax.add_patch(Australiashape)

    pcm = ax.pcolormesh(xi, yi, zi, alpha=1, cmap="RdBu_r", clip_path=(Australiashape))

    # set desired contour levels.
    clevs = np.linspace(0.0005, np.max(zi) + 0.001, 18)  # 0.16 # the maximum level I've seen so far is around 0.156
    # 0.00005
    levels = [0]
    levels.extend(clevs)

    ax.contour(xi, yi, zi, levels, linewidths=0.5, colors="k")
    # cntr1 = ax.contourf(xi, yi, zi, levels, cmap="RdBu_r")  # BuPu (better), "PuRd" (worse) , alpha=0.9 # RdBu_r (diverging so technically not good) ; (cool - bad)

    for artist in ax.get_children():
        artist.set_clip_path(Australiashape)

    # fig.colorbar(cntr1, ax=ax)

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

    ax.set_title(plottitle, fontsize=18)

    ax.set_ylabel("latitude", fontsize=16)
    ax.set_xlabel("longitude", fontsize=16)

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
    #       fancybox=True, shadow=True, ncol=5,fontsize=18)

    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    file_name = f"{plotsavename}.png"

    file_name = os.path.join(folder_path, file_name)

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()


def plot_target_property_density_v5(properties, coords_list, xlims, ylims, folder_path, plottitle, plotsavename):

    fig, ax = plt.subplots(1, 1, figsize=(20, 15))

    notified_times = {}
    for property_i in properties:
        notified_times[(property_i.x, property_i.y)] = 0

    for coords in coords_list:
        x = coords[0]
        y = coords[1]
        if (x, y) not in notified_times:
            notified_times[(x, y)] = 1
        else:
            notified_times[(x, y)] += 1

    x = []
    y = []
    z = []
    for key, value in notified_times.items():
        x.append(key[0])
        y.append(key[1])
        z.append(value)

    # now I have x, y, z as a set of irregularly space grids

    # https://matplotlib.org/stable/gallery/images_contours_and_fields/irregulardatagrid.html#sphx-glr-gallery-images-contours-and-fields-irregulardatagrid-py

    # Create grid values first.
    ngridx = 400
    ngridy = 800
    xi = np.linspace(min(xlims), max(xlims), ngridx)
    yi = np.linspace(min(ylims), max(ylims), ngridy)

    # using interpolation
    zi = griddata((x, y), z, (xi[None, :], yi[:, None]), method="cubic")

    zi = gaussian_filter(zi, sigma=2)

    # print(zi)
    print(np.max(zi))
    print(len(coords_list))

    Australiashape = spatial_setup.Australia_shape()
    Australiashape = shapely.plotting.patch_from_polygon(Australiashape, facecolor="white")
    ax.add_patch(Australiashape)

    pcm = ax.pcolormesh(xi, yi, zi, alpha=1, clip_path=(Australiashape))

    # might need to be max at 20 (i.e. the number of sims)
    # set desired contour levels.
    clevs = np.linspace(0.0005, np.max(zi) + 0.001, 18)  # 0.16 # the maximum level I've seen so far is around 0.156
    # 0.00005
    levels = [0]
    levels.extend(clevs)

    ax.contour(xi, yi, zi, levels, linewidths=0.5, colors="k")
    # cntr1 = ax.contourf(xi, yi, zi, levels, cmap="RdBu_r")  # BuPu (better), "PuRd" (worse) , alpha=0.9 # RdBu_r (diverging so technically not good) ; (cool - bad)

    for artist in ax.get_children():
        artist.set_clip_path(Australiashape)

    # fig.colorbar(cntr1, ax=ax)

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

    ax.set_title(plottitle, fontsize=18)

    ax.set_ylabel("latitude", fontsize=16)
    ax.set_xlabel("longitude", fontsize=16)

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
    #       fancybox=True, shadow=True, ncol=5,fontsize=18)

    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    file_name = f"{plotsavename}.png"

    file_name = os.path.join(folder_path, file_name)

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()


# coords_list = []
# sim_day = day
# date = premises.convert_time_to_date(sim_day)
# index = dates_list.index(date)
# for sim in sims_location_of_daily_notified_premises:
#     coords_list.extend(sim[index])
# print(coords_list)
# try:
#     plot_target_property_density(
#         coords_list,
#         xlims,
#         ylims,
#         folder_path_local,
#         "Forecast of new notified premises",
#         f"{decision_ver}_forecast_new_notified_premises_{sim_day}",
#     )
# except:
#     pass

ylims = [
    -35,
    ylims[1],
]
for sim_day in range(78 - 1, 105 + 1):
    coords_list = []
    date = premises.convert_time_to_date(sim_day)
    index = dates_list.index(date)
    for sim in sims_location_of_all_notified_premises:
        coords_list.extend(sim[index])
    # print("sims_location_of_all_notified_premises", coords_list)

    # plot_target_property_density(
    #     coords_list,
    #     xlims,
    #     ylims,
    #     folder_path_local,
    #     "Forecast of all notified premises",
    #     f"{decision_ver}_forecast_all_notified_premises_{sim_day}",
    # )

    # plot_target_property_density_v2(
    #     coords_list,
    #     xlims,
    #     ylims,
    #     folder_path_local,
    #     "Forecast of all notified premises",
    #     f"{decision_ver}_forecast_all_notified_premises_v2_{sim_day}",
    # )

    # plot_target_property_density_v3(coords_list,
    #     xlims,
    #     ylims,
    #     folder_path_local,
    #     "Forecast of all notified premises",
    #     f"{decision_ver}_forecast_all_notified_premises_v3_{sim_day}",)

    # plot_target_property_density_v4(
    #     coords_list,
    #     xlims,
    #     ylims,
    #     folder_path_local,
    #     "Forecast of all notified premises",
    #     f"{decision_ver}_forecast_all_notified_premises_v4_{sim_day}",
    # )

    plot_target_property_density_v5(
        properties,
        coords_list,
        xlims,
        ylims,
        folder_path_local,
        "Forecast of all notified premises",
        f"{decision_ver}_forecast_all_notified_premises_v5_{sim_day}",
    )

    # coords_list = []
    # date = premises.convert_time_to_date(sim_day)
    # index = full_dates_list.index(date)
    # for sim in sims_location_of_all_infected_premises:
    #     coords_list.extend(sim[index])

    # print("sims_location_of_all_infected_premises", coords_list)
    # try:
    #     plot_target_property_density(
    #         coords_list,
    #         xlims,
    #         ylims,
    #         folder_path_local,
    #         "Forecast of all infected premises",
    #         f"{decision_ver}_forecast_all_infected_premises_{sim_day}",
    #     )
    # except Exception as e:
    #     print(e)


# output.make_video(folder_path_local, prefix=f"{decision_ver}_forecast_all_notified_premises_", times=list(range(78, 105 + 1)), save_name_prefix="")

# output.make_video(
#     folder_path_local,
#     prefix=f"{decision_ver}_forecast_all_notified_premises_v2_",
#     times=list(range(77, 105 + 1)),
#     save_name_prefix="",
# )

# output.make_video(folder_path_local, prefix=f"{decision_ver}_forecast_all_infected_premises_", times=list(range(78, 105 + 1)), save_name_prefix="")


# output.make_video(
#     folder_path_local,
#     prefix=f"{decision_ver}_forecast_all_notified_premises_v4_",
#     times=list(range(77, 105 + 1)),
#     save_name_prefix="",
# )

output.make_video(
    folder_path_local,
    prefix=f"{decision_ver}_forecast_all_notified_premises_v5_",
    times=list(range(77, 105 + 1)),
    save_name_prefix="",
)
