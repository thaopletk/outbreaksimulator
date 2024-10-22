# to be possibly converted into a test

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import datetime
import json
import pickle
import numpy as np
import simulator.simulator as simulator
import simulator.output as output
import simulator.SEIR as SEIR

xrange = [150, 151]
yrange = [-30, -29]

set_up_params = {
    "n": 10,  # total number of properties to include
    "r": 25,  # note that this should be in KILOMETERS, the maximum wind dispersal distance
    "xrange": xrange,
    "yrange": yrange,
    "average_property_ha": 500,
}


folder_path_main = os.path.join(os.path.dirname(__file__), "outputs", "temp")
if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)

property_setup_info = simulator.property_setup(
    folder_path_main,
    set_up_params["n"],
    set_up_params["r"],
    set_up_params["average_property_ha"],
    set_up_params["xrange"],
    set_up_params["yrange"],
)

properties = property_setup_info[0]
property_coordinates = property_setup_info[1]

init_vax_probability = 0.5
vax_modifier = 0.5
r_wind = set_up_params["r"]
beta_wind = 0.01
beta_animal = 2

time = 0


# limits for the figures
xlims = [round(xrange[0], 2) - 0.005, round(xrange[1], 2) + 0.005]
ylims = [round(yrange[0], 1) - 0.05, round(yrange[1], 1) + 0.05]

# seed infection (in the center third)
properties, seed_property = simulator.seed_infection(xrange, yrange, properties)

# initialise list of cumulative infections from each property - calculated for FOI every loop
cumulative_infection_proportions = list(np.zeros(set_up_params["n"]))
cumulative_infection_proportions[seed_property] = (
    properties[seed_property].cumulative_infections / properties[seed_property].size
)

# set up some random initial vaccination
for i, premise in enumerate(properties):
    if premise.infection_status != 1:
        premise.vaccination(
            init_vax_probability, properties, time, culled_neighbours_only=False
        )

output.plot_map(
    properties,
    property_coordinates,
    time,
    xlims=xlims,
    ylims=ylims,
    folder_path=folder_path_main,
)

# spread begins here:

FOI = list(np.zeros(set_up_params["n"]))

infected_properties = 1  # so the while loop begins

time += 1

controlzone = None

infected_properties = 0
for i, premise in enumerate(properties):
    if not premise.culled_status:
        FOI[i] = SEIR.calculate_force_of_infection(
            properties, i, vax_modifier, r_wind, beta_wind, beta_animal
        )

print(FOI)
