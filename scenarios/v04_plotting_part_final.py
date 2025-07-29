""" v0.4 

    plotting part final - for outcomes


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

import v04_plotting_functions as plotting_functions

folder_path_main = os.path.join(os.path.dirname(__file__), "v04")

folder_path_local = os.path.join(folder_path_main, "05_plotting")
if not os.path.exists(folder_path_local):
    os.makedirs(folder_path_local)


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


# cases over time

#############################################
# read in relevant data--
decision_ver = sys.argv[1]
finalised_number = 21
unique_output = f"05_after_decision_{decision_ver}_{finalised_number}"
folder_path = os.path.join(folder_path_main, unique_output)
first_detection_day = 48  # TO UPDATE
day = 105  # TO UPDATE


properties_name = os.path.join(folder_path, f"properties_{unique_output}")
with open(properties_name, "rb") as file:
    properties = pickle.load(file)

dates_list = [premises.convert_time_to_date(t) for t in range(first_detection_day, day + 1)]
# print(dates_list)
daily_notifs = [0] * len(dates_list)

for property_i in properties:
    notif_date = property_i.notification_date
    if notif_date != "NA":
        index = dates_list.index(notif_date)
        daily_notifs[index] += 1


save_name = f"{decision_ver}_daily_lab_confirmed_cases"
for i in range(len(dates_list)):
    plotting_functions.plot_combined_daily_and_total_notifications(
        [0, len(dates_list)],
        [0, sum(daily_notifs) + 1],
        dates_list,
        dates_list[: i + 1],
        daily_notifs[: i + 1],
        folder_path_local,
        f"{save_name}_{i}",
    )

output.make_video(folder_path_local, prefix=save_name + "_", times=list(range(len(dates_list))), save_name_prefix="")


# visual map of cases and expanding control zones over time
for day in range(78, 105 + 1):

    plotting_stuff_name = os.path.join(folder_path, f"preprocessed_plotting_data{day}")
    with open(plotting_stuff_name, "rb") as file:
        plotting_stuff = pickle.load(file)
    (
        source_indices,
        geometry_culled,
        geometry_confirmed_infected,
        geometry_DCP,
        geometry_undergoing_testing,
        geometry_vaccinated,
        geometry_infected,
        TPs,
        TPs_undergoing_testing,
        TPs_false_result,
    ) = plotting_stuff

    # constructing control zones
    newcontrolzone = plotting_functions.construct_control_zones(properties, source_indices)

    plotting_functions.plot_premises_with_controls(
        folder_path_local,
        f"{decision_ver}_map_{day}",
        newcontrolzone,
        xlims,
        ylims,
        geometry_culled,
        geometry_confirmed_infected,
        geometry_DCP,
        TPs_undergoing_testing,
        geometry_vaccinated,
        geometry_infected=[],
        final_vaccination=True,
    )

save_name = f"{decision_ver}_map"
output.make_video(folder_path_local, prefix=save_name + "_", times=list(range(78, 105 + 1)), save_name_prefix="")
