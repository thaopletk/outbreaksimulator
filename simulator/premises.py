""" Premises class definition 

    The premises class describes farms (or other properties), with attributes such as location and size

    Expands upon the Property class from FMD_Modelling

"""

import sys
import os
import numpy as np
from geopy.geocoders import Nominatim

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from FMD_modelling.class_definitions import Property, Animal
import datetime
import itertools
from simulator.spatial_functions import calculate_area


def convert_time_to_date(
    time, start_date=datetime.datetime(year=2024, month=11, day=1)
):
    """Converts outbreak days (0, 1, 2...) to fake dates, started at some specified date (day 0).
    Parameters
    ----------
    time : int
        Simulation day to convert
    start_date : datetime.datetime objective
        Date time object describing "day 0".

    Returns
    -------
    date : string
        Formatted string d/m/Y representing the physical date
    """
    current_date = start_date + datetime.timedelta(days=time)
    return current_date.strftime("%d/%m/%Y")


# for now, we need additional parameters, hence inheriting from the fmdmodelling code
class Premises(Property):
    """
    A class used to represent premises/properties in the model

    Since we need additional parameters, this class inherits the Property class from the fmdmodelling code (class_definitions.py)

    Attributes
    ----------
    (so many attributes... - TODO)


    Methods
    ----------
    (so many methods - TODO)

    """

    id_iter = itertools.count()
    notified_iter = itertools.count(
        start=1
    )  # IP (infected properties) should start from 1
    geolocator = Nominatim(user_agent="http")

    # area in hectares
    def __init__(
        self,
        num_animals=0,
        movement_freq=1,
        coordinates=[0, 0],
        area_ha=500,
        neighbourhood=None,
        property_polygon=None,
        property_polygon_puffed=None,
        property_type="NA",
        movement_probability=0,
        movement_prop_animals=0,
        extra_capacity_multiplier=1,
        allowed_movement=["farm"],
        max_daily_movements=1,
    ):

        # currently, the class only requires these two parameters to initialise
        super().__init__({"size": num_animals, "movement_frequency": movement_freq})

        # but we will initialise more, now, rather than doing it in the loop

        self.coordinates = coordinates
        self.radius = None  # not applicable, as we don't have radial properties
        self.area = area_ha
        self.neighbourhood = neighbourhood
        self.total_neighbours = len(neighbourhood)

        # unique to this class
        self.reported_status = False
        self.culled_on_suspicion = False
        self.polygon = property_polygon
        self.puffed_poly = property_polygon_puffed
        self.puffed_poly_area = calculate_area(property_polygon_puffed)

        # things required for output, for input into the downstream model
        self.id = next(Premises.id_iter)
        self.status = "NA"
        self.ip = "NA"
        self.exposure_date = "NA"
        self.clinical_date = "NA"
        self.notification_date = "NA"
        self.removal_date = "NA"
        self.recovery_date = "NA"
        self.vacc_date = "NA"
        self.region = "NA"
        self.county = "NA"
        self.cluster = "NA"
        self.type = property_type

        # for movement
        self.movement_probability = movement_probability
        self.movement_prop_animals = movement_prop_animals
        self.extra_capacity_multiplier = extra_capacity_multiplier
        self.movement_frequency = movement_freq

        self.capacity = num_animals * extra_capacity_multiplier

        self.allowed_movement = allowed_movement
        self.max_daily_movements = max_daily_movements

    #
    def vaccinate(self, time):
        self.vaccination_status = 1
        self.vacc_date = convert_time_to_date(time)

        return 0

    def vaccination(
        self, prob_vaccinate, properties, time, culled_neighbours_only=True
    ):
        """Decide whether or not to vaccinate

        Since we will allow properties to vaccination *without* needing culled neighbours, this code has been adapted from the original definition

        Should first check whether or not it's already culled
        """

        if culled_neighbours_only:
            prop_culled_neighbours = 0
            if len(self.neighbourhood):  # premise has neighbours
                neighbours = [el[0] for el in self.neighbourhood]
                culled_neighbours = sum(
                    [properties[i].culled_status for i in neighbours]
                )
                prop_culled_neighbours = culled_neighbours / self.total_neighbours

            # vaccination
            if prop_culled_neighbours:  # if there are culled neighbours
                vaccinate_rand = np.random.rand()
                if vaccinate_rand < prob_vaccinate * prop_culled_neighbours:
                    self.vaccinate(time)
        else:
            vaccinate_rand = np.random.rand()
            if vaccinate_rand < prob_vaccinate:
                self.vaccinate(time)
        return

    def cull_without_reporting(self, time):
        """Cull without reporting - useful for ring culling"""
        self.infection_status = 0
        self.culled_status = 1
        # all animals culled
        self.animals = []

        report = ""
        # no notification date
        self.removal_date = convert_time_to_date(time)
        # no change in "IP" status
        # self.reported_status = False # no change
        self.culled_on_suspicion = True
        x, y = self.coordinates

        location = self.geolocator.reverse(f"{y},{x}")
        report = f"DAY {self.removal_date} - Property ID {self.id}, {round(self.area,1)} ha cattle property at location (x,y)=({round(x,2)}, {round(y,2)}), {location}, is within the ring culling zone.\nA total of {self.size} animal(s) have been culled.\n"

        return report, self.size

    def reporting(
        self, clinical_reporting_threshold, prob_report, time, force_report=False
    ):
        if not force_report:
            super().reporting(
                {
                    "clinical_reporting_threshold": clinical_reporting_threshold,
                    "prob_report": prob_report,
                }
            )
        else:
            self.infection_status = 0
            self.culled_status = 1
            # all animals culled
            self.animals = []

        report = ""
        culled_animals = 0
        if self.culled_status == 1:
            culled_animals = self.size
            self.notification_date = convert_time_to_date(time)
            self.status = "IP"
            self.ip = next(Premises.notified_iter)
            self.reported_status = True
            x, y = self.coordinates

            location = self.geolocator.reverse(f"{y},{x}")
            report = f"DAY {self.notification_date} - IP {self.ip} (ID {self.id}), {round(self.area,1)} ha cattle property at location (x,y)=({round(x,2)}, {round(y,2)}), {location}, has been reported infected.\nA total of {culled_animals} animal(s) have been culled.\n"

        return report, culled_animals

    def infection_model(
        self, latent_period, infectious_period, preclinical_period, FOI, time
    ):
        super().infection_model(
            {
                "latent_period": latent_period,
                "infectious_period": infectious_period,
                "pre-clinical_period": preclinical_period,
            },
            FOI,
        )

        if self.infection_status == 1 and self.clinical_date == "NA":
            self.clinical_date = convert_time_to_date(
                time
            )  # might need to change this, but for now, it should be the earliest date with clinical symptoms

    def return_output_row(self):
        """Returns a row with information for outputing (required downstream for forecasting)

        Returns
        -------
        list
            a list containing the following information in order:
            id, status, ip, exposure_date, clinical_date, notification_date, removal_date, recovery_date, vacc_date, region, county, cluster, xcoord, ycoord, area, type, total

        """

        return [
            self.id,
            self.status,
            self.ip,
            self.exposure_date,
            self.clinical_date,
            self.notification_date,
            self.removal_date,
            self.recovery_date,
            self.vacc_date,
            self.region,
            self.county,
            self.cluster,
            self.coordinates[0],
            self.coordinates[1],
            self.area,
            self.type,
            self.size,
        ]

    def return_known_output_row(self):
        """Returns a row with *known* information for outputing (required downstream for forecasting)

        I.e., by "known", I mean that if an infected property hasn't notified yet, then there shouldn't be anything printed there regarding clinical dates

        Returns
        -------
        list
            a list containing the following information in order:
            id, status, ip, exposure_date, clinical_date, notification_date, removal_date, recovery_date, vacc_date, region, county, cluster, xcoord, ycoord, area, type, total

        """

        if (
            self.reported_status
        ):  # if reported already, then all information can be provided
            return self.return_output_row()
        if (
            self.culled_on_suspicion
        ):  # if culled on suspicion, then exposure, clinical, notification dates should be NA
            return [
                self.id,
                self.status,
                self.ip,
                "NA",  # self.exposure_date,
                "NA",  # self.clinical_date,
                self.notification_date,  # this should already be "NA"
                self.removal_date,  # this shouldn't be NA, since this is a property that has been culled
                self.recovery_date,
                self.vacc_date,
                self.region,
                self.county,
                self.cluster,
                self.coordinates[0],
                self.coordinates[1],
                self.area,
                self.type,
                self.size,
            ]
        else:
            return [
                self.id,
                self.status,
                self.ip,
                "NA",  # self.exposure_date,
                "NA",  # self.clinical_date,
                self.notification_date,  # this should already be "NA"
                self.removal_date,  # this should already be "NA"
                self.recovery_date,
                self.vacc_date,
                self.region,
                self.county,
                self.cluster,
                self.coordinates[0],
                self.coordinates[1],
                self.area,
                self.type,
                self.size,
            ]
