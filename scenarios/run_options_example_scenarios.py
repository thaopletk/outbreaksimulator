# to be possibly converted into a test

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import datetime
import json
import pickle

import simulator.simulator as simulator


xrange = [150, 151]
yrange = [-30, -29]

set_up_params = {
    "n": 50,  # total number of properties to include
    "r_wind": 25,  # note that this should be in KILOMETERS, the maximum wind dispersal distance
    "xrange": xrange,
    "yrange": yrange,
    "average_property_ha": 500,  # TODO this isn't exactly the average property size...but it *is* related to it. There may be a minimum size to this...
    "average_animals_per_ha": 0.2,
    "movement_frequency": 3,
}


params_low_incubation = {
    "init_vax_probability": 0,
    "stop_time": 14,
    "vax_modifier": 0.4,
    "beta_wind": 2,
    "beta_animal": 4,
    "latent_period": 2,
    "infectious_period": 1,
    "preclinical_period": 2,
    "prob_vaccinate": 0.5,
    "clinical_reporting_threshold": 0.05,
    "prob_report": 0.7,
    "movement_probability": 0.4,
    "movement_prop_animals": 0.2,
    "test_sensitivity": 0.9,
}
disease = "example"

params = {**set_up_params, **params_low_incubation}


folder_path_main = os.path.join(
    os.path.dirname(__file__), "outputs", "October_2024_options", "example_scenarios"
)
if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)

for (
    movement_restrictions,
    movement_restriction_radius_km,
    movement_restriction_convex,
) in [[False, None, None], [True, 10, False][True, 10, True]]:

    # check if there already exists a properties_initialised.pickle in the folder, and if so, load that instead of re-running property set_up
    # TODO - would be to also save the setup params, and check that the saved setup params match the ones above
    properties_initialised = os.path.join(
        folder_path_main, "properties_initialised.pickle"
    )
    if os.path.exists(properties_initialised):
        with open(properties_initialised, "rb") as file:
            property_setup_info = pickle.load(file)
    else:
        property_setup_info = simulator.property_setup(
            folder_path_main, **set_up_params
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

    plotting = True
    unique_output = f'{disease}_{datetime.datetime.now().strftime("%Y-%m-%d %H.%M.%S")}'
    # make a new folder
    folder_path = os.path.join(folder_path_main, unique_output)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    file = os.path.join(folder_path, "params.json")
    with open(file, "w") as f:
        json.dump(params, f)

    simulator.simulate_outbreak(
        plotting=plotting,
        folder_path=folder_path,
        properties=properties,
        property_coordinates=property_coordinates,
        unique_output=unique_output,
        movement_restrictions=movement_restrictions,
        movement_restriction_radius_km=movement_restriction_radius_km,
        movement_restriction_convex=movement_restriction_convex,
        **params,
    )
