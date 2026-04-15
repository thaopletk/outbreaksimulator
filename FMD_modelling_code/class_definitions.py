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


class Property:
    def __init__(self, params):
        # property characteristics
        self.coordinates = []
        self.radius = 0
        self.area = 0
        self.neighbourhood = []
        self.total_neighbours = 0
        self.animals = []
        self.size = params['size']

        # infection characteristics
        # not-status = 0
        # status = 1
        self.infection_status = 0
        self.vaccination_status = 0
        self.culled_status = 0

        self.vaccinate_delay = 0 
        self.cull_delay = 0

        # self.prop_infected = 0
        self.prop_infectious = 0
        self.prop_clinical = 0
        self.cumulative_infections = 0
        self.number_infected = 0

        self.movement_start_day = np.random.randint(0, params['movement_frequency'])

        return 

    # initialise all animals on the property 
    def init_animals(self, params):
        for _ in range(self.size):
            self.animals.append(Animal(params))
        return 
    
    # update infection counts
    def update_counts(self):
        number_infected = 0
        number_infectious = 0
        number_clinical = 0
        if not self.culled_status:
            for cow in self.animals:
                # check how many animals are infected (infection status of property) and how many are infectious (FOI calculation)
                if cow.infection_status == 'exposed':
                    number_infected += 1
                elif cow.infection_status == 'infectious':
                    number_infected += 1
                    number_infectious += 1
                
                # check how many animals are showing clinical symptoms (reporting)
                if cow.clinical_status == 'clinical':
                    number_clinical += 1
                
            # record proportion of animals infectious and clinical for other calculations 
            self.prop_infectious = number_infectious / len(self.animals)
            self.prop_clinical = number_clinical / len(self.animals)

            # if there's any infection, property is labelled infected
            self.number_infected = number_infected
            if number_infected > 0:
                self.infection_status = 1
        return 

    # does the property vaccinate?
    def vaccination(self, params, properties):
        # We assume properties won't vaccinate if they don't have culled neighbours
        # calculate proportion of culled neighbours 
        prop_culled_neighbours = 0
        if len(self.neighbourhood): #premise has neighbours
            neighbours = [el[0] for el in self.neighbourhood]
            culled_neighbours = sum([properties[i].culled_status for i in neighbours])
            prop_culled_neighbours = culled_neighbours/self.total_neighbours 

        # vaccination 
        if prop_culled_neighbours: #if there are culled neighbours 
            vaccinate_rand = np.random.rand()
            if vaccinate_rand < params['prob_vaccinate']*prop_culled_neighbours:
                self.vaccination_status = 1
        return

    # does the property report infection?
    def reporting(self, params):
        # only report if proportion of clinical cases is above the clinical reporting threshold 
        if self.prop_clinical > params['clinical_reporting_threshold']:
            reporting_rand = np.random.rand()
            chance_of_reporting = params['prob_report']*self.prop_clinical

            # we assume once a property reports infection, they are immediately culled 
            if reporting_rand < chance_of_reporting:
                self.infection_status = 0
                self.culled_status = 1
                # all animals culled
                self.animals = []
                
        return

    # infection model for an individual property
    def infection_model(self, params, FOI):
        infected_cases = 0
        clinical_cases = 0
        infectious_cases = 0

        # infection model for each animals
        for cow in self.animals:
            animal_inf = cow.infection_event(params, FOI) 
            if animal_inf:
                self.cumulative_infections += 1
            cow.check_transition(params)
            cow.update_clock()
        return 
    


class Animal: 
    def __init__(self, params):
        # infection_status: 'susceptible', 'exposed', 'infectious', 'recovered', 'culled'
        # clinical_status: 'susceptible', 'pre-clinical', 'clinical', 'recovered', 'culled'
        self.infection_status = 'susceptible'
        self.clinical_status = 'susceptible'
        self.infection_clock = 0
        self.clinical_clock = 0

        return 


    def update_clock(self, dt = 1):
        # infection clock
        if self.infection_status == 'exposed' or self.infection_status == 'infectious':
            self.infection_clock += dt

        # clinical clock
        if self.clinical_status == 'pre-clinical' or self.infection_status == 'clinical':
            self.clinical_clock += dt
        return 
    

    def check_transition(self, params):
        # exposed -> infectious
        if self.infection_status == 'exposed' and self.infection_clock > params['latent_period']:
            self.infection_status = 'infectious'
        # infectious -> recovered
        elif self.infection_status == 'infectious' and self.infection_clock > params['latent_period'] + params['infectious_period']:
            self.infection_status = 'recovered'
        
        # pre-clinical -> clinical
        if self.clinical_status == 'pre-clinical' and self.clinical_clock > params['pre-clinical_period']:
            self.clinical_status = 'clinical'

        return 


    def infection_event(self, params, FOI):
        if self.infection_status == 'susceptible':
            infection_rand = np.random.rand()
            infection_prob = 1 - np.exp(-FOI)

            # if infection occurs
            if infection_rand < infection_prob:
                if params['latent_period'] != 0:
                    self.infection_status = 'exposed'
                else: 
                    self.infection_status = 'infectious'

                if params['pre-clinical_period'] != 0:
                    self.clinical_status = 'pre-clinical'
                else: 
                    self.clinical_status = 'clinical'
                # if infection event happens - return 1
                return 1
        # otherwise if no infection event - return 0
        return 0