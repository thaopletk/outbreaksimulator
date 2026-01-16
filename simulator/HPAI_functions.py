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
        ) and property.type not in ["egg processing", "abbatoir"]:
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
    # TODO: need to update some status/check the status update;
    p.init_animals(None)
    infected_row = np.random.randint(0, len(p.chickens))  # this picks a random age
    for seed_animal in range(num_infected):
        p.chickens[infected_row][3][seed_animal].status = "infected"

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


def advance_chicken_egg_ages(properties):
    """increases the age of all the chickens and eggs by one day"""
    for facility in properties:
        for i in range(len(facility.chickens)):
            facility.chickens[i][2] += 1  # the third index is the age, by day
        for i in range(len(facility.eggs)):
            facility.eggs[i][1] += 1  # the second index is the age, by day
        for i in range(len(facility.eggs_fertilised)):
            facility.eggs_fertilised[i][1] += 1  # the second index is the age, by day


def egg_production(properties):
    """implements production of eggs..."""
    for facility in properties:
        if "layers" in facility.type:
            total_laying_chickens = 0
            for row in facility.chickens:
                if row[2] > 20 * 7 and row[2] < 78 * 7:  # i.e., if age is greater than 20 weeks
                    total_laying_chickens += row[0]  # the number of chickens
            facility.eggs.append(
                [int(total_laying_chickens / 2), 0]
            )  # assume half of the chickens lay eggs; age of eggs is zero
        elif facility.type == "meat growing-farm":
            pass  # no egg production
        elif facility.type == "pullets farm":
            pass  # no egg production
        elif facility.type == "egg processing":
            pass  # no egg production
        elif facility.type == "abbatoir":
            pass  # no egg production
        elif facility.type == "hatchery":
            total_laying_chickens = 0
            for row in facility.chickens:
                if row[2] > 20 * 7 and row[2] < 78 * 7:  # i.e., if age is greater than 20 weeks and less than 78
                    total_laying_chickens += row[0]  # the number of chickens
            facility.eggs_fertilised.append(
                [int(total_laying_chickens / 2), 0]
            )  # assume half of the chickens lay eggs; age of eggs is zero
            # NOTE I think the eggs should be hatched in pulses (.g. every 14 days) but for now, it'll be like this....
        else:
            raise ValueError(f"egg_production: property type not expected: {facility.type}")
