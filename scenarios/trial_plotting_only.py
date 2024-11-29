""" Trial Simulation Exercise plotting

Aim: for this script to iterate and plot improved figures for the trial simulation exercise.


"""

import sys
import os
import json
import pickle

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.output as output
from simulator.premises import convert_time_to_date, convert_date_to_time

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
# plotting_data_name = os.path.join(folder_path_first_report, "plotting_data28.5")
# with open(plotting_data_name, "rb") as file:
#     properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

# xlims = [147, 149.3]
# ylims = [-33, -31]

# output.plot_initial_report(properties, time, xlims, ylims, folder_path_first_report, contacts_for_plotting)


# next plot the movement standstill stuff

# read in

# time_plot = 29
# time_list = []
# while time_plot < 43:
#     print(time_plot)
#     time_list.append(time_plot)
#     plotting_data_name = os.path.join(folder_path_movement_standstill_A, f"plotting_data{time_plot}")
#     with open(plotting_data_name, "rb") as file:
#         properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

#     xlims = [146.5, 149.5]
#     ylims = [-33, -30.4]

#     output.plot_movement_standstill(properties,time,xlims,ylims,folder_path_movement_standstill_A,contacts_for_plotting)

#     print(time_plot + 0.5)
#     time_list.append(time_plot + 0.5)
#     plotting_data_name = os.path.join(folder_path_movement_standstill_A, f"plotting_data{time_plot+0.5}")
#     with open(plotting_data_name, "rb") as file:
#         properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

#     xlims = [146.5, 149.5]
#     ylims = [-33, -30.4]

#     output.plot_movement_standstill(properties,time_plot+0.5,xlims,ylims,folder_path_movement_standstill_A,contacts_for_plotting)

#     time_plot += 1

# output.make_video(folder_path_movement_standstill_A, "plot_standstill_", time_list, "")

# plot number of notified properties over time

# download the outbreak state
properties_filename = os.path.join(folder_path_movement_standstill_A, "properties_04A_movement_standstill_two_weeks")
with open(properties_filename, "rb") as file:
    properties = pickle.load(file)

# get notification_date

dates_list = [convert_time_to_date(time) for time in range(28, 43)]
daily_notifs = [0] * len(dates_list)

for property_i in properties:
    notif_date = property_i.notification_date
    if notif_date != "NA":
        index = dates_list.index(notif_date)
        daily_notifs[index] += 1

save_name = "movement_standstill_daily_notifications"

output.plot_daily_notifications_over_time(dates_list, daily_notifs, folder_path_movement_standstill_A, save_name)
