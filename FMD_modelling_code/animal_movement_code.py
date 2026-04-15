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

def animal_movement(properties, params, day):
    added_animals = []

    # take animals out first, then add them to other properties later (so animals don't move twice in one day)
    for premise_index in range(len(properties)):

        # if it's a movement day for this property 
        if not ((day - properties[premise_index].movement_start_day)%params['movement_frequency']):
            
            # if the property hasn't been culled
            if not properties[premise_index].culled_status:

                # if there is movement
                prob_movement = np.random.rand()
                if prob_movement < params['movement_probability']:
                    
                    # where can the animals moving to 
                    moving_to_premise_indices = []
                    for i in range(params['n']):
                        if not properties[i].culled_status and i != premise_index: #property hasn't been culled and isn't the moving from property
                            moving_to_premise_indices.append(i)
                    
                    # if there's somewhere to move the animals
                    if moving_to_premise_indices:
                        
                        # how many animals moving 
                        property_size = len(properties[premise_index].animals)
                        number_animals = int(np.floor(params['movement_prop_animals']*property_size))
                    
                        # choose random premise to move to 
                        moving_to_premise_index = np.random.choice(moving_to_premise_indices)
                        
                        # keeping track of moving the animals
                        moving_animal_list = []
                        for _ in range(int(number_animals)):
                            moving_animal_index = np.random.randint(0, len(properties[premise_index].animals))
                            moving_animal = properties[premise_index].animals.pop(moving_animal_index)
                            moving_animal_list.append(moving_animal)
                    
                        added_animals.append([moving_animal_list, moving_to_premise_index])
        
    # move animals to properties 
    if added_animals: #as long as there are animals to move
        for moving_list, moving_index in added_animals: 
            for moving_animal in moving_list: 
                properties[moving_index].animals.append(moving_animal)


    return 
