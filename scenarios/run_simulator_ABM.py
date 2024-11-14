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
    "n": 30,  # total number of properties to include
    "r_wind": 25,  # note that this should be in KILOMETERS, the maximum wind dispersal distance
    "xrange": xrange,
    "yrange": yrange,
    "average_property_ha": 500,  # TODO this isn't exactly the average property size...but it *is* related to it. There may be a minimum size to this...
    "average_animals_per_ha": 0.2,
    "property_types": {
        "saleyard": 0.001,
        "trader": 0.007,
        "feedlot": 0.007,
        "abbattoir": 0.001,
        "farm": 1 - 0.001 - 0.007 - 0.007 - 0.001,
    },
    "movement_frequency": {
        "saleyard": 1,
        "trader": 1,
        "feedlot": 1,
        "abbattoir": 1,
        "farm": 3,
    },
    "movement_probability": {
        "saleyard": 1,
        "trader": 1,
        "feedlot": 0.2,
        "abbattoir": 0,
        "farm": 0.5,
    },
    "movement_prop_animals": {
        "saleyard": 0.2,
        "trader": 0.8,
        "feedlot": 0.1,
        "abbattoir": 0,
        "farm": 0.2,
    },
    "extra_capacity_multiplier": {
        "saleyard": 3,
        "trader": 3,
        "feedlot": 3,
        "abbattoir": 1000,
        "farm": 1,
    },
    "allowed_movement": {
        "saleyard": ["saleyard", "trader", "feedlot", "abbattoir", "farm"],
        "trader": ["saleyard", "trader", "feedlot", "abbattoir", "farm"],
        "feedlot": ["abbattoir"],
        "abbattoir": [],
        "farm": ["saleyard", "trader", "feedlot", "abbattoir", "farm"],
    },
    "max_daily_movements": {
        "saleyard": 6,
        "trader": 3,
        "feedlot": 2,
        "abbattoir": 0,
        "farm": 1,
    },
}
# will need to do something special with abbattoirs, e.g. they move things to an infinite sink...
# need to set up their capacity, their current number of animals, their unique movement frequency which would be a lot higher...


folder_path_main = os.path.join(os.path.dirname(__file__), "outputs", "temp")
if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)

property_setup_info = simulator.property_setup(folder_path_main, **set_up_params)

# TODO : should consider a namedtuple for unpacking...
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

params_low_incubation = {
    "init_vax_probability": 0,  # note that this should be zero
    "stop_time": 21,
    "vax_modifier": 1
    - 0.7,  # vax modifier appears to be what you multiply the FOI by...
    "beta_wind": 2,
    "beta_animal": 4,
    "latent_period": 2,
    "infectious_period": 1,
    "preclinical_period": 2,
    "prob_vaccinate": 0,  # zero, as people won't randomly vaccination
    "clinical_reporting_threshold": 0.05,
    "prob_report": 0.7,
    "lab_test_sensitivity": 0.9,
    "clinical_test_sensitivity": 0.5,
}
disease = "low_incubation"

params = {**set_up_params, **params_low_incubation}

plotting = True
unique_output = f'{disease}_{datetime.datetime.now().strftime("%Y-%m-%d %H.%M.%S")}'
# make a new folder
folder_path = os.path.join(folder_path_main, unique_output)
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

file = os.path.join(folder_path, "params.json")
with open(file, "w") as f:
    json.dump(params, f)


total_culled, total_vaccinated, properties = simulator.simulate_outbreak(
    plotting=plotting,
    folder_path=folder_path,
    properties=properties,
    property_coordinates=property_coordinates,
    unique_output=unique_output,
    movement_standstill=True,  # if this is true, then movement restrictions should be false
    # movement_restrictions=True,
    # movement_restriction_radius_km=10,
    # movement_restriction_convex=True,
    # ring_vaccination=True,
    # ring_vaccination_radius_km=20,
    # ring_vaccination_convex=True,
    # ring_culling=True,
    # ring_culling_radius_km=15,
    # ring_culling_convex=False,
    # ring_testing=True,
    # ring_testing_radius_km=15,
    # ring_testing_convex=True,
    **params,
)
