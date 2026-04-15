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
# import seaborn as sns

# wind dispersal
def create_circle(centre, radius):
    # create circle of radius centred at centre
    return Point(centre[0], centre[1]).buffer(radius)

def property_intersection(circle1, circle2):
    intersection = circle1.intersection(circle2)
    intersection_area = intersection.area
    
    return intersection_area

def create_unsafe_disc(premise, radius):
    centre = premise.coordinates
    unsafe_disc = create_circle(centre, radius)
    area = unsafe_disc.area 

    return unsafe_disc, area

def wind_dispersal_FOI(properties, premise_index, params):
    FOI = 0
    
    # contribution from property i
    C_i = properties[premise_index].cumulative_infections
    A_i = properties[premise_index].area
    
    # area of safe radius disc
    unsafe_disc_i, A_is = create_unsafe_disc(properties[premise_index], params['r'])

    FOI += params['beta_wind']* C_i * A_i / A_is

    circle_i = create_circle(properties[premise_index].coordinates, properties[premise_index].radius)
    # contributions from neighbouring properties 
    for [index, dist_border, dist_centres] in properties[premise_index].neighbourhood:
        C_j = properties[index].cumulative_infections
        
        # calculating area overlap 
        unsafe_disc_j, A_js = create_unsafe_disc(properties[index], params['r'])
        A_ijs = property_intersection(unsafe_disc_j, circle_i)

        # calculating min distance centre j to boundary of i
        d_ij = dist_centres - properties[premise_index].radius
        distance_modifier = 1 - (d_ij / params['r'])

        # update FOI
        FOI += params['beta_wind'] * C_j * distance_modifier * A_ijs / A_js

    return FOI

# animal to animal 
def animal_FOI(premise, params):
    FOI = params['beta_animal'] * premise.prop_infectious
    return FOI

# total FOI
def calculate_FOI(properties, premise_index, params): 

    # FOI = FOI_animal-to-animal + FOI_wind-dispersal
    
    # vaccination modifier
    # vax_status = 1 if no vaccination
    #            = params['vax_modifier'] if vaccination
    vax_status = (params['vax_modifier'] - 1)*properties[premise_index].vaccination_status + 1

    FOI_wind = wind_dispersal_FOI(properties, premise_index, params)
    FOI_animal = animal_FOI(properties[premise_index], params)

    FOI = vax_status * (FOI_animal + FOI_wind)

    return FOI 