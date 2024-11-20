"""Disease Simulator

    Creates a DiseaseSimulator object to run spread simulation

    Typical workflow involves calling:
    * init
    * set_plotting_parameters
    * simulator function of choice...

"""

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
import simulator.animal_movement as animal_movement
from iteround import saferound
from shapely.ops import transform, unary_union
from simulator.spatial_functions import quick_distance_haversine
import simulator.simulator as simulator


class DiseaseSimulation:
    """A class to represent the disease parameters and disease simulation scenario"""

    def __init__(
        self,
        time=0,
        movement_records=[],
        disease_parameters={
            "beta_wind": 0.05,
            "beta_animal": 0.9,
            "latent_period": 7,
            "infectious_period": 23.1,
            "preclinical_period": 7,
        },
        spatial_only_parameters={
            "n": 50,
            "r_wind": 25,
            "xrange": [150.2503, 151.39695],
            "yrange": [-32.61181, -31.60829],
            "average_property_ha": 300,
        },
        job_parameters={
            "lab_test_sensitivity": 0.9,
            "clinical_test_sensitivity": 0.5,
            "cull_delay": 1,
            "contact_tracing_delay": 0.5,
            "lab_test_delay": 1.5,
            "clinical_delay": 0.5,
        },
    ):

        self.time = time

        self.movement_records = movement_records
        self.beta_wind = disease_parameters["beta_wind"]
        self.beta_animal = disease_parameters["beta_animal"]
        self.latent_period = disease_parameters["latent_period"]
        self.infectious_period = disease_parameters["infectious_period"]
        self.preclinical_period = disease_parameters["preclinical_period"]

        self.r_wind = spatial_only_parameters["r_wind"]

        self.vax_modifier = 0  # TODO - can set up a function to input in vaccination-relevant parameters

        # TODO : to add in reports as something that can be instantiated here

        # default set for plotting limits
        # limits for the figures
        self.xlims = [
            round(spatial_only_parameters["xrange"][0], 2) - 0.005,
            round(spatial_only_parameters["xrange"][1], 2) + 0.005,
        ]
        self.ylims = [
            round(spatial_only_parameters["yrange"][0], 1) - 0.05,
            round(spatial_only_parameters["yrange"][1], 1) + 0.05,
        ]
        self.plotting = True
        self.folder_path = ""
        self.unique_output = ""

        self.job_manager = management.JobManager(**job_parameters)

    def set_plotting_parameters(self, xlims, ylims, plotting=True, folder_path="", unique_output=""):
        self.xlims = xlims
        self.ylims = ylims
        self.plotting = plotting
        self.folder_path = folder_path
        self.unique_output = unique_output

    def simulate_outbreak_spread_only(self, properties, time=None, stop_time=7):
        """Run simulated outbreak, for undetected spread between (self.time (or time parameter if not NA)+1) and (stop_time) [inclusive], with no management"""

        if time != None:
            self.time = time

        if self.folder_path == "":
            raise Warning("Default folder path hasn't changed - recommend that set_plotting_parameters() be run first")

        controlzone = {}  # empty control zone
        contacts_for_plotting = {}  # empty, as no contact tracing will occur here

        FOI = list(np.zeros(len(properties)))
        while self.time < stop_time:
            self.time += 1
            # calculate FOI for each property
            for i, property_i in enumerate(properties):
                if not property_i.culled_status:
                    FOI[i] = SEIR.calculate_force_of_infection(
                        properties, i, self.vax_modifier, self.r_wind, self.beta_wind, self.beta_animal
                    )

            # run infection model for each property
            for i, property_i in enumerate(properties):
                property_i.infection_model(
                    self.latent_period, self.infectious_period, self.preclinical_period, FOI[i], self.time
                )

            # movement of animals
            controlzone_movement_restrictions = None

            movement_record = animal_movement.trialsimex_animal_movement(
                properties, day=self.time, controlzone=controlzone_movement_restrictions
            )
            if movement_record != []:
                self.movement_records.extend(movement_record)

            # update counts
            for i, premise in enumerate(properties):
                premise.update_counts()

            if self.plotting:
                simulator.plot_current_state(
                    properties,
                    self.time,
                    self.xlims,
                    self.ylims,
                    self.folder_path,
                    controlzone,
                    infectionpoly=False,
                    contacts_for_plotting=contacts_for_plotting,
                )
                # should also save things for plotting: i.e., everything that I had used to actually plot
                with open(os.path.join(self.folder_path, "plotting_data" + str(self.time)), "wb") as file:
                    pickle.dump(
                        [properties, self.time, self.xlims, self.ylims, controlzone, contacts_for_plotting], file
                    )

        if self.plotting:
            output.make_video(self.folder_path, "map_underlying")
            output.make_video(self.folder_path, "map_apparent")

        simulator.save_outbreak_state(
            properties,
            self.time,
            self.folder_path,
            self.unique_output,
            total_culled_animals=0,
            movement_records=self.movement_records,
            job_manager=self.job_manager,
        )

        simulator.save_movement_record(self.folder_path, self.movement_records)

        return properties, self.movement_records, self.time

    def simulate_outbreak_til_first_report(self, properties, time=None):
        """Run simulated outbreak, for spread starting from self.time+1 til the first report (end of the first day), with localised actions but no ring management"""

        if time != None:
            self.time = time

        if self.folder_path == "":
            raise Warning("Default folder path hasn't changed - recommend that set_plotting_parameters() be run first")
        if self.job_manager == None:
            raise ValueError("Job manager needs to be set")

        total_culled_animals = 0
        local_movement_restrictions = []
        controlzone = {}
        contacts_for_plotting = {}

        return total_culled_animals, local_movement_restrictions
