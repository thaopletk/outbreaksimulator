""" v0.5

    This script runs code to simulate an FMD outbreak seeded in Victoria

"""

import sys
import os
import json
import pickle
import random
import numpy as np
import subprocess


sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.simulator as simulator
import simulator.output as output
import simulator.disease_simulation as disease_simulation
import simulator.management as management
import simulator.premises as premises
import simulator.spatial_functions as spatial_functions
import simulator.spatial_setup as spatial_setup

folder_path_main = os.path.join(os.path.dirname(__file__), "v05")

# make main folder if it doesn't exist
if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)

# generate map and properties
# extension: generate a random map using, e.g., perlin noise

small_ver = "_small"  # for testing purposes
# small_ver = ""  # for running on the cluster


with open(os.path.join(folder_path_main, f"spatial_only_parameters{small_ver}.json"), "r") as file:
    spatial_only_parameters = json.load(file)  # has the total number of properties, hence the {small_ver}

# 1. Spatial-only, property-type-agnostic setup
spatial_only_filename = os.path.join(folder_path_main, "spatial_only_setup.pickle")
if not os.path.exists(spatial_only_filename):
    (
        property_coordinates,
        adjacency_matrix,
        neighbour_pairs,
        neighbourhoods,
        property_polygons,
        property_polygons_puffed,
        property_areas,
    ) = spatial_setup.generate_properties_with_land(
        spatial_only_parameters["n"],
        spatial_only_parameters["r_wind"],
        spatial_only_parameters["xrange"],
        spatial_only_parameters["yrange"],
        spatial_only_parameters["average_property_ha"],
    )

    output.plot_map_land(
        property_polygons,
        property_polygons_puffed,
        spatial_only_parameters["xrange"],
        spatial_only_parameters["yrange"],
        folder_path_main,
    )

    with open(spatial_only_filename, "wb") as file:
        pickle.dump(
            [
                property_coordinates,
                adjacency_matrix,
                neighbour_pairs,
                neighbourhoods,
                property_polygons,
                property_polygons_puffed,
                property_areas,
            ],
            file,
        )
else:
    with open(spatial_only_filename, "rb") as file:
        (
            property_coordinates,
            adjacency_matrix,
            neighbour_pairs,
            neighbourhoods,
            property_polygons,
            property_polygons_puffed,
            property_areas,
        ) = pickle.load(file)

# 2. Property-specific initialisation
properties_filename = os.path.join(folder_path_main, "properties_init")

with open(os.path.join(folder_path_main, f"properties_specific_parameters.json"), "r") as file:
    properties_specific_parameters = json.load(file)


random.seed(1)
np.random.seed(1)

if not os.path.exists(properties_filename):
    # set up properties
    properties = simulator.property_specific_initialisation_animals(
        spatial_only_parameters,
        properties_specific_parameters,
        property_coordinates,
        property_areas,
        neighbourhoods,
        property_polygons,
        property_polygons_puffed,
    )

    with open(properties_filename, "wb") as file:
        pickle.dump(properties, file)

else:
    # load properties
    with open(properties_filename, "rb") as file:
        properties = pickle.load(file)


# limits for the figures
xlims = [
    round(spatial_only_parameters["xrange"][0], 2) - 0.005,
    round(spatial_only_parameters["xrange"][1], 2) + 0.005,
]
ylims = [
    round(spatial_only_parameters["yrange"][0], 1) - 0.05,
    round(spatial_only_parameters["yrange"][1], 1) + 0.05,
]


# plot the neighbours (not wind-neighbours)
if not os.path.exists(os.path.join(folder_path_main, "map_underlying_neighbours.png")):
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


# seed infection
time = 0

folder_path_seed = os.path.join(folder_path_main, "01_seed")
if not os.path.exists(folder_path_seed):
    os.makedirs(folder_path_seed)

# parameters
with open(os.path.join(folder_path_main, "disease_parameters.json"), "r") as file:
    disease_parameters = json.load(file)

properties_seeded_filename = os.path.join(folder_path_seed, "properties_0")

northVICx = [141, 147]
northVICy = [-37, -34]


random.seed(52)
np.random.seed(23)
if not os.path.exists(properties_seeded_filename):
    # seed property
    unique_output = "day0"
    properties, seed_property = simulator.seed_infection_within_bound(
        northVICx,
        northVICy,
        properties,
        time,
        xlims,
        ylims,
        folder_path_seed,
        unique_output,
        None,  # disease_parameters["latent_period"],
        disease_parameters,
    )
    # seeds infection within bounds (QLDx,QLDy) and does some plotting and saving

else:
    with open(properties_seeded_filename, "rb") as file:
        properties = pickle.load(file)


# spread and then detection after a fixed number of properties infected...
random.seed(10)
np.random.seed(10)
minimum_spread_time = 21
target_infected_properties = 5


# area for first report Victoria
reportingregion_x = [141, 150]
reportingregion_y = [-40, -34]


unique_output = f"02_undetected_spread"
folder_path_undetected_spread = os.path.join(folder_path_main, unique_output)
if not os.path.exists(folder_path_undetected_spread):
    os.makedirs(folder_path_undetected_spread)

undetected_spread_properties_filename = os.path.join(folder_path_undetected_spread, "properties_" + unique_output)
undetected_spread_diseaseoutbreak_filename = os.path.join(
    folder_path_undetected_spread, "outbreakobject_" + unique_output
)


with open(os.path.join(folder_path_main, "job_parameters.json"), "r") as file:
    job_parameters = json.load(file)
with open(os.path.join(folder_path_main, "scenario_parameters.json"), "r") as file:
    scenario_parameters = json.load(file)


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

    # print(diseaseoutbreak.job_manager.jobs_queue)

    properties, movement_records, time = diseaseoutbreak.simulate_outbreak_spread_only(
        properties=properties,
        time=time,
        stop_time=minimum_spread_time,
        reporting_region_check=[reportingregion_x, reportingregion_y],
        min_infected_premises=target_infected_properties,
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

    print(f"Total number of infected premises: {total_infected}")

else:
    with open(undetected_spread_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(undetected_spread_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)


# trigger first report and early time processes (no change for now)
unique_output = "03_outbreak_detection"
folder_path_first_report = os.path.join(folder_path_main, unique_output)

if not os.path.exists(folder_path_first_report):
    os.makedirs(folder_path_first_report)

spread_properties_filename = os.path.join(folder_path_first_report, "properties_" + unique_output)
spread_diseaseoutbreak_filename = os.path.join(folder_path_first_report, "outbreakobject_" + unique_output)

random.seed(15)
np.random.seed(16)
if not os.path.exists(spread_properties_filename) or not os.path.exists(spread_diseaseoutbreak_filename):

    # # setting up a new disease outbreak object (uncomment if I make changes to disease_simulation.py but don't run from the top)
    # diseaseoutbreak_new = disease_simulation.DiseaseSimulation(
    #     time=diseaseoutbreak.time,
    #     disease_parameters=disease_parameters,
    #     spatial_only_parameters=spatial_only_parameters,
    #     job_parameters=job_parameters,
    #     scenario_parameters=scenario_parameters,
    # )
    # diseaseoutbreak_new.movement_records = diseaseoutbreak.movement_records
    # diseaseoutbreak_new.vax_modifier = diseaseoutbreak.vax_modifier
    # diseaseoutbreak_new.combined_narrative = diseaseoutbreak.combined_narrative
    # diseaseoutbreak_new.job_manager = diseaseoutbreak.job_manager
    # diseaseoutbreak_new.total_culled_animals = diseaseoutbreak.total_culled_animals
    # diseaseoutbreak_new.controlzone = diseaseoutbreak.controlzone
    # diseaseoutbreak_new.contacts_for_plotting = diseaseoutbreak.contacts_for_plotting
    # diseaseoutbreak_new.daily_statistics = diseaseoutbreak.daily_statistics
    # diseaseoutbreak_new.first_detection_day = diseaseoutbreak.first_detection_day

    # diseaseoutbreak = diseaseoutbreak_new

    # adjust the plotting parameters for this new scenario
    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path_first_report,
        unique_output=unique_output,
    )

    first_detection_day = diseaseoutbreak.time + 1

    # print(diseaseoutbreak.job_manager.jobs_queue)

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


# try two weeks of simulation, but with a national standstill now.
unique_output = f"04_to_first_decision_point"
folder_path = os.path.join(folder_path_main, unique_output)
days_to_run_for = 7 * 2

if not os.path.exists(folder_path):
    os.makedirs(folder_path)

spread_properties_filename = os.path.join(folder_path, "properties_" + unique_output)
spread_diseaseoutbreak_filename = os.path.join(folder_path, "outbreakobject_" + unique_output)

management_parameters = {"movement_restrictions": ["national_standstill"]}

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

    total_infected = 0
    for property_i in properties:
        if property_i.exposure_date != "NA":
            total_infected += 1

    print(f"Total number of infected premises: {total_infected}")


# then base example decision - high resourcing, but no more standstill
