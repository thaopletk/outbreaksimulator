""" Main control

Aim: for this script to control and run different elements and steps needed for the trial simulation exercise.


"""

import sys
import os
import json
import pickle

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.simulator as simulator

# import simulator.management as management
import simulator.disease_simulation as disease_simulation

# folder names
folder_path_main = os.path.join(os.path.dirname(__file__), "trial_simex")
folder_path_seed = os.path.join(folder_path_main, "01_seed")
folder_path_undetected_spread_1 = os.path.join(folder_path_main, "02_undetected_spread_one_week")
folder_path_first_report = os.path.join(folder_path_main, "03_spread_til_first_report")
folder_path_movement_standstill_A = os.path.join(folder_path_main, "04A_movement_standstill_two_weeks")
folder_path_radius_50km_B = os.path.join(folder_path_main, "04B_movement_radius_50km_two_weeks")
folder_path_radius_25km_C = os.path.join(folder_path_main, "04C_movement_radius_25km_two_weeks")


# step 1: make folder for everything
# Not in output folder, so that it'll be synced...

if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)


# step 2: initiate the full proper map, including with different property types
# parameters
with open(os.path.join(folder_path_main, "spatial_only_parameters.json"), "r") as file:
    spatial_only_parameters = json.load(file)
with open(os.path.join(folder_path_main, "properties_specific_parameters.json"), "r") as file:
    properties_specific_parameters = json.load(file)
with open(os.path.join(folder_path_main, "job_parameters.json"), "r") as file:
    job_parameters = json.load(file)
with open(os.path.join(folder_path_main, "scenario_parameters.json"), "r") as file:
    scenario_parameters = json.load(file)
# properties_filename = os.path.join(folder_path_main, "properties_initialised.pickle")
properties_filename = os.path.join(folder_path_main, "properties_init")
if not os.path.exists(properties_filename):
    property_setup_info = simulator.trial_simex_property_setup(
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


# limits for the figures
xlims = [
    round(spatial_only_parameters["xrange"][0], 2) - 0.005,
    round(spatial_only_parameters["xrange"][1], 2) + 0.005,
]
ylims = [
    round(spatial_only_parameters["yrange"][0], 1) - 0.05,
    round(spatial_only_parameters["yrange"][1], 1) + 0.05,
]

# parameters
with open(os.path.join(folder_path_main, "disease_parameters.json"), "r") as file:
    disease_parameters = json.load(file)

# step 3: force initial seeding of a property in/near the center (call it a "stud farm") and save
time = 0
if not os.path.exists(folder_path_seed):
    os.makedirs(folder_path_seed)

properties_seeded_filename = os.path.join(folder_path_seed, "properties_0")
if not os.path.exists(properties_seeded_filename):
    # seed property
    unique_output = "day0"

    properties, seed_property = simulator.seed_infection_at_property_type(
        spatial_only_parameters["xrange"],
        spatial_only_parameters["yrange"],
        properties,
        "stud farm",
        time,
        xlims,
        ylims,
        folder_path_seed,
        unique_output,
        disease_parameters["latent_period"],
    )
    # seeds infection at stud_farm and also saves new properties output figures and tables as necessary

else:
    with open(properties_seeded_filename, "rb") as file:
        properties = pickle.load(file)

# step 4: run the simulation, including forcing some initial movements from that center seeded property (over 7 days), with undetected spread
if not os.path.exists(folder_path_undetected_spread_1):
    os.makedirs(folder_path_undetected_spread_1)

stop_time = 7
unique_output = "02_undetected_spread_one_week"
undetected_spread_properties_filename = os.path.join(folder_path_undetected_spread_1, "properties_" + unique_output)
undetected_spread_diseaseoutbreak_filename = os.path.join(
    folder_path_undetected_spread_1, "outbreakobject_" + unique_output
)
if not os.path.exists(undetected_spread_properties_filename) or not os.path.exists(
    undetected_spread_diseaseoutbreak_filename
):

    # to force some initial movements from that seeded property, adjust some of its movement parameters
    stud_farm_i = None
    for i in range(len(properties)):
        if properties[i].type == "stud farm":
            stud_farm_i = i
            p = properties[i]
            p.movement_probability = 1
            p.movement_start_day = 1
            p.movement_frequency = 1
            p.max_daily_movements = 6
            break
    if stud_farm_i == None:
        raise ValueError("Stud farm not found for some reason")

    # initiate various things that start from empty:
    movement_records = []
    diseaseoutbreak = disease_simulation.DiseaseSimulation(
        time=time,
        movement_records=movement_records,
        disease_parameters=disease_parameters,
        spatial_only_parameters=spatial_only_parameters,
        job_parameters=job_parameters,
        scenario_parameters=scenario_parameters,
    )

    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path_undetected_spread_1,
        unique_output=unique_output,
    )

    properties, movement_records, time = diseaseoutbreak.simulate_outbreak_spread_only(
        properties=properties, time=time, stop_time=stop_time
    )

    # re-adjust the seeded property movements back to normal adjust those movements down after a week
    p = properties[stud_farm_i]
    p.movement_probability = properties_specific_parameters["movement_probability"]["stud farm"]
    p.movement_frequency = properties_specific_parameters["movement_frequency"]["stud farm"]
    p.max_daily_movements = properties_specific_parameters["max_daily_movements"]["stud farm"]

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


# Step 5: continue running the simulation until the first report; start the default processes (contact tracing, assume that clinical confirmation is immediate, lab testing in process); the day will probably end with minimal movement restrictions for the infected property and the contact traced properties.
# These properties should shown on a map
# Then stop the simulation, and allow for some options for the next day of simulation
# Options: complete movement standstill, and certain radii around the infected property

if not os.path.exists(folder_path_first_report):
    os.makedirs(folder_path_first_report)
unique_output = "03_spread_til_first_report"

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

    properties, movement_records, time, total_culled_animals, job_manager = (
        diseaseoutbreak.simulate_outbreak_til_first_report(properties)
    )

    # and then resave the end state
    with open(spread_properties_filename, "wb") as file:
        pickle.dump(properties, file)

    # and save the diseaseoutbreak object
    with open(spread_diseaseoutbreak_filename, "wb") as file:
        pickle.dump(diseaseoutbreak, file)


# Step 6. Give management options: complete standstill, or standstill of certain radius. Run for TWO WEEKS,
days_to_run_for = 14

# you should be able to have multiple management happening at the same time
# it could be a list of dictionaries; the dictionary should have a management_type, and for different management types, there might be different sub parameters; for ring management, obviously there should be a ring radius, and something to flag whether or not it should be convex management
# could you have different management priorities? I don't know.

# 6A: If a complete standstill, then:

if not os.path.exists(folder_path_movement_standstill_A):
    os.makedirs(folder_path_movement_standstill_A)
unique_output = "04A_movement_standstill_two_weeks"

movement_standstill_A_properties_filename = os.path.join(
    folder_path_movement_standstill_A, "properties_" + unique_output
)
movement_standstill_A_diseaseoutbreak_filename = os.path.join(
    folder_path_movement_standstill_A, "outbreakobject_" + unique_output
)

if not os.path.exists(movement_standstill_A_properties_filename) or not os.path.exists(
    movement_standstill_A_diseaseoutbreak_filename
):
    with open(spread_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(spread_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)

    # adjust the plotting parameters for this new scenario
    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path_movement_standstill_A,
        unique_output=unique_output,
    )

    management_parameters = [{"type": "movement_standstill"}]

    properties, movement_records, time, total_culled_animals, job_manager = (
        diseaseoutbreak.simulate_outbreak_management(properties, management_parameters, days_to_run_for)
    )

    # and then resave the end state
    with open(movement_standstill_A_properties_filename, "wb") as file:
        pickle.dump(properties, file)

    # and save the diseaseoutbreak object
    with open(movement_standstill_A_diseaseoutbreak_filename, "wb") as file:
        pickle.dump(diseaseoutbreak, file)


# 6B: movement radius of 50km
if not os.path.exists(folder_path_radius_50km_B):
    os.makedirs(folder_path_radius_50km_B)
unique_output = "04B_movement_radius_50km_two_weeks"

radius_50km_B_properties_filename = os.path.join(folder_path_radius_50km_B, "properties_" + unique_output)
radius_50km_B_diseaseoutbreak_filename = os.path.join(folder_path_radius_50km_B, "outbreakobject_" + unique_output)
if not os.path.exists(radius_50km_B_properties_filename) or not os.path.exists(radius_50km_B_diseaseoutbreak_filename):
    with open(spread_properties_filename, "rb") as file:
        properties = pickle.load(file)
    with open(spread_diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)

    # adjust the plotting parameters for this new scenario
    diseaseoutbreak.set_plotting_parameters(
        xlims=xlims,
        ylims=ylims,
        plotting=True,
        folder_path=folder_path_radius_50km_B,
        unique_output=unique_output,
    )

    management_parameters = [{"type": "movement_restriction", "radius_km": 50, "convex": False}]

    properties, movement_records, time, total_culled_animals, job_manager = (
        diseaseoutbreak.simulate_outbreak_management(properties, management_parameters, days_to_run_for)
    )

    # and then resave the end state
    with open(radius_50km_B_properties_filename, "wb") as file:
        pickle.dump(properties, file)

    # and save the diseaseoutbreak object
    with open(radius_50km_B_diseaseoutbreak_filename, "wb") as file:
        pickle.dump(diseaseoutbreak, file)


# NOT DOING THIS - too many options
# # 6C: movement radius of 25km
# if not os.path.exists(folder_path_radius_25km_C):
#     os.makedirs(folder_path_radius_25km_C)
# unique_output = "04C_movement_radius_25km_two_weeks"

# radius_25km_C_properties_filename = os.path.join(folder_path_radius_25km_C, "properties_" + unique_output)
# radius_25km_C_diseaseoutbreak_filename = os.path.join(folder_path_radius_25km_C, "outbreakobject_" + unique_output)
# if not os.path.exists(radius_25km_C_properties_filename) or not os.path.exists(radius_25km_C_diseaseoutbreak_filename):
#     with open(spread_properties_filename, "rb") as file:
#         properties = pickle.load(file)
#     with open(spread_diseaseoutbreak_filename, "rb") as file:
#         diseaseoutbreak = pickle.load(file)

#     # adjust the plotting parameters for this new scenario
#     diseaseoutbreak.set_plotting_parameters(
#         xlims=xlims,
#         ylims=ylims,
#         plotting=True,
#         folder_path=folder_path_radius_25km_C,
#         unique_output=unique_output,
#     )

#     management_parameters = [{"type": "movement_restriction", "radius_km": 25, "convex": False}]

#     properties, movement_records, time, total_culled_animals, job_manager = (
#         diseaseoutbreak.simulate_outbreak_management(properties, management_parameters, days_to_run_for)
#     )

#     # and then resave the end state
#     with open(radius_25km_C_properties_filename, "wb") as file:
#         pickle.dump(properties, file)

#     # and save the diseaseoutbreak object
#     with open(radius_25km_C_diseaseoutbreak_filename, "wb") as file:
#         pickle.dump(diseaseoutbreak, file)


def run_specific_branch(
    local_properties_filename,
    local_diseaseoutbreak_filename,
    properties_filename,
    diseaseoutbreak_filename,
    folder_path_local,
    unique_output,
    management_parameters,
    days_to_run_for,
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
            diseaseoutbreak.simulate_outbreak_management(properties, management_parameters, days_to_run_for)
        )

        # and then resave the end state
        with open(local_properties_filename, "wb") as file:
            pickle.dump(properties, file)

        # and save the diseaseoutbreak object
        with open(local_diseaseoutbreak_filename, "wb") as file:
            pickle.dump(diseaseoutbreak, file)


# Step 7: now there are options regarding ring culling, OR ring testing (at fixed radius, maybe 25km, no ring surveillance, too many options...). There should also be options regarding the changing (or not) of movement restriction radius. Run for TWO WEEKS,
days_to_run_for = 14
previous_outbreak_step_filenames = [
    [movement_standstill_A_properties_filename, movement_standstill_A_diseaseoutbreak_filename, "04A"],
    [radius_50km_B_properties_filename, radius_50km_B_diseaseoutbreak_filename, "04B"],
    # [radius_25km_C_properties_filename, radius_25km_C_diseaseoutbreak_filename, "04C"],
]

outbreak_step_7_filenames = []

# TODO is to see if many of these can be run in parallel
# (if it was the cluster, then you would submit multiple jobs ah)

for properties_filename, diseaseoutbreak_filename, identifier in previous_outbreak_step_filenames:
    long_name = ""
    short_code = identifier
    # NOTE: taking out 25km, to limit options
    for new_movement_option in ["standstill", "restriction50km"]:  # , "restriction25km"]:
        short_code_1 = short_code
        long_name_1 = new_movement_option
        if new_movement_option == "standstill":
            management_parameters = [{"type": "movement_standstill"}]
            short_code_1 += "-05A"
        elif new_movement_option == "restriction50km":
            management_parameters = [{"type": "movement_restriction", "radius_km": 50, "convex": False}]
            short_code_1 += "-05B"
        elif new_movement_option == "restriction25km":
            management_parameters = [{"type": "movement_restriction", "radius_km": 25, "convex": False}]
            short_code_1 += "-05C"
        else:
            raise ValueError("Ring management option not identified")

        # should also include the option of NOT doing anything more
        for ring_management_option, management_identifier in [
            # ["", "_only"], # taking this out too, to say that "outbreak is intensifying, need more management--i.e., ring testing in addition to contact tracing"
            # ["ring culling", "_cull25km"], # NOTE ring cullinng is not considered; reason: "no social license / too much protesting"
            ["ring testing", "_test30km"],
        ]:
            long_name_2 = long_name_1 + management_identifier
            short_code_2 = short_code_1
            if ring_management_option == "":
                short_code_2 += "A"
            elif ring_management_option == "ring culling":
                management_parameters.append({"type": "ring_culling", "radius_km": 25, "convex": False})
                short_code_2 += "B"
            elif ring_management_option == "ring testing":
                management_parameters.append({"type": "ring_testing", "radius_km": 30, "convex": False})
                short_code_2 += "C"
            else:
                raise ValueError("Ring management option not identified")
                # ring testing is currently a combination of clinical observation and lab testing

            unique_output = short_code_2 + "_" + long_name_2
            folder_path_local = os.path.join(folder_path_main, unique_output)
            if not os.path.exists(folder_path_local):
                os.makedirs(folder_path_local)
            local_properties_filename = os.path.join(folder_path_local, "properties_" + unique_output)
            local_diseaseoutbreak_filename = os.path.join(folder_path_local, "outbreakobject_" + unique_output)

            outbreak_step_7_filenames.append([local_properties_filename, local_diseaseoutbreak_filename, short_code_2])

            run_specific_branch(
                local_properties_filename,
                local_diseaseoutbreak_filename,
                properties_filename,
                diseaseoutbreak_filename,
                folder_path_local,
                unique_output,
                management_parameters,
                days_to_run_for,
            )


# Step 8: give options regarding movement radius, ring culling, ring testing, and ring *vaccination* run until the invasion dies out (hopefully)
# days_to_run_for = 28
days_to_run_for = 120


outbreak_step_8_filenames = []
for properties_filename, diseaseoutbreak_filename, identifier in outbreak_step_7_filenames:
    long_name = ""
    short_code = identifier
    for new_movement_option in [
        "standstill",
        "restriction50km",
    ]:  # , "restriction25km"]: # taking out 25km to reduce decision space
        short_code_1 = short_code
        long_name_1 = new_movement_option
        if new_movement_option == "standstill":
            management_parameters = [{"type": "movement_standstill"}]
            short_code_1 += "-06A"
        elif new_movement_option == "restriction50km":
            management_parameters = [{"type": "movement_restriction", "radius_km": 50, "convex": False}]
            short_code_1 += "-06B"
        elif new_movement_option == "restriction25km":
            management_parameters = [{"type": "movement_restriction", "radius_km": 25, "convex": False}]
            short_code_1 += "-06C"

        # should also include the option of NOT doing anything more
        for ring_management_option, management_identifier in [
            # ["", "_only"],
            # ["ring culling", "cull25km"],
            ["ring testing", "test50km"],
            ["ring vaccination", "vaccinate50km"],  # 50km, to vaccinate ahead of the front?
        ]:
            long_name_2 = long_name_1 + management_identifier
            short_code_2 = short_code_1
            if ring_management_option == "":
                short_code_2 += "A"
            elif ring_management_option == "ring culling":
                management_parameters.append({"type": "ring_culling", "radius_km": 25, "convex": False})
                short_code_2 += "B"
            elif ring_management_option == "ring testing":
                management_parameters.append({"type": "ring_testing", "radius_km": 50, "convex": False})
                short_code_2 += "C"
            elif ring_management_option == "ring vaccination":
                management_parameters.append({"type": "ring_vaccination", "radius_km": 50, "convex": False})
                short_code_2 += "D"
            else:
                raise ValueError("Ring management option not identified")

            unique_output = short_code_2 + "_" + long_name_2
            folder_path_local = os.path.join(folder_path_main, unique_output)
            if not os.path.exists(folder_path_local):
                os.makedirs(folder_path_local)
            local_properties_filename = os.path.join(folder_path_local, "properties_" + unique_output)
            local_diseaseoutbreak_filename = os.path.join(folder_path_local, "outbreakobject_" + unique_output)

            outbreak_step_8_filenames.append([local_properties_filename, local_diseaseoutbreak_filename, short_code_2])

            run_specific_branch(
                local_properties_filename,
                local_diseaseoutbreak_filename,
                properties_filename,
                diseaseoutbreak_filename,
                folder_path_local,
                unique_output,
                management_parameters,
                days_to_run_for,
            )

exit(1)
