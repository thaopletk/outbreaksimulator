import sys
import os
import random

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from shapely.geometry import Point
import csv
import math
import pickle
import matplotlib.pyplot as plt
import simulator.spatial_setup as spatial_setup
import simulator.management as management
import simulator.premises as premises
import simulator.SEIR as SEIR
import simulator.output as output
import simulator.fixed_spatial_setup as fixed_spatial_setup
import simulator.animal_movement as animal_movement
from iteround import saferound
from shapely.ops import transform, unary_union
from simulator.spatial_functions import quick_distance_haversine
import time


def seed_HPAI_infection(
    xrange_bounds,
    yrange_bounds,
    properties,
    time=0,
    xlims=[],
    ylims=[],
    folder_path="",
    unique_output="",
    latent_period=7,
    disease_parameters=None,
):
    """Seeds an infection at a property within the bounds specified"""
    seed_property = 0  # default

    viable_properties = []
    for i, property in enumerate(properties):
        coords = property.coordinates
        if (
            coords[0] <= xrange_bounds[1]
            and coords[0] >= xrange_bounds[0]
            and coords[1] <= yrange_bounds[1]
            and coords[1] >= yrange_bounds[0]
        ):
            viable_properties.append(i)

    # seed this property
    # randomly pick a property to see:
    seed_property = random.choice(viable_properties)

    p = properties[seed_property]
    # TODO technically, to encapsulate this better, there should a function that allows you to infect a specific animal(s), and that will then update infection_status, prop_infections, cumulative_infections, and exposure_date, and anything else that may need to be updated
    p.infection_status = 1
    if latent_period != None:
        p.exposure_date = premises.convert_time_to_date(time - latent_period)
    else:  # the version with multiple animals
        latent_period = disease_parameters[p.animal_type]["latent_period"]
        p.exposure_date = premises.convert_time_to_date(time - latent_period)

    num_infected = 10
    # TODO: need to update some status/check the status update; need to convert the chicken arrays into objects
    for seed_animal in range(num_infected):
        p.animals[seed_animal].status = "infected"

    p.prop_infectious = num_infected / p.size
    p.cumulative_infections = num_infected

    output.plot_map(
        properties,
        time,
        xlims=xlims,
        ylims=ylims,
        folder_path=folder_path,
        real_situation=True,
        controlzone=None,
        infectionpoly=None,
        contacts_for_plotting={},  # contacts_for_plotting,  # hiding the contacts for plotting, to make things look clearer,,,, TODO in the real situation, these should be the actual movements, or something
    )

    fixed_spatial_setup.save_chicken_property_csv(properties, time, folder_path, unique_output)

    return properties, seed_property
