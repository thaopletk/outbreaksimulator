from collections import namedtuple
import numpy as np 
from scipy.integrate import odeint 
import matplotlib.pyplot as plt
import random as rand
from scipy.stats import hypergeom
from tqdm import tqdm 
import csv
import pandas as pd
from IPython import display
import time
from pathlib import Path
from moviepy.editor import ImageSequenceClip
import os
from matplotlib.patches import Circle
from shapely.geometry import Point
from shapely.geometry import Polygon
import math

from generate_property_grid import generate_properties
from class_definitions import Property 
from class_definitions import Animal 
from FOI_calculation_fns import calculate_FOI 
from plotting_code import plot_graph 
from plotting_code import make_video
from animal_movement_code import animal_movement 


def ABM(params, plotting, grid_size,property_radius):
    # outputs of interest - how many properties were culled and how many were vaccinated
    # i.e. how many reported, how many vaccinated and how widespread was the outbreak
    total_culled = 0
    total_vaccinated = 0

    # generate property grid
    property_coordinates, adjacency_matrix, neighbour_pairs, neighbourhoods = generate_properties(params['n'], params['r'], grid_size, property_radius)
    
    # initialise properties 
    properties = []
    for i in range(params['n']):
        properties.append(Property(params))
        properties[i].init_animals(params)
        properties[i].coordinates = property_coordinates[i]
        properties[i].radius = property_radius[i]
        properties[i].area = np.pi*(property_radius[i]**2)
        properties[i].neighbourhood = neighbourhoods[i]
        properties[i].total_neighbours = len(properties[i].neighbourhood)

    # seed infection
    # property coordinates allocated at random, so we always the first property in each simulation 
    seed_property = 0
    seed_animal = 0
    properties[seed_property].infection_status = 1
    properties[seed_property].animals[seed_animal].status = 'infected'
    properties[seed_property].number_infected = 1
    properties[seed_property].prop_infectious = 1/params['size']
    properties[seed_property].cumulative_infections = 1
    infected_sum = 1

    # initialise list of cumulative infections from each property - calculated for FOI every loop
    cumulative_infection_proportions = list(np.zeros(params['n']))
    cumulative_infection_proportions[seed_property] = properties[seed_property].cumulative_infections/len(properties[seed_property].animals)

    # initialise FOI - calculated every loop
    FOI = list(np.zeros(params['n']))
    
    # things for single simulation plotting
    # plot_graph(properties, property_coordinates, time)
    plotting_list = []
    plt.figure()

    time = 0
    # start time loop
    while infected_sum > 0:
        time += 1
        plotting_list.append([])
        # recalculated at the end of the time step
        infected_properties = 0

        # calculate FOI for each property
        for i, premise in enumerate(properties):
            if not premise.culled_status:
                FOI[i] = calculate_FOI(properties, i, params)
                # FOI[i] = calculate_FOI(premise, params, cumulative_infection_proportions)

        for premise in properties: 
            if not premise.culled_status and not premise.infection_status:
                premise.vaccination(params, properties)

        for premise in properties: 
            if not premise.culled_status: 
                premise.reporting(params)

        for i, premise in enumerate(properties):
            premise.infection_model(params, FOI[i])
        
        # movement of animals
        animal_movement(properties, params, time)
        
        # update counts 
        # simulation ends when infected_sum = 0
        infected_sum = 0
        for i, premise in enumerate(properties):
            premise.update_counts()
            if not premise.culled_status:
                cumulative_infection_proportions[i] = premise.cumulative_infections/len(premise.animals)
                infected_sum += premise.number_infected
        
        

        

        # # run infection model for each property
        # for i, premise in enumerate(properties): 
        #     # if the property has not been culled
        #     if not premise.culled_status:
        #         # run infection model and update infection numbers 
        #         premise.infection_model(params, FOI[i])
        #         cumulative_infection_proportions[i] = premise.cumulative_infections/len(premise.animals)

        #         # does the property vaccinate?
        #         # property can only vaccinate if they are not infected already
        #         if not premise.infection_status:
        #             premise.vaccination(params, properties)

        #         # does the property report?
        #         # property can only report if they are infected and have not been culled yet
        #         else:
        #             premise.reporting(params)
        #             # counting infected properties while we're considering infected properties
        #             infected_properties += 1

        #     # if property has been culled
        #     else: 
        #         # keeping track of infected_proportions for all properties
        #         cumulative_infection_proportions[i] = 0

        # infected_sum = 0
        # for i, premise in enumerate(properties):
        #     premise.update_counts()
        #     infected_sum += premise.number_infected
        
        # # movement of animals
        # animal_movement(properties, params, time)

        if plotting:
            plot_graph(properties, property_coordinates, time)
    
    if plotting:
        make_video()

    # statistics from end of simulation
    for premise in properties:
        if premise.culled_status:
            total_culled += 1
        if premise.vaccination_status:
            total_vaccinated += 1
        
    return total_culled, total_vaccinated