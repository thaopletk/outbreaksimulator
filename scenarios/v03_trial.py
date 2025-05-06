""" v0.3 Trial

This script controls and run different elements and steps, testing the expanded version of the code post v0.2 


"""

import sys
import os
import json
import pickle
import random
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.simulator as simulator
import simulator.output as output
import simulator.disease_simulation as disease_simulation
import simulator.management as management
import simulator.premises as premises
import simulator.spatial_functions as spatial_functions

folder_path_main = os.path.join(os.path.dirname(__file__), "outputs", "v03_trial")
folder_path_seed = os.path.join(folder_path_main, "01_seed")

# step 1: make main folder if it doesn't exist
if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)

# step 2: initiate the full proper map, including with different property types
# parameters
small_ver = "_small"
small_ver = ""  # for running on the cluster

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

# area for first report
reportingregion_x = [140, 155]
reportingregion_y = [-32, -29]

properties_filename = os.path.join(folder_path_main, "properties_init")

random.seed(10)
np.random.seed(11)


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


# plot the animal density
if not os.path.exists(os.path.join(folder_path_main, "animal_density.png")):
    output.plot_animal_density(properties, xlims, ylims, folder_path=folder_path_main)

# if not os.path.exists(os.path.join(folder_path_main, "animals.png")):
#     output.plot_animals(properties, xlims, ylims, folder_path=folder_path_main)
# if not os.path.exists(os.path.join(folder_path_main, "animal_density_hist2D.png")):
#     output.plot_animal_density_hist2d(properties, xlims, ylims, folder_path=folder_path_main)


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


random.seed(12)
np.random.seed(13)
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
stop_time = 21  # 28
first_detection_day = stop_time + 1

undetected_spread_properties_filename = os.path.join(folder_path_undetected_spread, "properties_" + unique_output)
undetected_spread_diseaseoutbreak_filename = os.path.join(
    folder_path_undetected_spread, "outbreakobject_" + unique_output
)


random.seed(13)
np.random.seed(14)

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

    print(diseaseoutbreak.job_manager.jobs_queue)

    properties, movement_records, time = diseaseoutbreak.simulate_outbreak_spread_only(
        properties=properties,
        time=time,
        stop_time=stop_time,
        reporting_region_check=[reportingregion_x, reportingregion_y],
    )

    first_detection_day = time + 1

    # and then resave the end state
    with open(undetected_spread_properties_filename, "wb") as file:
        pickle.dump(properties, file)

    # and save the diseaseoutbreak object
    with open(undetected_spread_diseaseoutbreak_filename, "wb") as file:
        pickle.dump(diseaseoutbreak, file)

    total_infected = 0
    for property_i in properties:
        if property_i.exposure_date != "NA":
            total_infected += 1

    if total_infected > 150:
        raise ValueError("Total number of infected premises at time of detection is too high, run again!")


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

random.seed(15)
np.random.seed(16)
if not os.path.exists(spread_properties_filename) or not os.path.exists(spread_diseaseoutbreak_filename):
    # adjust the plotting parameters for this new scenario
    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path_first_report,
        unique_output=unique_output,
    )

    first_detection_day = diseaseoutbreak.time + 1

    print(diseaseoutbreak.job_manager.jobs_queue)

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

# TODO - to actually get the first detection date, get the first/smaller number of file in the simulate-first-two-days folder...


# step 6
# about two weeks of simulation
unique_output = "04_two_weeks"
folder_path = os.path.join(folder_path_main, unique_output)
days_to_run_for = 14

management_parameters = [  # TODO - currently not used...could actually implement it...
    {"type": "movement_restriction", "radius_km": 5, "convex": False},
    {"type": "conditional_movement", "radius_km": 80, "convex": False, "probability_reduction": 0.1},
    {"type": "ring_surveillance", "radius_km": 80, "convex": False},
]
# jobs_resourcing = {
#     "LabTesting": [10, 15, 20],
#     "ClinicalObservation": [20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130],
#     "Cull": [10],
#     "ContactTracing": [100],
# }  # TODO - currently not used...could actually implement it...

if not os.path.exists(folder_path):
    os.makedirs(folder_path)

spread_properties_filename = os.path.join(folder_path, "properties_" + unique_output)
spread_diseaseoutbreak_filename = os.path.join(folder_path, "outbreakobject_" + unique_output)

outbreak_step_6_filenames = [
    [spread_properties_filename, spread_diseaseoutbreak_filename, unique_output],
]

random.seed(17)
np.random.seed(18)
if not os.path.exists(spread_properties_filename) or not os.path.exists(spread_diseaseoutbreak_filename):
    # adjust the plotting parameters for this new scenario
    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path,
        unique_output=unique_output,
    )

    # TODO not 100% satisfactorily complete
    properties, movement_records, time, total_culled_animals, job_manager = (
        diseaseoutbreak.simulate_outbreak_management(
            properties, management_parameters, days_to_run_for, resource_setting="default"
        )
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


# function to make it easier to run specific "branches" of the simulator "history"
def run_specific_branch(
    local_properties_filename,
    local_diseaseoutbreak_filename,
    properties_filename,
    diseaseoutbreak_filename,
    folder_path_local,
    unique_output,
    management_parameters,
    days_to_run_for,
    resource_setting,
    vaccination=False,
):

    if not os.path.exists(local_properties_filename) or not os.path.exists(local_diseaseoutbreak_filename):

        with open(properties_filename, "rb") as file:
            properties = pickle.load(file)
        with open(diseaseoutbreak_filename, "rb") as file:
            diseaseoutbreak = pickle.load(file)

        # adjust the plotting parameters for this new scenario
        diseaseoutbreak.set_plotting_parameters(
            xlims=xlims,
            ylims=ylims,
            plotting=True,
            folder_path=folder_path_local,
            unique_output=unique_output,
        )

        properties, movement_records, time, total_culled_animals, job_manager = (
            diseaseoutbreak.simulate_outbreak_management(
                properties, management_parameters, days_to_run_for, resource_setting, vaccination
            )
        )

        # and then resave the end state
        with open(local_properties_filename, "wb") as file:
            pickle.dump(properties, file)

        # and save the diseaseoutbreak object
        with open(local_diseaseoutbreak_filename, "wb") as file:
            pickle.dump(diseaseoutbreak, file)


# STEP 7: run some different options after decision-making
days_to_run_for = 14

outbreak_step_7_filenames = []

management_parameters = []  # dummy parameters because they're not actually used right now

# NOTE this could be parallellised, or run as multiple jobs on the cluster.
for properties_filename, diseaseoutbreak_filename, identifier in outbreak_step_6_filenames:
    long_name = ""
    short_code = identifier  # not used here, since there is only one history in outbreak_step_6_filenames
    for resource_setting in ["high", "low"]:
        unique_output = "05_two_weeks_" + resource_setting
        folder_path_local = os.path.join(folder_path_main, unique_output)
        if not os.path.exists(folder_path_local):
            os.makedirs(folder_path_local)
        local_properties_filename = os.path.join(folder_path_local, "properties_" + unique_output)
        local_diseaseoutbreak_filename = os.path.join(folder_path_local, "outbreakobject_" + unique_output)

        outbreak_step_7_filenames.append(
            [local_properties_filename, local_diseaseoutbreak_filename, resource_setting]
        )  # note, have set identifier = resource_setting

        random.seed(19)
        np.random.seed(20)
        run_specific_branch(
            local_properties_filename,
            local_diseaseoutbreak_filename,
            properties_filename,
            diseaseoutbreak_filename,
            folder_path_local,
            unique_output,
            management_parameters,
            days_to_run_for,
            resource_setting,
        )


# STEP 8: phase 3, high/low resource status with vaccination or no vaccination
days_to_run_for = 28

outbreak_step_8_filenames = []

management_parameters = []  # dummy parameters because they're not actually used right now

# NOTE this could be parallellised, or run as multiple jobs on the cluster.
for properties_filename, diseaseoutbreak_filename, step7_resource_setting in outbreak_step_7_filenames:
    for resource_setting in ["high", "low"]:
        for vaccination in [True, False]:
            unique_output = f"05_{step7_resource_setting}_06_{resource_setting}_{vaccination}"
            folder_path_local = os.path.join(folder_path_main, unique_output)
            if not os.path.exists(folder_path_local):
                os.makedirs(folder_path_local)
            local_properties_filename = os.path.join(folder_path_local, "properties_" + unique_output)
            local_diseaseoutbreak_filename = os.path.join(folder_path_local, "outbreakobject_" + unique_output)

            outbreak_step_8_filenames.append(
                [local_properties_filename, local_diseaseoutbreak_filename, unique_output]
            )  # note, have set identifier = unique_output

            random.seed(21)
            np.random.seed(22)
            run_specific_branch(
                local_properties_filename,
                local_diseaseoutbreak_filename,
                properties_filename,
                diseaseoutbreak_filename,
                folder_path_local,
                unique_output,
                management_parameters,
                days_to_run_for,
                resource_setting,
                vaccination,
            )
