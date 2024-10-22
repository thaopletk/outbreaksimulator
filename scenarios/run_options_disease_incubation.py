# to be possibly converted into a test

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import datetime
import json
import pickle

import simulator.spatial_setup as spatial_setup
import simulator.output as output
import simulator.simulator as simulator


xrange = [150, 151]
yrange = [-30, -29]

folder_path_main = os.path.join(
    os.path.dirname(__file__), "outputs", "October_2024_options"
)
if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)

n = 500

set_up_params = {
    "n": n,  # total number of properties to include
    "r_wind": 25,  # note that this should be in KILOMETERS, the maximum wind dispersal distance
    "xrange": xrange,
    "yrange": yrange,
    "average_property_ha": 1000,
    "average_animals_per_ha": 0.2,
    "movement_frequency": 3,
}

# this process can take a long time...possibly due to all the polygons and checks
property_setup_info = simulator.property_setup(folder_path_main, **set_up_params)

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

params_all = {
    "init_vax_probability": 0,
    "stop_time": 30,
    "vax_modifier": 0.4,
    "beta_wind": 0.1,
    "beta_animal": 2,
    "prob_vaccinate": 0.5,
    "clinical_reporting_threshold": 0.05,
    "prob_report": 0.5,
    "movement_probability": 0.1,
    "movement_prop_animals": 0.2,
}

params_short_incubation = {
    "latent_period": 2,
    "infectious_period": 2,
    "preclinical_period": 2,
}

params_long_incubation = {
    "latent_period": 8,
    "infectious_period": 8,
    "preclinical_period": 8,
}

for disease, disease_params in [
    ["short_incubation", params_short_incubation],
    ["long_incubation", params_long_incubation],
]:
    # read in the property set up information (cleanly)
    with open(
        os.path.join(folder_path_main, "properties_initialised.pickle"), "rb"
    ) as file:
        property_setup_info = pickle.load(file)

    params = {**set_up_params, **params_all, **disease_params}

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
        **params,
    )
