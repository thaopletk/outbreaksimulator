""" Trial Simulation Exercise plotting

Aim: for this script to iterate and plot improved figures for the trial simulation exercise.


"""

import sys
import os
import json
import pickle

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.output as output

folder_path_main = os.path.join(os.path.dirname(__file__), "trial_simex")
folder_path_seed = os.path.join(folder_path_main, "01_seed")
folder_path_undetected_spread_1 = os.path.join(folder_path_main, "02_undetected_spread_one_week")
folder_path_first_report = os.path.join(folder_path_main, "03_spread_til_first_report")
folder_path_movement_standstill_A = os.path.join(folder_path_main, "04A_movement_standstill_two_weeks")
folder_path_radius_50km_B = os.path.join(folder_path_main, "04B_movement_radius_50km_two_weeks")
folder_path_radius_25km_C = os.path.join(folder_path_main, "04C_movement_radius_25km_two_weeks")


# first plotting
# after the first report:

# read in plotting_data28.5 from folder 03_spread_til_first_report
plotting_data_name = os.path.join(folder_path_first_report, "plotting_data28.5")
with open(plotting_data_name, "rb") as file:
    properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

xlims = [147, 149.3]
ylims = [-33, -31]

output.plot_initial_report(properties, time, xlims, ylims, folder_path_first_report, contacts_for_plotting)
