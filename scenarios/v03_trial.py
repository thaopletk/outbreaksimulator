""" v0.3 Trial

This script controls and run different elements and steps, testing the expanded version of the code post v0.2 


"""

import sys
import os
import json
import pickle

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.simulator as simulator
import simulator.output as output
import simulator.disease_simulation as disease_simulation
import simulator.management as management
import simulator.premises as premises


folder_path_main = os.path.join(os.path.dirname(__file__), "outputs", "v03_trial")
folder_path_seed = os.path.join(folder_path_main, "01_seed")


# step 1: make main folder if it doesn't exist
if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)

# step 2: initiate the full proper map, including with different property types
# parameters
small_ver = "_small"
# small_ver = "" # for running on the cluster

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

properties_filename = os.path.join(folder_path_main, "properties_init")
if not os.path.exists(properties_filename):
    property_setup_info = simulator.property_setup_v03(
        folder_path_main, spatial_only_parameters, properties_specific_parameters
    )

    (
        properties,
        property_coordinates,
        adjacency_matrix,
        neighbour_pairs,
        neighbourhoods,
        property_polygons,
        property_polygons_puffed,
        property_areas,
    ) = property_setup_info


else:
    # load properties
    with open(properties_filename, "rb") as file:
        properties = pickle.load(file)


# plot the neighbours (not wind-neighbours)
if not os.path.exists(os.path.join(folder_path_main, "map_underlying0.png")):
    output.plot_map(
        properties,
        time=0,
        xlims=xlims,
        ylims=ylims,
        folder_path=folder_path_main,
        real_situation=True,
        controlzone=None,
        infectionpoly=False,
        contacts_for_plotting={},
        show_movement_neighbours=True,
    )

# TODO plotting animal density seems to take a lot of time, should make it better /faster
# or could just run it on the cluster anyway? and fix things via photoshop
# plot the animal density
if not os.path.exists(os.path.join(folder_path_main, "animal_density.png")):
    output.plot_animal_density(properties, xlims, ylims, folder_path=folder_path_main)

if not os.path.exists(os.path.join(folder_path_main, "animals.png")):
    output.plot_animals(properties, xlims, ylims, folder_path=folder_path_main)


# step 3:  initial seeding of a property
# the initial seeding will occur in Northern Queensland
# COULD TODO: make seeding occur either near a major port
# to get something near major cities, I should get their lat/long positions, (either hard code or download something from ABS), and allow spread to a wind-radius around those cities.

time = 0
if not os.path.exists(folder_path_seed):
    os.makedirs(folder_path_seed)

# parameters
with open(os.path.join(folder_path_main, "disease_parameters.json"), "r") as file:
    disease_parameters = json.load(file)

properties_seeded_filename = os.path.join(folder_path_seed, "properties_0")

northQLDx = [141, 146]
northQLDy = [-17, -10]
if not os.path.exists(properties_seeded_filename):
    # seed property
    unique_output = "day0"

    properties, seed_property = simulator.seed_infection_within_bound(
        northQLDx,
        northQLDy,
        properties,
        time,
        xlims,
        ylims,
        folder_path_seed,
        unique_output,
        disease_parameters["latent_period"],
    )
    # seeds infection within bounds (northQLDx,northQLDy) and does some plotting and saving

else:
    with open(properties_seeded_filename, "rb") as file:
        properties = pickle.load(file)

# step 4:  simulate undetected spread ~ 28 days)
unique_output = "02_undetected_spread"
folder_path_undetected_spread = os.path.join(folder_path_main, unique_output)

if not os.path.exists(folder_path_undetected_spread):
    os.makedirs(folder_path_undetected_spread)

# TODO could change this so that it runs until there are X number of infected properties in each of the main states or territories
stop_time = 65  # 28
first_detection_day = stop_time + 1

undetected_spread_properties_filename = os.path.join(folder_path_undetected_spread, "properties_" + unique_output)
undetected_spread_diseaseoutbreak_filename = os.path.join(
    folder_path_undetected_spread, "outbreakobject_" + unique_output
)
if not os.path.exists(undetected_spread_properties_filename) or not os.path.exists(
    undetected_spread_diseaseoutbreak_filename
):

    # initiate various things that start from empty:
    diseaseoutbreak = disease_simulation.DiseaseSimulation(
        time=time,
        disease_parameters=disease_parameters,
        spatial_only_parameters=spatial_only_parameters,
        job_parameters=job_parameters,
        scenario_parameters=scenario_parameters,
    )

    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path_undetected_spread,
        unique_output=unique_output,
    )

    properties, movement_records, time = diseaseoutbreak.simulate_outbreak_spread_only(
        properties=properties, time=time, stop_time=stop_time
    )

    # and then resave the end state
    with open(undetected_spread_properties_filename, "wb") as file:
        pickle.dump(properties, file)

    # and save the diseaseoutbreak object
    with open(undetected_spread_diseaseoutbreak_filename, "wb") as file:
        pickle.dump(diseaseoutbreak, file)

else:

    with open(undetected_spread_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(undetected_spread_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)


# Step 5: trigger the first report in northern NSW and initial actions
# the early time processes
# start the default processes (contact tracing, assume that clinical confirmation is immediate, lab testing in process). Management jobs are stored in a job manager object. The day will probably end with minimal movement restrictions for the infected property and the contact traced properties.
# These properties should shown on a map
unique_output = "03_outbreak_detection"
folder_path_first_report = os.path.join(folder_path_main, unique_output)

if not os.path.exists(folder_path_first_report):
    os.makedirs(folder_path_first_report)

spread_properties_filename = os.path.join(folder_path_first_report, "properties_" + unique_output)
spread_diseaseoutbreak_filename = os.path.join(folder_path_first_report, "outbreakobject_" + unique_output)

if not os.path.exists(spread_properties_filename) or not os.path.exists(spread_diseaseoutbreak_filename):
    # adjust the plotting parameters for this new scenario
    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path_first_report,
        unique_output=unique_output,
    )

    reportingregion_x = [140, 155]
    reportingregion_y = [-31, -29]

    properties, movement_records, time, total_culled_animals, job_manager = diseaseoutbreak.simulate_first_two_days(
        properties, reportingregion_x, reportingregion_y
    )

    # and then resave the end state
    with open(spread_properties_filename, "wb") as file:
        pickle.dump(properties, file)

    # and save the diseaseoutbreak object
    with open(spread_diseaseoutbreak_filename, "wb") as file:
        pickle.dump(diseaseoutbreak, file)
else:
    with open(spread_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(spread_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)

# Step 6: three days of a national standstill to conduct more contact tracing and testing and figure out the situation
unique_output = "04_national_standstill"
folder_path = os.path.join(folder_path_main, unique_output)
days_to_run_for = 3
management_parameters = [{"type": "national_standstill"}]
# and during this time period, will  conduct clinical observations, and schedule testing regardless (DCPs basically)

if not os.path.exists(folder_path):
    os.makedirs(folder_path)

spread_properties_filename = os.path.join(folder_path, "properties_" + unique_output)
spread_diseaseoutbreak_filename = os.path.join(folder_path, "outbreakobject_" + unique_output)

if not os.path.exists(spread_properties_filename) or not os.path.exists(spread_diseaseoutbreak_filename):
    # adjust the plotting parameters for this new scenario
    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path,
        unique_output=unique_output,
    )

    properties, movement_records, time, total_culled_animals, job_manager = (
        diseaseoutbreak.simulate_national_standstill(properties, days_to_run_for)
    )

    # and then resave the end state
    with open(spread_properties_filename, "wb") as file:
        pickle.dump(properties, file)

    # and save the diseaseoutbreak object
    with open(spread_diseaseoutbreak_filename, "wb") as file:
        pickle.dump(diseaseoutbreak, file)

    job_manager.calculate_resources_used(folder_path)

    # plot number of notified properties over time TODO
    # TODO: save it as a csv as well
    dates_list = [
        premises.convert_time_to_date(time)
        for time in range(first_detection_day, first_detection_day + days_to_run_for + 2)
    ]
    print(dates_list)
    daily_notifs = [0] * len(dates_list)

    for property_i in properties:
        notif_date = property_i.notification_date
        if notif_date != "NA":
            index = dates_list.index(notif_date)
            daily_notifs[index] += 1

    save_name = "movement_standstill_daily_notifications"

    output.plot_daily_notifications_over_time(dates_list, daily_notifs, folder_path, save_name)

    # plot the full outbreak window at end time point

    # plotting_data_name = os.path.join(folder_path, f"plotting_data{time}")
    # with open(plotting_data_name, "rb") as file:
    #     properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

    # TODO - this wasn't working - fix it
    # output.plot_simex(properties,time,xlims,ylims,folder_path,contacts_for_plotting={},xylabels = True,save_suffix="_v2")


else:
    with open(spread_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(spread_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)

# step 7
# about two weeks of simulation
unique_output = "05_two_weeks"
folder_path = os.path.join(folder_path_main, unique_output)
days_to_run_for = 14 - 3
management_parameters = [
    {"type": "movement_restriction", "radius_km": 5, "convex": False},
    {"type": "conditional_movement", "radius_km": 80, "convex": False, "probability_reduction": 0.1},
    {"type": "ring_surveillance", "radius_km": 80, "convex": False},
]
jobs_resourcing = {
    "LabTesting": [10, 15, 20],
    "ClinicalObservation": [20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130],
    "Cull": [10],
    "ContactTracing": [100],
}

if not os.path.exists(folder_path):
    os.makedirs(folder_path)

spread_properties_filename = os.path.join(folder_path, "properties_" + unique_output)
spread_diseaseoutbreak_filename = os.path.join(folder_path, "outbreakobject_" + unique_output)

if not os.path.exists(spread_properties_filename) or not os.path.exists(spread_diseaseoutbreak_filename):
    # adjust the plotting parameters for this new scenario
    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path,
        unique_output=unique_output,
    )

    # TODO not complete
    properties, movement_records, time, total_culled_animals, job_manager = (
        diseaseoutbreak.simulate_outbreak_management(
            properties, management_parameters, days_to_run_for, jobs_resourcing
        )
    )

    # and then resave the end state
    with open(spread_properties_filename, "wb") as file:
        pickle.dump(properties, file)

    # and save the diseaseoutbreak object
    with open(spread_diseaseoutbreak_filename, "wb") as file:
        pickle.dump(diseaseoutbreak, file)

    # TODO: add in a "total" column? or add in relative costs/estimated costs and a total estimated cost...
    job_manager.calculate_resources_used(folder_path)

    # plot number of notified properties over time TODO
    dates_list = [
        premises.convert_time_to_date(time)
        for time in range(first_detection_day, first_detection_day + days_to_run_for + 2)
    ]
    print(dates_list)
    daily_notifs = [0] * len(dates_list)

    for property_i in properties:
        notif_date = property_i.notification_date
        if notif_date != "NA":
            index = dates_list.index(notif_date)
            daily_notifs[index] += 1

    save_name = "movement_standstill_daily_notifications"

    output.plot_daily_notifications_over_time(dates_list, daily_notifs, folder_path, save_name)

    # plot the full outbreak window at end time point

    # plotting_data_name = os.path.join(folder_path, f"plotting_data{time}")
    # with open(plotting_data_name, "rb") as file:
    #     properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

    # output.plot_simex(
    #     properties, time, xlims, ylims, folder_path, contacts_for_plotting={}, xylabels=True, save_suffix="_v2"
    # )

else:
    with open(spread_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(spread_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)
