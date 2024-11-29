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

#     output.plot_simex(properties,time,xlims,ylims,folder_path_movement_standstill_A,contacts_for_plotting)

#     print(time_plot + 0.5)
#     time_list.append(time_plot + 0.5)
#     plotting_data_name = os.path.join(folder_path_movement_standstill_A, f"plotting_data{time_plot+0.5}")
#     with open(plotting_data_name, "rb") as file:
#         properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

#     xlims = [146.5, 149.5]
#     ylims = [-33, -30.4]

#     output.plot_simex(properties,time_plot+0.5,xlims,ylims,folder_path_movement_standstill_A,contacts_for_plotting)

#     time_plot += 1

# output.make_video(folder_path_movement_standstill_A, "plot_standstill_", time_list, "")


# plot number of notified properties over time

# download the outbreak state
# properties_filename = os.path.join(folder_path_movement_standstill_A, "properties_04A_movement_standstill_two_weeks")
# with open(properties_filename, "rb") as file:
#     properties = pickle.load(file)

# # get notification_date

# dates_list = [convert_time_to_date(time) for time in range(28, 43)]
# daily_notifs = [0] * len(dates_list)

# for property_i in properties:
#     notif_date = property_i.notification_date
#     if notif_date != "NA":
#         index = dates_list.index(notif_date)
#         daily_notifs[index] += 1

# save_name = "movement_standstill_daily_notifications"

# output.plot_daily_notifications_over_time(dates_list, daily_notifs, folder_path_movement_standstill_A, save_name)

## plot the full outbreak window at end time point

# plotting_data_name = os.path.join(folder_path_movement_standstill_A, "plotting_data42.5")
# with open(plotting_data_name, "rb") as file:
#     properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

# # xlims = [144.5, 151.5]
# # ylims = [-34.5, -28.5]

# output.plot_simex(properties,time,xlims,ylims,folder_path_movement_standstill_A,contacts_for_plotting={},xylabels = True,save_suffix="_v2")


# next plot the movement standstill stuff

# read in

# time_plot = 29
# time_list = []
# while time_plot < 43:
#     print(time_plot)
#     time_list.append(time_plot)
#     # plotting_data_name = os.path.join(folder_path_radius_50km_B, f"plotting_data{time_plot}")
#     # with open(plotting_data_name, "rb") as file:
#     #     properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

#     # xlims = [146.5, 150.1]
#     # ylims = [-33, -29.9]

#     # if time == 30:
#     #     contacts_for_plotting = {}

#     # output.plot_simex(properties,time,xlims,ylims,folder_path_radius_50km_B,contacts_for_plotting,controlzone=controlzone, plot_name = "50km_restrictions")

#     # if time_plot < 31:
#     #     xlims = [147, 149.3]
#     #     ylims = [-33, -31]

#     #     output.plot_simex(properties,time,xlims,ylims,folder_path_radius_50km_B,contacts_for_plotting,controlzone=controlzone, plot_name = "50km_restrictions_smaller")

#     print(time_plot + 0.5)
#     time_list.append(time_plot + 0.5)
#     # plotting_data_name = os.path.join(folder_path_radius_50km_B, f"plotting_data{time_plot+0.5}")
#     # with open(plotting_data_name, "rb") as file:
#     #     properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

#     # xlims = [146.5, 150.1]
#     # ylims = [-33, -29.9]

#     # output.plot_simex(properties,time_plot+0.5,xlims,ylims,folder_path_radius_50km_B,contacts_for_plotting,controlzone=controlzone, plot_name = "50km_restrictions")

#     # if time_plot < 31:
#     #     xlims = [147, 149.3]
#     #     ylims = [-33, -31]

#     #     output.plot_simex(properties,time_plot+0.5,xlims,ylims,folder_path_radius_50km_B,contacts_for_plotting,controlzone=controlzone, plot_name = "50km_restrictions_smaller")

#     time_plot += 1

# output.make_video(folder_path_radius_50km_B, "plot_50km_restrictions_", time_list, "")


# # plot number of notified properties over time

# # download the outbreak state
# properties_filename = os.path.join(folder_path_radius_50km_B, "properties_04B_movement_radius_50km_two_weeks")
# with open(properties_filename, "rb") as file:
#     properties = pickle.load(file)

# # get notification_date

# dates_list = [convert_time_to_date(time) for time in range(28, 43)]
# daily_notifs = [0] * len(dates_list)

# for property_i in properties:
#     notif_date = property_i.notification_date
#     if notif_date != "NA":
#         index = dates_list.index(notif_date)
#         daily_notifs[index] += 1

# save_name = "50km_restrictions_daily_notifications"

# output.plot_daily_notifications_over_time(dates_list, daily_notifs, folder_path_radius_50km_B, save_name)

# # plot the full outbreak window at end time point

# plotting_data_name = os.path.join(folder_path_radius_50km_B, "plotting_data42.5")
# with open(plotting_data_name, "rb") as file:
#     properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

# # xlims = [144.5, 151.5]
# # ylims = [-34.5, -28.5]

# output.plot_simex(properties,time,xlims,ylims,folder_path_radius_50km_B,contacts_for_plotting={},xylabels = True,save_suffix="_v2",controlzone=controlzone,plot_name = "50km_restrictions")


# plot heaps of things now

for timerange in [[43, 57], [57, 117]]:
    if timerange == [43, 57]:
        folder_path_list = [
            "04A-05AC_standstill_test30km",
            "04A-05BC_restriction50km_test30km",
            "04B-05AC_standstill_test30km",
            "04B-05BC_restriction50km_test30km",
        ]
    else:
        folder_path_list = [
            "04A-05AC-06AC_standstilltest50km",
            "04A-05AC-06AD_standstillvaccinate50km",
            "04A-05AC-06BC_restriction50kmtest50km",
            "04A-05AC-06BD_restriction50kmvaccinate50km",
            "04A-05BC-06AC_standstilltest50km",
            "04A-05BC-06AD_standstillvaccinate50km",
            "04A-05BC-06BC_restriction50kmtest50km",
            "04A-05BC-06BD_restriction50kmvaccinate50km",
            "04B-05AC-06AC_standstilltest50km",
            "04B-05AC-06AD_standstillvaccinate50km",
            "04B-05AC-06BC_restriction50kmtest50km",
            "04B-05AC-06BD_restriction50kmvaccinate50km",
            "04B-05BC-06AC_standstilltest50km",
            "04B-05BC-06AD_standstillvaccinate50km",
            "04B-05BC-06BC_restriction50kmtest50km",
            "04B-05BC-06BD_restriction50kmvaccinate50km",
        ]

    for folder in folder_path_list:
        folder_path = os.path.join(folder_path_main, folder)

        time_plot = timerange[0]
        time_list = []
        while time_plot < timerange[1]:
            print(time_plot)
            time_list.append(time_plot)

            plotting_data_name = os.path.join(folder_path, f"plotting_data{time_plot}")
            with open(plotting_data_name, "rb") as file:
                properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

            xlims = [146, 150.1]
            ylims = [-33.5, -29.9]

            if "standstill" in folder:
                controlzone["movement restrictions"] = None

            output.plot_simex(
                properties,
                time,
                xlims,
                ylims,
                folder_path,
                contacts_for_plotting,
                controlzone=controlzone,
                plot_name=folder,
            )

            print(time_plot + 0.5)
            time_list.append(time_plot + 0.5)
            plotting_data_name = os.path.join(folder_path, f"plotting_data{time_plot+0.5}")
            with open(plotting_data_name, "rb") as file:
                properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

            xlims = [146, 150.1]
            ylims = [-33.5, -29.9]

            if "standstill" in folder:
                controlzone["movement restrictions"] = None

            output.plot_simex(
                properties,
                time_plot + 0.5,
                xlims,
                ylims,
                folder_path,
                contacts_for_plotting,
                controlzone=controlzone,
                plot_name=folder,
            )

            time_plot += 1

        output.make_video(folder_path, f"plot_{folder}_", time_list, "")

        # plot number of notified properties over time

        # download the outbreak state
        properties_filename = os.path.join(folder_path, "properties_" + folder)
        with open(properties_filename, "rb") as file:
            properties = pickle.load(file)

        # get notification_date

        dates_list = [convert_time_to_date(time) for time in range(28, timerange[1])]
        daily_notifs = [0] * len(dates_list)

        for property_i in properties:
            notif_date = property_i.notification_date
            if notif_date != "NA":
                index = dates_list.index(notif_date)
                daily_notifs[index] += 1

        save_name = "daily_notifications"

        output.plot_daily_notifications_over_time(dates_list, daily_notifs, folder_path, save_name)

        # plot the full outbreak window at end time point

        plotting_data_name = os.path.join(folder_path, f"plotting_data{timerange[1]-1}.5")
        with open(plotting_data_name, "rb") as file:
            properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

        # xlims = [144.5, 151.5]
        # ylims = [-34.5, -28.5]

        output.plot_simex(
            properties,
            time,
            xlims,
            ylims,
            folder_path_radius_50km_B,
            contacts_for_plotting={},
            xylabels=True,
            save_suffix="_v2",
            controlzone=controlzone,
            plot_name="full_window",
        )

    exit(1)
