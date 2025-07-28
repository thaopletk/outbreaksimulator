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
total_sims = 10
first_detection_day = 47  # UPDATE/FIX THIS
day = 59  # FIX/UPDATE THIS

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

        for property_i in properties:
            notif_date = property_i.notification_date
            if notif_date != "NA":
                index = dates_list.index(notif_date)
                daily[index].append(property_i.coordinates)
        sims_location_of_daily_notified_premises.append(daily)

        all_notified_daily = [[] for _ in range(len(dates_list))]
        for i in range(len(dates_list)):
            for j in range(i):
                all_notified_daily[i].extend(daily[j])
        sims_location_of_all_notified_premises.append(all_notified_daily)

        daily_infected = [[] for _ in range(len(full_dates_list))]
        for property_i in properties:
            clinical_date = property_i.clinical_date
            if clinical_date != "NA":
                index = full_dates_list.index(clinical_date)
                daily_infected[index].append(property_i.coordinates)

        all_infected_daily = [[] for _ in range(len(full_dates_list))]
        for i in range(len(full_dates_list)):
            for j in range(i):
                all_infected_daily[i].extend(daily_infected[j])
        sims_location_of_all_infected_premises.append(all_infected_daily)


# plot line graphs with median and intervals
def plot_median_interval_over_time(dates_list, results, plottitle, folder_path, save_name):
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    x_points = list(range(len(dates_list)))

    ax.plot(x_points, results["median"], label="median")
    ax.fill_between(x_points, results["025"], results["025"], alpha=0.5, label="95 interval")
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

folder_path_local = os.path.join(folder_path_main, "plot_outputs")
if not os.path.exists(folder_path_local):
    os.makedirs(folder_path_local)

daily_notified_cases = {}
daily_notified_cases["median"] = np.median(sims_daily_notified_cases, axis=0)
daily_notified_cases["025"] = np.quantile(sims_daily_notified_cases, 0.025, axis=0)
daily_notified_cases["975"] = np.quantile(sims_daily_notified_cases, 0.975, axis=0)
plot_median_interval_over_time(
    dates_list, daily_notified_cases, "Daily notified cases", folder_path_local, f"{decision_ver}_daily_notified_cases"
)

cumulative_notified_cases = {}
cumulative_notified_cases["median"] = np.median(sims_daily_total_notified_cases, axis=0)
cumulative_notified_cases["025"] = np.quantile(sims_daily_total_notified_cases, 0.025, axis=0)
cumulative_notified_cases["975"] = np.quantile(sims_daily_total_notified_cases, 0.975, axis=0)
plot_median_interval_over_time(
    dates_list,
    cumulative_notified_cases,
    "Total notified cases",
    folder_path_local,
    f"{decision_ver}_total_notified_cases",
)

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
    """Aim: to plot a map of animal density across space"""

    fig, ax = plt.subplots(1, 1, figsize=(20, 15))

    x = [l[0] for l in coords_list]
    y = [l[1] for l in coords_list]

    # https://python-graph-gallery.com/85-density-plot-with-matplotlib/
    nbins = 50

    k = gaussian_kde([x, y])
    xi, yi = np.mgrid[min(xlims) : max(xlims) : nbins * 1j, min(ylims) : max(ylims) : nbins * 1j]
    zi = k(np.vstack([xi.flatten(), yi.flatten()])).reshape(xi.shape)

    Australiashape = spatial_setup.Australia_shape()
    Australiashape = shapely.plotting.patch_from_polygon(Australiashape, facecolor="white")
    ax.add_patch(Australiashape)

    ax.contour(xi, yi, zi, levels=14, linewidths=0.5, colors="k")
    cntr1 = ax.contourf(xi, yi, zi, levels=14, cmap="RdBu_r")

    for artist in ax.get_children():
        artist.set_clip_path(Australiashape)

    fig.colorbar(cntr1, ax=ax)

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


coords_list = []
sim_day = day
date = premises.convert_time_to_date(sim_day)
index = dates_list.index(date)
for sim in sims_location_of_all_notified_premises:
    coords_list.extend(sim[index])
print("sims_location_of_all_notified_premises", coords_list)

try:
    plot_target_property_density(
        coords_list,
        xlims,
        ylims,
        folder_path_local,
        "Forecast of all notified premises",
        f"{decision_ver}_forecast_all_notified_premises_{sim_day}",
    )
except Exception as e:
    print(e)

try:
    plot_target_property_density_v2(
        coords_list,
        xlims,
        ylims,
        folder_path_local,
        "Forecast of all notified premises",
        f"{decision_ver}_forecast_all_notified_premises_{sim_day}_v2",
    )
except Exception as e:
    print(e)

coords_list = []
sim_day = day
date = premises.convert_time_to_date(sim_day)
index = full_dates_list.index(date)
for sim in sims_location_of_all_infected_premises:
    coords_list.extend(sim[index])

print("sims_location_of_all_infected_premises", coords_list)
try:
    plot_target_property_density(
        coords_list,
        xlims,
        ylims,
        folder_path_local,
        "Forecast of all infected premises",
        f"{decision_ver}_forecast_all_infected_premises_{sim_day}",
    )
except Exception as e:
    print(e)
