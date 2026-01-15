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


geolocator = Nominatim(user_agent="http")


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

    def init_chickens_eggs(self):
        """Initiating things that are specific for chicken (meat and egg) premises
        Could turn this into a new class that inherits the premises class in the future
        """
        # num chickens: in self.size
        self.chickens = []
        self.eggs = []
        self.eggs_fertilised = []

        if "layers" in self.type:
            if self.type == "layers free-range":
                approx_chickens_per_shed = 10000  # for free range, the number should be less than other cases
            elif self.type == "layers caged":
                approx_chickens_per_shed = 14000  # going by 12k-14k of chickens per shed
            elif self.type == "layers barn":
                approx_chickens_per_shed = 12000  # going by 12k-14k of chickens per shed

            if 2 * approx_chickens_per_shed < self.size:
                # if there are a LOT of chickens, then let them also rear pullets
                # TODO: place them in different sheds technically
                weeks_dispersion = 78 - 1
                age_group_lower = 1
            else:
                # https://www.poultryhub.org/production/chicken-egg-layer-industry/layer-farm-sequence
                #  laying chickens, assume age is from 20 weeks to 78 weeks
                # assuming full capcity, running flow
                weeks_dispersion = 78 - 20
                age_group_lower = 20
            chickens_per_age_group = int(self.size / weeks_dispersion)
            total_chickens = 0
            shed_num = 1
            total_laying_chickens = 0
            for week in range(age_group_lower, 78):
                if total_chickens > shed_num * approx_chickens_per_shed:
                    shed_num += 1
                # num chickens, shed number, age by days
                self.chickens.append([chickens_per_age_group, shed_num, week * 7])
                total_chickens += chickens_per_age_group
                if week >= 20:
                    total_laying_chickens += chickens_per_age_group

            self.size = total_chickens  # updating the number in case the division is imperfect
            self.num_sheds = shed_num

            # eggs: num eggs, age of eggs , no shed?
            self.eggs = [
                [int(total_laying_chickens / 5), 0],  # assuming that not all the chickens lay every day,
                [int(total_laying_chickens / 5), 1],  # and that it takes a few days for eggs to be processed/removed
                [int(total_laying_chickens / 5), 2],
            ]

        elif self.type == "meat growing-farm":
            # broilers: 4-6 weeks of age https://kb.rspca.org.au/categories/farmed-animals/poultry/meat-chickens/how-are-meat-chickens-farmed-in-australia

            approx_chickens_per_shed = 12000  # going by 12k-14k of chickens per shed
            weeks_dispersion = 6 - 4
            chickens_per_age_group = int(self.size / weeks_dispersion)
            total_chickens = 0
            shed_num = 1
            for week in range(4, 6):
                if total_chickens > shed_num * approx_chickens_per_shed:
                    shed_num += 1
                # num chickens, shed number, age by days
                if chickens_per_age_group > approx_chickens_per_shed:
                    num_sheds_needed = int(chickens_per_age_group / approx_chickens_per_shed)
                    approx_chickens_per_shed_in_age_group = int(chickens_per_age_group / num_sheds_needed)
                    for shed in range(num_sheds_needed):
                        self.chickens.append([approx_chickens_per_shed_in_age_group, shed_num, week * 7])
                        total_chickens += approx_chickens_per_shed_in_age_group
                        if shed < num_sheds_needed - 1:
                            shed_num += 1
                else:
                    self.chickens.append([chickens_per_age_group, shed_num, week * 7])
                    total_chickens += chickens_per_age_group

            self.size = total_chickens  # updating the number in case the division is imperfect
            self.num_sheds = shed_num

            # no eggs at premises

        elif self.type == "pullets farm":
            # 6 to 20 weeks - https://www.poultryhub.org/production/chicken-egg-layer-industry/layer-farm-sequence
            approx_chickens_per_shed = 12000  # going by 12k-14k of chickens per shed
            weeks_dispersion = 20 - 1  # starting from week old chicks
            chickens_per_age_group = int(self.size / weeks_dispersion)
            total_chickens = 0
            shed_num = 1
            for week in range(6, 20):
                if total_chickens > shed_num * approx_chickens_per_shed:
                    shed_num += 1
                # num chickens, shed number, age by days
                self.chickens.append([chickens_per_age_group, shed_num, week * 7])
                total_chickens += chickens_per_age_group

            self.size = total_chickens  # updating the number in case the division is imperfect
            self.num_sheds = shed_num

            # no eggs at premises

        elif self.type == "egg processing":
            self.num_sheds = 1
            # no chickens at premises
            # assuming no eggs at premises on starting
        elif self.type == "abbatoir":
            self.num_sheds = 1
            self.chickens = [[self.size, self.num_sheds, 6 * 7]]  # assuming all broiler chickens
            # no eggs at premises
        elif self.type == "hatchery":
            approx_chickens_per_shed = 12000  # going by 12k-14k of chickens per shed

            # laying chickens
            weeks_dispersion = 78 - 20
            chickens_per_age_group = int(self.size / weeks_dispersion)
            total_chickens = 0
            shed_num = 1
            for week in range(20, 78):
                if total_chickens > shed_num * approx_chickens_per_shed:
                    shed_num += 1
                # num chickens, shed number, age by days
                self.chickens.append([chickens_per_age_group, shed_num, week * 7])
                total_chickens += chickens_per_age_group

            self.size = total_chickens  # updating the number in case the division is imperfect
            self.num_sheds = shed_num

            self.eggs_fertilised = [[self.size, day] for day in [0, 7, 14, 20]]  # eggs at various stages

            pass  # TODO actually need to calculate the number of chickens the hatchery has to support the other stuff
        else:
            raise ValueError(f"property type not expected: {self.type}")

    def convert_to_animal_objects(self):
        pass

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

        report = f"DAY {self.notification_date} - IP {self.ip} (ID {self.id}), {round(self.area,1)} ha cattle property at location (x,y)=({round(self.x,2)}, {round(self.y,2)}), {self.location}, has been found infected. A total of {culled_animals} animal(s) will be culled."

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

        report = f"Property ID {self.id} ({self.type}), {round(self.area,1)} ha cattle property at location (x,y)=({round(self.x,2)}, {round(self.y,2)}), {self.location}, has been reported possible infection."

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
        property_size = len(self.animals)
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
        super().infection_model(
            {
                "latent_period": latent_period,
                "infectious_period": infectious_period,
                "pre-clinical_period": preclinical_period,
            },
            FOI,
        )

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
                self.size,
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
                self.size,
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
                self.size,
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
                self.size,
            ]

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
            self.size,
            self.num_sheds,
            self.chickens,
            self.eggs,
            self.eggs_fertilised,
        ]
