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

import math


def rounding_entities(val):
    if val < 10:
        return val
    if val < 100:
        return math.floor(val / 5) * 5
    if val < 500:
        return math.floor(val / 50) * 50
    if val < 1000:
        return math.floor(val / 100) * 100
    if val < 10000:
        return math.floor(val / 1000) * 1000
    if val < 100000:
        return math.floor(val / 10000) * 10000
    return math.floor(val / 100000) * 100000


geolocator = Nominatim(user_agent="http")


def get_current_datetime(time, start_date=datetime.datetime(year=2026, month=1, day=1)):
    if type(time) != int:
        time = int(np.floor(time))
        # TODO : here, I should allow for "morning" vs "afternoon" or some other time thing
    current_date = start_date + datetime.timedelta(days=time)
    return current_date


def convert_time_to_date(time, start_date=datetime.datetime(year=2026, month=1, day=1), return_string="%d/%m/%Y"):
    """Converts outbreak days (0, 1, 2...) to fake dates, started at some specified date (day 0).
    Parameters
    ----------
    time : int
        Simulation day to convert
    start_date : datetime.datetime objective
        Date time object describing "day 0".
    return_string : str
        String for formatting date output
    Returns
    -------
    date : string
        Formatted string d/m/Y representing the physical date
    """
    if type(time) != int:
        time = int(np.floor(time))
        # TODO : here, I should allow for "morning" vs "afternoon" or some other time thing
    current_date = start_date + datetime.timedelta(days=time)
    return current_date.strftime(return_string)


def convert_date_to_time(date, start_date=datetime.datetime(year=2026, month=1, day=1)):
    d1 = datetime.datetime.strptime(date, "%d/%m/%Y")
    return abs((d1 - start_date).days)


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
    notified_iter = itertools.count(start=1)  # IP (infected properties) should start from 1
    # geolocator = Nominatim(user_agent="http")

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
        allowed_movement=["farm"],
        max_daily_movements=1,
        animal_type="cattle",
    ):

        # currently, the class only requires these two parameters to initialise
        super().__init__({"size": num_animals, "movement_frequency": movement_freq})

        self.animal_type = animal_type

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
        self.movement_frequency = movement_freq
        self.movement_neighbours = None

        self.allowed_movement = allowed_movement
        self.max_daily_movements = max_daily_movements
        self.allowed_movement_details = None

        self.x, self.y = self.coordinates

        self.location = geolocator.reverse(f"{self.y},{self.x}")
        self.address = self.location.raw["address"]
        self.state = self.address.get("state", "")
        if self.state == "":
            self.state = self.address.get("territory", "")

        self.undergoing_testing = False
        self.day_of_last_lab_test = None
        self.clinical_report_outcome = None  # otherwise, true or false

        # for chicken premises specific
        self.num_sheds = None
        self.chickens = None
        self.eggs = None
        self.eggs_fertilised = None
        self.chicken_capacity = self.size
        self.accepts_hatchlings = False  # whether they rear pullets or not
        self.approx_chickens_per_shed = None

        self.custom_info = (
            {}
        )  # setting up an empty dictionary to add in any custom info to be set live during the simulation

    def requesting_chickens(self):
        """generally superceeded by accepting_animals() function"""
        current_chickens = self.get_num_chickens()
        if self.chicken_capacity < current_chickens or np.abs((self.chicken_capacity - current_chickens) / 100) < 0.01:
            return 0
        else:
            return self.chicken_capacity - current_chickens

    def init_chickens_eggs(self):
        """Initiating things that are specific for chicken (meat and egg) premises
        Could turn this into a new class that inherits the premises class in the future
        """
        # num chickens: in self.size
        self.sheds = {}
        self.eggs = 0

        if "layers" in self.type:
            if self.type == "layers free-range":
                self.approx_chickens_per_shed = 10000  # for free range, the number should be less than other cases
            elif self.type == "layers caged":
                self.approx_chickens_per_shed = 14000  # going by 12k-14k of chickens per shed
            elif self.type == "layers barn":
                self.approx_chickens_per_shed = 12000  # going by 12k-14k of chickens per shed

            # all in / all out style
            # https://www.poultryhub.org/production/chicken-egg-layer-industry/layer-farm-sequence
            #  laying chickens, assume age is from 20 weeks to 78 weeks
            # assuming full capcity, running flow

            self.num_sheds = math.ceil(self.size / self.approx_chickens_per_shed)
            if self.num_sheds > 5:
                chickens_possible_week_ages = list(range(1, 78))  # lower age limit - rearing pullets
                self.accepts_hatchlings = True
                # TODO meaning they shouldn't accept birds from pullet farms, only hatched chicks?
            else:
                chickens_possible_week_ages = list(range(20, 78))

            actual_chickens_per_shed = int(self.size / self.num_sheds)
            total_chickens = 0
            total_laying_chickens = 0
            for shed_i in range(1, self.num_sheds + 1):
                week = np.random.choice(chickens_possible_week_ages)
                self.sheds[shed_i] = {
                    "chickens": [
                        {"n": actual_chickens_per_shed, "age": week * 7}
                    ],  # array format, to accept multiple-age chickens if necessary
                    "cleaning": False,
                    "cleaning_completion": None,
                }

                total_chickens += actual_chickens_per_shed

                if week >= 20:
                    total_laying_chickens += actual_chickens_per_shed

            self.size = total_chickens  # updating the number in case the division is imperfect

            # eggs: num eggs
            self.eggs = actual_chickens_per_shed * np.random.randint(
                0, self.num_sheds
            )  # age actually doesn't matter if they're not in a shed (yet)
            # and fertilised eggs can be moved into a shed

        elif self.type == "broiler farm":
            # broilers: 4-6 weeks of age https://kb.rspca.org.au/categories/farmed-animals/poultry/meat-chickens/how-are-meat-chickens-farmed-in-australia

            self.approx_chickens_per_shed = 12000  # going by 12k-14k of chickens per shed

            # NEW CHICKEN ALLOCATION - more akin to "all in / all out", with chickens of the same age in each shed
            self.num_sheds = math.ceil(self.size / self.approx_chickens_per_shed)
            chickens_possible_week_ages = list(
                range(1, 6 + 1)
            )  # lower age limit - all broiler farms to accept hatchlings directly
            self.accepts_hatchlings = True
            actual_chickens_per_shed = int(self.size / self.num_sheds)

            total_chickens = 0
            for shed_i in range(1, self.num_sheds + 1):
                week = np.random.choice(chickens_possible_week_ages)
                self.sheds[shed_i] = {
                    "chickens": [{"n": actual_chickens_per_shed, "age": week * 7}],
                    "cleaning": False,
                    "cleaning_completion": None,
                }
                total_chickens += actual_chickens_per_shed

            self.size = total_chickens  # updating the number in case the division is imperfect

            # no eggs at premises

        elif self.type == "pullet farm":
            # 6 to 20 weeks - https://www.poultryhub.org/production/chicken-egg-layer-industry/layer-farm-sequence
            self.approx_chickens_per_shed = 12000  # going by 12k-14k of chickens per shed

            self.num_sheds = math.ceil(self.size / self.approx_chickens_per_shed)
            chickens_possible_week_ages = list(range(1, 20 + 1))
            self.accepts_hatchlings = True
            actual_chickens_per_shed = int(self.size / self.num_sheds)

            total_chickens = 0
            for shed_i in range(1, self.num_sheds + 1):
                week = np.random.choice(chickens_possible_week_ages)
                self.sheds[shed_i] = {
                    "chickens": [{"n": actual_chickens_per_shed, "age": week * 7}],
                    "cleaning": False,
                    "cleaning_completion": None,
                }
                total_chickens += actual_chickens_per_shed

            self.size = total_chickens  # updating the number in case the division is imperfect

            # no eggs at premises

        elif self.type == "egg processing":
            self.num_sheds = 1
            # no chickens at premises
            # assuming no eggs at premises on starting
            # assuming max capacity....
            # TODO: add in some capacity eventually ya

        elif self.type == "abbatoir":
            self.num_sheds = 1  # TODO - possibility to add more sheds?
            self.approx_chickens_per_shed = 14000  # TODO - assuming this is their daily capacity...
            self.sheds[1] = {
                "chickens": [{"n": self.size, "age": 6 * 7}],  # broiler chickens ready for slaughter
                "cleaning": False,
                "cleaning_completion": None,
            }

            # no eggs at premises

        elif self.type == "hatchery":
            self.approx_chickens_per_shed = (
                12000  # going by 12k-14k of chickens per shed - number of eggs -> hatchlings
            )

            self.num_sheds = math.ceil(self.size / self.approx_chickens_per_shed)
            chickens_possible_week_ages = list(range(0, 4))  # actually fertilised egg ages.
            actual_chickens_per_shed = int(self.size / self.num_sheds)

            for shed_i in range(1, self.num_sheds + 1):
                week = np.random.choice(chickens_possible_week_ages)
                self.sheds[1] = {
                    "eggs": [{"n": actual_chickens_per_shed, "age": week * 7}],
                    "cleaning": False,
                    "cleaning_completion": None,
                }

            self.size = 0  # all eggs at the moment

        elif self.type == "breeder":
            self.approx_chickens_per_shed = 12000  # going by 12k-14k of chickens per shed

            self.num_sheds = math.ceil(self.size / self.approx_chickens_per_shed)
            actual_chickens_per_shed = int(self.size / self.num_sheds)

            chickens_possible_week_ages = list(range(20, 78))  # laying chickens
            total_chickens = 0
            for shed_i in range(1, self.num_sheds + 1):
                week = np.random.choice(chickens_possible_week_ages)
                self.sheds[shed_i] = {
                    "chickens": [{"n": actual_chickens_per_shed, "age": week * 7}],
                    "cleaning": False,
                    "cleaning_completion": None,
                }
                total_chickens += actual_chickens_per_shed

            self.size = total_chickens  # updating the number in case the division is imperfect

            self.eggs = self.approx_chickens_per_shed * np.random.randint(
                0, self.num_sheds
            )  # assuming some backlog; all are fertilised eggs by default
        else:
            raise ValueError(f"property type not expected: {self.type}")

    def convert_to_animal_objects(self):
        pass

    def init_animals(self, params):
        if self.animal_type != "chicken":
            super().init_animals(params)  # call the OG init_animals function
        else:
            for shed_i, shed_info in self.sheds.items():
                if "chickens" in shed_info:
                    for chicken_dict in self.sheds[shed_i]["chickens"]:
                        chicken_animal_objs = [Animal(params) for _ in range(chicken_dict["n"])]
                        chicken_dict["objs"] = chicken_animal_objs

                    print(self.sheds[shed_i]["chickens"])
                    # for i in range(len(self.sheds[shed_i]['chickens'])):
                    #     original_dict = self.sheds[shed_i]['chickens'][i]
                    #     chicken_animal_objs = [Animal(params) for _ in range(original_dict['n'])]
                    #     original_dict['objs'] = chicken_animal_objs
                    #     self.sheds[shed_i]['chickens'][i] = original_dict # doing this because I'm not sure if it's in place? TODO: check this

        return

    #
    def vaccinate(self, time):
        self.vaccination_status = 1
        self.vacc_date = convert_time_to_date(time)

        return 0

    def vaccination(self, prob_vaccinate, properties, time, culled_neighbours_only=True):
        """Decide whether or not to vaccinate

        Since we will allow properties to vaccination *without* needing culled neighbours, this code has been adapted from the original definition

        Should first check whether or not it's already culled
        """

        if culled_neighbours_only:
            prop_culled_neighbours = 0
            if len(self.neighbourhood):  # premise has neighbours
                neighbours = [el[0] for el in self.neighbourhood]
                culled_neighbours = sum([properties[i].culled_status for i in neighbours])
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

        report = f"DAY {self.removal_date} - Property ID {self.id}, {round(self.area,1)} ha cattle property at location (x,y)=({round(self.x,2)}, {round(self.y,2)}), {self.location}, is within the ring culling zone.\nA total of {self.size} animal(s) have been culled.\n"

        return report, self.size

    def report_only(self, time):
        report = ""
        self.notification_date = convert_time_to_date(time)
        self.status = "IP"
        self.ip = next(Premises.notified_iter)
        self.reported_status = True

        culled_animals = self.size
        if self.animal_type != "chicken":
            report = f"DAY {self.notification_date} - IP {self.ip} (ID {self.id}), {round(self.area,1)} ha cattle property at location (x,y)=({round(self.x,2)}, {round(self.y,2)}), {self.location}, has been found infected. A total of {culled_animals} animal(s) will be culled."
        else:
            self.size = self.get_num_chickens()
            culled_animals = self.size
            report = f"DAY {self.notification_date} - Property ID {self.id} has been designated IP {self.ip}, located at (x,y)=({round(self.x,2)}, {round(self.y,2)}), {self.location}. The property has a total of {culled_animals} chicken(s) and {self.get_num_eggs()+self.get_num_fertilised_eggs()} egg(s)."

        return report

    def cull_only(self, time):
        self.infection_status = 0
        self.culled_status = 1
        # all animals culled
        self.animals = []

        self.removal_date = convert_time_to_date(time)

        report = ""
        culled_animals = self.size

        report = f"DAY {convert_time_to_date(time)} - IP {self.ip} (ID {self.id}), {round(self.area,1)} ha cattle property at location (x,y)=({round(self.x,2)}, {round(self.y,2)}), {self.location}, has been depopulated.\nA total of {culled_animals} animal(s) have been culled."

        return report, culled_animals

    def prob_of_reporting_only(self, clinical_reporting_threshold, prob_report):
        if self.prop_clinical > clinical_reporting_threshold:
            reporting_rand = np.random.rand()
            chance_of_reporting = prob_report * self.prop_clinical

            # we assume once a property reports infection, they are immediately culled
            if reporting_rand < chance_of_reporting:
                return True
        return False

    def report_suspicion(self, time):
        # report = f"DAY {convert_time_to_date(time)} - Property ID {self.id} ({self.type}), {round(self.area,1)} ha cattle property at location (x,y)=({round(self.x,2)}, {round(self.y,2)}), {self.location}, has been reported possible infection.\n"
        # TODO ! there should be some kind of status change here...
        self.clinical_report_outcome = True

        if self.animal_type != "chicken":

            report = f"Property ID {self.id} ({self.type}), {round(self.area,1)} ha cattle property at location (x,y)=({round(self.x,2)}, {round(self.y,2)}), {self.location}, has been reported possible infection."
        else:
            report = f"Property ID {self.id} ({self.type}) at location ({round(self.x,2)}, {round(self.y,2)}), {self.location}, has been reported possible infection."
            self.status = "SP"  # suspect premises

        return report

    def reporting(self, clinical_reporting_threshold, prob_report, time, force_report=False):
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
            self.removal_date = convert_time_to_date(time)

        report = ""
        culled_animals = 0
        if self.culled_status == 1:
            culled_animals = self.size
            report += self.report_only(time)

            report = f"DAY {self.notification_date} - IP {self.ip} (ID {self.id}), {round(self.area,1)} ha cattle property at location (x,y)=({round(self.x,2)}, {round(self.y,2)}), {self.location}, has been reported infected.\nA total of {culled_animals} animal(s) have been culled.\n"

        return report, culled_animals

    def movement_flag(self, day):
        """Returns true if there is movement on this day, and no if not"""
        # if it's a movement day for this property
        if not ((day - self.movement_start_day) % self.movement_frequency):
            # if there is movement
            prob_movement = np.random.rand()
            if prob_movement < self.movement_probability:
                return True
        return False

    def calculate_allowed_movement_neighbours(self, property_indices_with_allowed_movement):
        # this is because, during the simulation, control zones mean that movement is not allowed to all properties in "movement_neighbours", so we just need to re-calculate where you can actually move
        allowed_movement_neighbours = {}
        total_num_allowed = 0
        for allowed_type in self.movement_neighbours.keys():
            allowed_movement_neighbours[allowed_type] = []
            for j in self.movement_neighbours[allowed_type]:
                if j in property_indices_with_allowed_movement:
                    allowed_movement_neighbours[allowed_type].append(j)
                    total_num_allowed += 1

        return allowed_movement_neighbours, total_num_allowed

    def calculate_num_animals_to_move(self):
        """note, this assumes that movement WILL occur; the return value can be zero"""
        property_size = len(
            self.animals
        )  # TODO need to update this, self.animals may not be accurate anymore with chickens in arrays
        number_animals = int(np.floor(self.movement_prop_animals * property_size))
        if property_size > 1 and number_animals == 0:
            number_animals = 1  # keeping at least one animal in each property

        return number_animals

    def calculate_where_to_move(self, num_properties_to_move_to, allowed_movement_neighbours):
        # I need self.allowed_movement

        property_types_to_move_to = []
        weights = []
        for type, indices_list in allowed_movement_neighbours.items():
            if len(indices_list) > 0:
                property_types_to_move_to.append(type)
                weights.append(self.allowed_movement[type])

        if sum(weights) == 0:
            return []
        else:
            weights = [i / sum(weights) for i in weights]

        move_to_types_list = np.random.choice(
            property_types_to_move_to, size=num_properties_to_move_to, replace=True, p=weights
        )

        return move_to_types_list

    def move_out_animals(self, number_animals):
        moving_animal_list = []
        for _ in range(int(number_animals)):
            moving_animal_index = np.random.randint(0, len(self.animals))

            moving_animal = self.animals.pop(moving_animal_index)

            moving_animal_list.append(moving_animal)

        self.size = len(self.animals)  # updating this

        return moving_animal_list

    def move_out_an_infectious_animal(self):
        for animal_index in range(len(self.animals)):
            if self.animals[animal_index].infection_status in ["exposed", "infectious"]:
                moving_animal = self.animals.pop(animal_index)
                self.size = len(self.animals)  # updating this
                return moving_animal

        return False

    def add_animals(self, moving_animal_list):
        for moving_animal in moving_animal_list:
            self.animals.append(moving_animal)
        self.size = len(self.animals)  # updating this

        return 0

    def infection_model(self, latent_period, infectious_period, preclinical_period, FOI, time):
        params = {
            "latent_period": latent_period,
            "infectious_period": infectious_period,
            "pre-clinical_period": preclinical_period,
        }

        if self.animal_type != "chicken":
            super().infection_model(
                params,
                FOI,
            )
        else:
            # infection model for each animals

            for i in range(len(self.chickens)):
                # if there are already animal objects...
                if len(self.chickens[i]) > 3:
                    for chicken in self.chickens[i][3]:
                        animal_inf = chicken.infection_event(params, FOI)
                        if animal_inf:
                            self.cumulative_infections += 1
                        chicken.check_transition(params)
                        chicken.update_clock()
                else:
                    if FOI > 0:  # i.e., they can get infected
                        # convert to animal objects
                        self.init_animals(None)
                        for chicken in self.chickens[i][3]:
                            animal_inf = chicken.infection_event(params, FOI)
                            if animal_inf:
                                self.cumulative_infections += 1
                            chicken.check_transition(params)
                            chicken.update_clock()
                    else:
                        pass  # pass  - no infection risk

        # TODO to be honest, not sure if this is correct, since infection staus and stuff don't update until later....
        if self.infection_status == 1 and self.exposure_date == "NA":
            self.exposure_date = convert_time_to_date(time)

        if self.prop_clinical > 0 and self.clinical_date == "NA":
            self.clinical_date = convert_time_to_date(
                time
            )  # might need to change this, but for now, it should be the earliest date with clinical symptoms # TODO : however, what does this mean if infected animals were all moved off the property?

    def return_output_row(self, RTM=False):
        """Returns a row with information for outputing (required downstream for forecasting)

        Returns
        -------
        list
            a list containing the following information in order:
            id, status, ip, exposure_date, clinical_date, notification_date, removal_date, recovery_date, vacc_date, region, county, cluster, xcoord, ycoord, area, type, total

        """
        if RTM:
            if self.animal_type == "chicken":
                if self.status == "IP":  # meaning that some culling has occured
                    num_animals = (
                        self.get_num_chickens() + self.custom_info["culled_birds"]
                    )  # get the total number of live chickens and culled birds
                else:
                    num_animals = self.get_num_chickens()
            else:
                num_animals = self.size

            return [
                self.id,
                self.status if self.status == "IP" else "NIL",
                self.clinical_date,
                self.notification_date,
                self.recovery_date,
                self.removal_date,
                self.vacc_date,
                self.coordinates[0],
                self.coordinates[1],
                self.area,
                num_animals,
            ]

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
            self.animal_type,
            self.size,
        ]

    def return_known_output_row(self, RTM=False):
        """Returns a row with *known* information for outputing (required downstream for forecasting)

        I.e., by "known", I mean that if an infected property hasn't notified yet, then there shouldn't be anything printed there regarding clinical dates

        Returns
        -------
        list
            a list containing the following information in order:
            id, status, ip, exposure_date, clinical_date, notification_date, removal_date, recovery_date, vacc_date, region, county, cluster, xcoord, ycoord, area, type, total

        """

        if self.animal_type == "chicken":
            try:
                property_data_known = self.custom_info["property_data_known"]
            except:
                property_data_known = False

            if property_data_known:
                num_animals = self.get_num_chickens()
                if "culled_birds" in self.custom_info:
                    num_animals += self.custom_info["culled_birds"]
            else:
                num_animals = rounding_entities(
                    self.get_num_chickens()
                )  # technically, this should only get used if the property isn't an IP? so don't need to add in culled birds
                if "culled_birds" in self.custom_info:
                    num_animals += self.custom_info["culled_birds"]
        else:
            num_animals = self.size

        if self.reported_status:  # if reported already, then all information can be provided
            return self.return_output_row(RTM)
        if self.culled_on_suspicion:  # if culled on suspicion, then exposure, clinical, notification dates should be NA
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
                self.animal_type,
                num_animals,
            ]
        elif RTM:
            return [
                self.id,
                self.status if self.status == "IP" else "NIL",
                "NA",  # self.clinical_date,
                self.notification_date,  # this should already be "NA"
                self.recovery_date,  # this should already be "NA"
                self.removal_date,  # this should already be "NA"
                self.vacc_date,
                self.coordinates[0],
                self.coordinates[1],
                self.area,
                num_animals,
            ]

        else:
            return [
                self.id,
                self.status,  # if self.status == "IP" else "NA",
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
                self.animal_type,
                num_animals,
            ]

    def check_if_chicken_objects(self):
        """Return False if it's still array; return true if there are chicken objects"""
        if len(self.chickens) > 0:
            if len(self.chickens[0]) == 3:
                return False
            else:
                return True
        return False

    def chicken_array(self):
        """Returns the chicken array for printing - needed in the case that it's actually full of chicken objects"""
        chick_array = []
        for shed_i, shed_info in self.sheds:
            try:
                for chickens_row in shed_info["chickens"]:
                    chick_array.append({"shed": shed_i, "n": chickens_row["n"], "age": chickens_row["age"]})
            except:
                pass

        return chick_array

    def get_num_chickens(self):
        num_chickens = 0
        for shed_i, shed_info in self.sheds.items():
            try:
                for chickens_row in shed_info["chickens"]:
                    num_chickens += chickens_row["n"]
            except:
                pass  # for the case that it doesn't have chickens

        self.size = num_chickens
        return num_chickens

    def get_num_eggs(self):
        if self.type != "breeder" and self.type != "hatchery":
            return self.eggs
        else:
            return 0

    def get_num_fertilised_eggs(self):
        if self.type == "breeder":
            return self.eggs
        elif self.type == "hatchery":
            num_eggs = 0
            for shed_i, shed_info in self.sheds.items():
                try:
                    for eggs_row in shed_info["eggs"]:
                        num_eggs += eggs_row["n"]
                except:
                    pass  # for the case that it doesn't have eggs
        else:
            return 0

    def update_counts(self):
        if self.animal_type != "chicken":
            super.update_counts()
        else:
            number_infected = 0
            number_infectious = 0
            number_clinical = 0
            if self.check_if_chicken_objects() == False:
                # no infections
                self.prop_infectious = 0
                self.prop_clinical = 0
                self.number_infected = 0
                self.size = self.get_num_chickens()
            else:
                # potential infection, check chickens one by one
                total_number_of_chickens = 0
                for row in self.chickens:
                    total_number_of_chickens += row[0]
                    for chicken in row[3]:
                        if chicken.infection_status == "exposed":
                            number_infected += 1
                        elif chicken.infection_status == "infectious":
                            number_infected += 1
                            number_infectious += 1

                        # check how many animals are showing clinical symptoms (reporting)
                        if chicken.clinical_status == "clinical":
                            number_clinical += 1

                self.size = total_number_of_chickens

                # record proportion of animals infectious and clinical for other calculations
                self.prop_infectious = number_infectious / total_number_of_chickens
                self.prop_clinical = number_clinical / total_number_of_chickens

                # if there's any infection, property is labelled infected
                self.number_infected = number_infected
                if number_infected > 0:
                    self.infection_status = 1

    def return_output_row_chickens(self):
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
            self.animal_type,
            self.get_num_chickens(),
            self.num_sheds,
            self.chicken_array(),  # self.chickens,
            self.get_num_eggs(),
            self.get_num_fertilised_eggs(),
        ]

    def accepting_animals(self, time=0):
        """
        Function to check if this premises is ready to accept animals (birds), and return the shed number that is free, for movement

        relevant for pullet farm, broiler farm and layers, and abbatoirs

        :param self: Description
        """

        chickens_per_shed = {shed_i: 0 for shed_i in range(1, self.num_sheds + 1)}
        for row in self.chickens:
            chickens_per_shed[row[1]] += row[0]

        empty_sheds = []
        for shed, num_chickens in chickens_per_shed.items():
            if num_chickens == 0:
                empty_sheds.append(shed)

                # TODO: add a check of when the shed was emptied / if it's still in the "cleaning" status or not, or something like that

        return empty_sheds, self.approx_chickens_per_shed

    def want_to_move_chickens_hatchery(self):
        num_chickens_to_move_abbatoir = 0
        row_indices_to_move_abbatoir = []
        for i in range(len(self.chickens)):
            row = self.chickens[i]
            chicken_age = row[2]
            if chicken_age > 546:  # TODO - well, there should be something better about this
                num_chickens_to_move_abbatoir += row[0]
                row_indices_to_move_abbatoir.append(i)

        property_types_to_move_to_abbatoir = [
            "abbatoir"
        ]  # TODO - need to refactor to avoid hard coding if possible OTL

        pass  # TODO - hard!!! need to keep laying chickens!

    def want_to_move_chickens_pullet_farm(self):
        num_chickens_to_move = 0
        row_indices_to_move = []
        for i in range(len(self.chickens)):
            row = self.chickens[i]
            chicken_age = row[2]
            if chicken_age > 119:  # TODO - well, there should be something better about this
                num_chickens_to_move += row[0]
                row_indices_to_move.append(i)

        property_types_to_move_to = [
            "layers free-range",
            "layers caged",
            "layers barn",
        ]  # TODO - need to refactor to avoid hard coding if possible OTL

        return num_chickens_to_move, row_indices_to_move, property_types_to_move_to

    def want_to_move_animals(self):
        pass

    def want_to_move_eggs(self):
        pass
