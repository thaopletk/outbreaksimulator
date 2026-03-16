"""Disease Simulator

Creates a DiseaseSimulator object to run spread simulation

Typical workflow involves calling:
* init
* set_plotting_parameters
* simulator function of choice... making sure to reset set_plotting_parameters for different parts

"""

import sys
import os
import random
import pandas as pd
import itertools

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import numpy as np

from shapely.geometry import Point, Polygon

# import csv
# import math
import pickle
import matplotlib.pyplot as plt
import simulator.spatial_setup as spatial_setup
import simulator.management as management
import simulator.premises as premises
import simulator.SEIR as SEIR
import simulator.output as output
import simulator.animal_movement as animal_movement
import simulator.spatial_functions as spatial_functions
import simulator.HPAI_functions as HPAI_functions
import simulator.fixed_spatial_setup as fixed_spatial_setup
from datetime import datetime as dt

# from iteround import saferound
from shapely.ops import transform, unary_union

# from simulator.spatial_functions import quick_distance_haversine
import simulator.simulator as simulator


class DiseaseSimulation:
    """A class to represent the disease parameters and disease simulation scenario"""

    def __init__(
        self,
        time=0,
        movement_records=animal_movement.create_movement_records_df(),
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
        scenario_parameters={"clinical_reporting_threshold": 0.05, "prob_report": 0.7},
    ):
        """
        A class used to represent the simulation model controller

        Attributes
        ----------
        (so many attributes... - TODO)


        Methods
        ----------
        (so many methods - TODO)

        """

        self.time = time

        self.movement_records = movement_records

        animal_types = list(disease_parameters.keys())

        self.beta_wind = {animal: disease_parameters[animal]["beta_wind"] for animal in animal_types}
        self.beta_animal = {animal: disease_parameters[animal]["beta_animal"] for animal in animal_types}
        self.latent_period = {animal: disease_parameters[animal]["latent_period"] for animal in animal_types}
        self.infectious_period = {animal: disease_parameters[animal]["infectious_period"] for animal in animal_types}
        self.preclinical_period = {animal: disease_parameters[animal]["preclinical_period"] for animal in animal_types}

        self.r_wind = spatial_only_parameters["r_wind"]

        self.clinical_reporting_threshold = scenario_parameters["clinical_reporting_threshold"]
        self.prob_report = scenario_parameters["prob_report"]
        self.prob_report_commercial = scenario_parameters["prob_report_commercial"]
        self.prob_report_backyard = scenario_parameters["prob_report_backyard"]

        self.vax_modifier = 0.6

        self.combined_narrative = []  # ["day","date","type","property sim id", "report", "property case id"]

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

        self.job_manager = management.JobManager(spatial_only_parameters["n"], **job_parameters)
        self.total_culled_animals = 0
        self.controlzone = {}  # empty control zone
        self.contacts_for_plotting = {}  # empty, as no contact tracing will occur here

        self.daily_statistics = {}  # converted_date, stat types

        self.first_detection_day = None

        self.case_id_counter = 0
        self.notified_iter = itertools.count(start=1)

    def set_plotting_parameters(self, xlims, ylims, plotting=True, folder_path="", unique_output=""):
        """Sets the plotting parameters, especially important to update regularly if you want things to output to a different folder"""
        self.xlims = xlims
        self.ylims = ylims
        self.plotting = plotting
        self.folder_path = folder_path
        self.unique_output = unique_output

    def set_vax_modifier(self, vax_modifier):
        self.vax_modifier = vax_modifier

    def save_reports(self, properties, restricted_area=None, control_area=None, output_suffix=""):
        """Saves the text report (narrative) which includes all the actions and reports"""
        total_culled = 0
        total_vaccinated = 0

        total_properties_in_restricted_area = 0
        total_properties_in_control_area = 0
        for property in properties:
            if property.culled_status:
                total_culled += 1
            if property.vaccination_status:
                total_vaccinated += 1

            if restricted_area != None:
                if property.polygon.intersects(restricted_area):
                    total_properties_in_restricted_area += 1
            if control_area != None:
                if property.polygon.intersects(control_area):
                    total_properties_in_control_area += 1

        DCPs_positive_clinical_test_pending = 0
        DCPs_negative_clinical_test_pending = 0
        for property_index in self.job_manager.jobs_queue.keys():
            if property_index == "NA":  # zone based action
                pass
            else:
                if properties[property_index].status == "DCP":
                    for day, status in self.job_manager.jobs_queue[property_index]["LabTesting"].items():
                        if status == "in progress":
                            if properties[property_index].clinical_report_outcome:
                                DCPs_positive_clinical_test_pending += 1
                            else:
                                DCPs_negative_clinical_test_pending += 1

        to_save_narrative = [x[:] for x in self.combined_narrative]
        # to_save_narrative.append(
        #     [
        #         self.time,
        #         premises.convert_time_to_date(self.time),
        #         "summary",
        #         "",
        #         f"Total culled properties: {total_culled}; total vaccinated properties: {total_vaccinated}; total culled animals: {self.total_culled_animals}; total properties in restricted area: {total_properties_in_restricted_area}; total properties in control area: {total_properties_in_control_area}; DCPs_positive_clinical_test_pending: {DCPs_positive_clinical_test_pending}; DCPs_negative_clinical_test_pending: {DCPs_negative_clinical_test_pending}",
        #     ]  # TODO: update this for chickens
        # )
        narrative_df = pd.DataFrame(to_save_narrative, columns=["day", "date", "type", "sim_id", "report", "case_id"])

        narrative_df = narrative_df[["day", "date", "type", "sim_id", "case_id", "report"]]

        narrative_df.to_csv(os.path.join(self.folder_path, f"combined_narrative{output_suffix}.csv"), index=False)

    def save_daily_statistics(self, output_suffix=""):
        header = [
            "date",
            "num self-reported",
            "num positive clinical",
            "num lab tested",
            "num confirmed infected",
            "num tested negative",
            "DCP tested negative",
            "surveillance tested negative",
            "culled birds",
            "destroyed eggs",
            "vaccinated birds",
        ]
        data = []

        for key, value in self.daily_statistics.items():
            data.append(
                [
                    key,
                    value["num self-reported"],
                    value["num positive clinical"],
                    value["num lab tested"],
                    value["num confirmed infected"],
                    value["num tested negative"],
                    value["DCP tested negative"],
                    value["surveillance tested negative"],
                    value["culled birds"],
                    value["destroyed eggs"],
                    value["vaccinated birds"],
                ]
            )
        # order by the date
        data.sort(key=lambda x: x[0])
        # convert to dataframe
        # save the dataframe
        data_df = pd.DataFrame(data, columns=header)

        data_df.to_csv(os.path.join(self.folder_path, f"daily_statistics{output_suffix}.csv"), index=False)

    def save_preprocessed_plotting_information(self, properties):

        self_reported_list = []
        for row in self.combined_narrative:
            if row[2] == "report" and "has been reported possible infection" in row[4]:
                self_reported_list.append(row[3])
        source_indices = []
        for i, premise in enumerate(properties):
            if premise.reported_status == True or premise.clinical_report_outcome == True or premise.status == "DCP":
                source_indices.append(i)
            else:
                if i in self_reported_list:
                    source_indices.append(i)

        # will only have these points
        geometry_culled = []
        geometry_confirmed_infected = []
        geometry_DCP = []
        geometry_undergoing_testing = []
        geometry_vaccinated = []
        geometry_infected = []

        TPs = []

        for index, premise in enumerate(properties):
            long, lat = premise.coordinates
            curr_farm = Point(long, lat)
            if premise.culled_status == True:
                geometry_culled.append(curr_farm)

                contact_tracing_report, traced_property_indices = management.contact_tracing(properties, index, self.movement_records, self.time)
                TPs.extend(traced_property_indices)

            elif premise.reported_status == True:
                geometry_confirmed_infected.append(curr_farm)

                contact_tracing_report, traced_property_indices = management.contact_tracing(properties, index, self.movement_records, self.time)
                TPs.extend(traced_property_indices)

            elif premise.clinical_report_outcome == True or premise.status == "DCP" or index in self_reported_list:
                geometry_DCP.append(curr_farm)

                contact_tracing_report, traced_property_indices = management.contact_tracing(properties, index, self.movement_records, self.time)
                TPs.extend(traced_property_indices)
            elif premise.infection_status:
                geometry_infected.append(curr_farm)
            elif premise.undergoing_testing == True:
                geometry_undergoing_testing.append(curr_farm)

            if premise.vaccination_status:
                # # geometry_vaccinated.append(premise.polygon)
                # puff_p1 = Polygon(spatial_functions.geodesic_point_buffer(lat, long, km=10))
                # geometry_vaccinated.append(puff_p1)
                geometry_vaccinated.append(curr_farm)

        TPs = list(set(TPs))

        final_TPs = []
        TPs_undergoing_testing = []
        TPs_false_result = []
        for index in TPs:
            if index in geometry_culled or index in geometry_confirmed_infected or index in geometry_DCP:
                pass
            else:
                long, lat = properties[index].coordinates
                curr_farm = Point(long, lat)
                final_TPs.append(curr_farm)
                if properties[index].clinical_report_outcome == False:
                    if properties[index].undergoing_testing == True:
                        TPs_undergoing_testing.append(curr_farm)  # aka, it's still waiting for a lab test...
                    else:
                        TPs_false_result.append(curr_farm)
                elif (
                    properties[index].undergoing_testing == True
                ):  # clinical_report_outcome == None; means that it's waiting for a clinical team AND a lab test
                    TPs_undergoing_testing.append(curr_farm)

        plotting_stuff = [
            source_indices,
            geometry_culled,
            geometry_confirmed_infected,
            geometry_DCP,
            geometry_undergoing_testing,
            geometry_vaccinated,
            geometry_infected,
            TPs,
            TPs_undergoing_testing,
            TPs_false_result,
        ]

        with open(os.path.join(self.folder_path, "preprocessed_plotting_data" + str(self.time)), "wb") as file:
            pickle.dump(
                plotting_stuff,
                file,
            )

    def make_report(self, reported_property, converted_date, property_index):
        """Saves text in the combined narrative that a property reported"""
        OG_status = reported_property.status
        report = reported_property.report_suspicion(self.time)
        self.combined_narrative.append([self.time, converted_date, "report", property_index, report, ""])
        self.combined_narrative.append(
            [
                self.time,
                converted_date,
                "status_update",
                property_index,
                f"{reported_property.type} (sim_id {reported_property.id}) has updated status: {reported_property.status} (prior status: {OG_status})",
                reported_property.case_id,
            ]
        )
        if reported_property.case_id == None:
            self.case_id_counter += 1
            reported_property.case_id = self.case_id_counter
            self.combined_narrative.append(
                [
                    self.time,
                    converted_date,
                    "status_update",
                    property_index,
                    f"{reported_property.type} (sim_id {reported_property.id}) has been assigned case id {reported_property.case_id} {reported_property.status}",
                    reported_property.case_id,
                ]
            )
        if reported_property.data_source == "":
            reported_property.data_source = "self-report"  # for e.g. backyard premises

        reported_property.custom_info["self_report_date"] = converted_date

    def add_local_movement_restriction(self, reported_property, converted_date):
        """Adds the property area to movement restrictions (no movements to or from this property) and saves text in the combined narrative that this occurred"""
        self.combined_narrative.append(
            [
                self.time,
                converted_date,
                "control",
                reported_property.id,
                f"No movements are allowed to or from property {reported_property.id} ({reported_property.type})",
            ]
        )
        self.job_manager.local_movement_restrictions.append(reported_property.polygon)

    def add_contact_tracing_job(self, property_index, converted_date):
        """Adds (schedules) a contact tracing job to the job_manager, and adds text to the combined narrative that this occurred"""
        s_report = self.job_manager.schedule_contract_tracing(property_index, self.time)
        self.combined_narrative.append([self.time, converted_date, "tracing", property_index, s_report])

    def add_lab_testing_after_observation_job(self, property_i, property_index, converted_date):
        """Schedules lab testing (with reduced testing delay), and adds this note into the combined narrative"""
        report, scheduled_successful = self.job_manager.schedule_lab_testing_after_observation(property_index, self.time)

        self.combined_narrative.append([self.time, converted_date, "test", property_index, report])
        if scheduled_successful:
            property_i.undergoing_testing = True

    def run_property_selfreporting(self, properties, i):
        converted_date = premises.convert_time_to_date(self.time)
        self.daily_statistics[converted_date]["num positive clinical"] += 1

        property_i = properties[i]
        self.make_report(property_i, converted_date, i)

        # enact local movement restrictions around this property, just in case
        self.add_local_movement_restriction(property_i, converted_date)

        # schedule contact tracing
        self.add_contact_tracing_job(i, converted_date)

        # schedule lab testing
        self.add_lab_testing_after_observation_job(property_i, i, converted_date)

        return 0

    def simulate_property_reporting(self, properties):
        """Simulates property reporting, outside of the job management system"""

        did_any_properties_report = False

        for i, property_i in enumerate(properties):
            if (
                not property_i.culled_status
                and not property_i.reported_status
                and property_i.prob_of_reporting_only(self.clinical_reporting_threshold, self.prob_report)
            ):
                # essentially the same as a positive clinical observation

                did_any_properties_report = True

                self.run_property_selfreporting(properties, i)

        return did_any_properties_report

    def calculate_FOI_for_each_property(self, properties, outbreak_sim="LSD", time=0):
        """Calculates the force of infection for each property, to be run at the start of each day (before movement occurs)"""
        FOI = list(np.zeros(len(properties)))
        for i, property_i in enumerate(properties):
            if not property_i.culled_status:
                FOI[i] = SEIR.calculate_force_of_infection(
                    properties, i, self.vax_modifier, self.r_wind, self.beta_wind, self.beta_animal, outbreak_sim, time
                )
        return FOI

    def run_infection_model_for_each_property(self, properties, FOI):
        """Runs the infection model for each property, i.e., advances infection stages and checks if properties become infected or not"""
        for i, property_i in enumerate(properties):
            animal_type = property_i.animal_type
            property_i.infection_model(
                self.latent_period[animal_type],
                self.infectious_period[animal_type],
                self.preclinical_period[animal_type],
                FOI[i],
                self.time,
            )
        return properties

    # TODO: technically, it may be possible to just run a different simulate_outbreak_spread function, but just set the probability of reporting to zero, or to modularise things further (the code parts that are repeated across different functions)
    def simulate_outbreak_spread_only(
        self,
        properties,
        time=None,
        stop_time=7,
        reporting_region_check=[[140, 155], [-32, -29]],
        min_infected_premises=70,
        outbreak_sim="LSD",
        max_spread_time=150,
    ):
        """Run simulated outbreak, for undetected spread between (self.time (or time parameter if not NA)+1) and (stop_time) [inclusive], with no management


        Parameters
        ----------
        properties
            list of all the premises objects

        Returns
        -------

        """

        if time != None:
            self.time = time

        if self.folder_path == "":
            raise Warning("Default folder path hasn't changed - recommend that set_plotting_parameters() be run first")

        while self.time < stop_time:
            self.time += 1

            # function that ages eggs and chickens
            if outbreak_sim == "HPAI":
                HPAI_functions.advance_chicken_egg_ages(properties)
                HPAI_functions.egg_production(properties)
                HPAI_functions.finish_cleaning_sheds(properties, self.time)
                # TODO : in the future, can add some natural deaths...

            # calculate FOI for each property
            FOI = self.calculate_FOI_for_each_property(properties, outbreak_sim, self.time)

            # run infection model for each property
            properties = self.run_infection_model_for_each_property(properties, FOI)

            # movement of animals
            controlzone_movement_restrictions = None

            if outbreak_sim == "LSD":
                if self.time % 2 == 0:
                    movement_record = animal_movement.extra_southward_movement(properties, day=self.time)
                    self.movement_records = pd.concat([self.movement_records, movement_record], axis=0, ignore_index=True)
                else:
                    movement_record = animal_movement.animal_movement(properties, day=self.time, controlzone=controlzone_movement_restrictions)
                    self.movement_records = pd.concat([self.movement_records, movement_record], axis=0, ignore_index=True)
            elif outbreak_sim == "HPAI":
                movement_record, number_of_movement_requests = HPAI_functions.animal_movement(
                    properties, day=self.time, controlzone=controlzone_movement_restrictions
                )
                self.movement_records = pd.concat([self.movement_records, movement_record], axis=0, ignore_index=True)

            # update counts of infected/clinical/etc animals on each farm
            for i, premise in enumerate(properties):
                premise.update_counts()

            if self.plotting:
                simulator.plot_current_state(  # TODO - simulator is a weird place to put plotting, probably...
                    properties,
                    self.time,
                    self.xlims,
                    self.ylims,
                    self.folder_path,
                    self.controlzone,
                    infectionpoly=False,
                    contacts_for_plotting=self.contacts_for_plotting,
                    apparent_situation_plot=False,  # no point plotting this
                )

                # # should also save things for plotting: i.e., everything that I had used to actually plot
                # with open(os.path.join(self.folder_path, "plotting_data" + str(self.time)), "wb") as file:
                #     pickle.dump(
                #         [properties, self.time, self.xlims, self.ylims, self.controlzone, self.contacts_for_plotting],
                #         file,
                #     )

            if self.time == stop_time:
                # check if we actually have a property available in the reporting region yet or not; if not, extend the stop  time
                list_of_potential_reporting_properties = self.get_properties_in_reporting_region(
                    properties, reporting_region_check[0], reporting_region_check[1]
                )

                total_infected = 0
                for property_i in properties:
                    if property_i.exposure_date != "NA":
                        total_infected += 1
                if len(list_of_potential_reporting_properties) == 0 or total_infected < min_infected_premises:
                    if stop_time < max_spread_time:
                        stop_time += 1

        # since we're not going to show the videos anyway, only saving plot data at the end to limit memory consumption
        with open(os.path.join(self.folder_path, "plotting_data" + str(self.time)), "wb") as file:
            pickle.dump(
                [properties, self.time, self.xlims, self.ylims, self.controlzone, self.contacts_for_plotting],
                file,
            )

        # if self.plotting:
        #     output.make_video(self.folder_path, "map_underlying")
        #     output.make_video(self.folder_path, "map_apparent")

        simulator.save_outbreak_state(
            properties,
            self.time,
            self.folder_path,
            self.unique_output,
            total_culled_animals=0,
            movement_records=self.movement_records,
            job_manager=self.job_manager,
        )

        if outbreak_sim == "HPAI":
            fixed_spatial_setup.save_chicken_property_csv(properties, self.time, self.folder_path, self.unique_output)

        animal_movement.save_movement_record(self.folder_path, self.movement_records)

        return properties, self.movement_records, self.time

    def get_properties_in_reporting_region(self, properties, reportingregion_x, reportingregion_y):
        # find properties with infected (clinical infected) animals within reportingregion_x, reportingregion_y
        list_of_potential_reporting_properties = []
        for i, property_i in enumerate(properties):
            if property_i.clinical_date != "NA" and property_i.type != "backyard":
                x, y = property_i.coordinates
                if x >= reportingregion_x[0] and x <= reportingregion_x[1] and y >= reportingregion_y[0] and y <= reportingregion_y[1]:
                    list_of_potential_reporting_properties.append(i)
        return list_of_potential_reporting_properties

    def select_first_reported_property(self, properties, reportingregion_x, reportingregion_y):
        """Forces the first report of an infected property in the area that we want

        Parameters
        ----------
        properties
            list of all the premises objects
        reportingregion_x : list
            contains [min_x, max_x], defining the reporting region boundaries
        reportingregion_y : list
            contains [min_y, max_y], defining the reporting region boundaries

        Returns
        -------
        first_report_i : int
            index of the property that was first reported


        """

        list_of_potential_reporting_properties = self.get_properties_in_reporting_region(properties, reportingregion_x, reportingregion_y)

        if len(list_of_potential_reporting_properties) == 0:
            raise RuntimeError("No clinically infected properties found within the wanted reporting region")

        # randomly select one to be the first to report
        first_report_i = random.choice(list_of_potential_reporting_properties)

        return first_report_i

    def force_sim_pause_after_report(self, properties, restricted_area, control_area, output_suffix=""):
        simulator.plot_current_state(
            properties,
            self.time,
            self.xlims,
            self.ylims,
            self.folder_path,
            self.controlzone,
            infectionpoly=False,
            contacts_for_plotting=self.contacts_for_plotting,
        )
        self.save_preprocessed_plotting_information(properties)

        with open(os.path.join(self.folder_path, "plotting_data" + str(self.time)), "wb") as file:
            pickle.dump(
                [properties, self.time, self.xlims, self.ylims, self.controlzone, self.contacts_for_plotting],
                file,
            )

        simulator.save_outbreak_state(
            properties,
            self.time,
            self.folder_path,
            self.unique_output,
            total_culled_animals=self.total_culled_animals,
            movement_records=self.movement_records,
            job_manager=self.job_manager,
        )

        animal_movement.save_movement_record(self.folder_path, self.movement_records)
        self.save_reports(properties, restricted_area, control_area, output_suffix=output_suffix)
        self.job_manager.save_jobs_queue(self.folder_path)
        self.save_daily_statistics(output_suffix)

        # TODO: add in a "total" column? or add in relative costs/estimated costs and a total estimated cost...
        self.job_manager.calculate_resources_used(self.folder_path, output_suffix)

        dates_list = [premises.convert_time_to_date(t) for t in range(self.first_detection_day, self.time + 1)]
        # print(dates_list)
        daily_notifs = [0] * len(dates_list)

        for property_i in properties:
            notif_date = property_i.notification_date
            if notif_date != "NA":
                index = dates_list.index(notif_date)
                daily_notifs[index] += 1

        save_name = "daily_notifications"

        output.plot_daily_notifications_over_time(dates_list, daily_notifs, self.folder_path, save_name)

        output.plot_total_notifs_over_time(dates_list, daily_notifs, self.folder_path, save_name="total_notifs")

        daily_notifs_by_state = {}
        for property_i in properties:
            notif_date = property_i.notification_date
            if notif_date != "NA":
                if property_i.state not in daily_notifs_by_state:
                    daily_notifs_by_state[property_i.state] = [0] * len(dates_list)
                index = dates_list.index(notif_date)
                daily_notifs_by_state[property_i.state][index] += 1
        for state in daily_notifs_by_state.keys():
            output.plot_daily_notifications_over_time(dates_list, daily_notifs_by_state[state], self.folder_path, "daily_notifs_" + state)
            output.plot_total_notifs_over_time(dates_list, daily_notifs_by_state[state], self.folder_path, save_name="total_notifs_" + state)

        return properties, self.movement_records, self.time, self.total_culled_animals, self.job_manager

    def simulate_first_report(self, properties, reportingregion_x, reportingregion_y, outbreak_sim="LSD", output_suffix=""):
        """Simulates the first day of reporting and subsequent actions on that first day

        Parameters
        ----------
        properties
            list of all the premises objects
        reportingregion_x : list
            contains [min_x, max_x], defining the reporting region boundaries
        reportingregion_y : list
            contains [min_y, max_y], defining the reporting region boundaries

        Returns
        -------
        properties
            list of all the premises objects, may have changed
        first_report_i : int
            index of the property that was first reported
        traced_property_indices : list
            list of indices of the properties that had movements connected to the reported property

        """

        # new day, allow disease spread

        self.time += 1
        self.first_detection_day = self.time
        converted_date = premises.convert_time_to_date(self.time)
        self.daily_statistics[converted_date] = {
            "num self-reported": 0,
            "num positive clinical": 0,
            "num lab tested": 0,
            "num confirmed infected": 0,
            "num tested negative": 0,
            "DCP tested negative": 0,
            "surveillance tested negative": 0,
            "culled birds": 0,
            "destroyed eggs": 0,
            "vaccinated birds": 0,
        }

        if outbreak_sim == "HPAI":
            HPAI_functions.advance_chicken_egg_ages(properties)
            HPAI_functions.egg_production(properties)
            # TODO : in the future, can add some natural deaths...

        FOI = self.calculate_FOI_for_each_property(properties, outbreak_sim, self.time)

        properties = self.run_infection_model_for_each_property(properties, FOI)

        # forcing a property to report
        first_report_i = self.select_first_reported_property(properties, reportingregion_x, reportingregion_y)
        reported_property = properties[first_report_i]
        self.make_report(reported_property, converted_date, first_report_i)
        self.daily_statistics[converted_date]["num self-reported"] += 1

        return self.force_sim_pause_after_report(properties, restricted_area=None, control_area=None, output_suffix=output_suffix)

    def simulate_first_day(self, properties, reportingregion_x, reportingregion_y):
        """Simulates the first day of reporting and subsequent actions on that first day

        Parameters
        ----------
        properties
            list of all the premises objects
        reportingregion_x : list
            contains [min_x, max_x], defining the reporting region boundaries
        reportingregion_y : list
            contains [min_y, max_y], defining the reporting region boundaries

        Returns
        -------
        properties
            list of all the premises objects, may have changed
        first_report_i : int
            index of the property that was first reported
        traced_property_indices : list
            list of indices of the properties that had movements connected to the reported property

        """

        # new day, allow disease spread

        self.time += 1
        self.first_detection_day = self.time
        converted_date = premises.convert_time_to_date(self.time)
        self.daily_statistics[converted_date] = {
            "num positive clinical": 0,
            "num lab tested": 0,
            "num confirmed infected": 0,
            "num tested negative": 0,
            "DCP tested negative": 0,
            "surveillance tested negative": 0,
        }

        FOI = self.calculate_FOI_for_each_property(properties)

        properties = self.run_infection_model_for_each_property(properties, FOI)

        # forcing a property to report
        first_report_i = self.select_first_reported_property(properties, reportingregion_x, reportingregion_y)
        reported_property = properties[first_report_i]
        self.make_report(reported_property, converted_date, first_report_i)
        self.daily_statistics[converted_date]["num positive clinical"] += 1

        # movement restrictions on reported property
        self.add_local_movement_restriction(reported_property, converted_date)

        # record EMAI lab result (end of day, technically)
        self.combined_narrative.append(
            [
                self.time,
                converted_date,
                "test",
                first_report_i,
                f"EMAI lab has confirmed a positive LSD result for property {reported_property.id} ({reported_property.type})",
            ]
        )
        # add this as a job to the job queue for completeness
        self.job_manager.jobs_queue[reported_property.id]["LabTesting"][str(self.time)] = ["complete", converted_date]

        # general movements of animals
        controlzone_movement_restrictions = unary_union(self.job_manager.local_movement_restrictions)  # because it is definite not empty []
        self.controlzone["movement restrictions"] = controlzone_movement_restrictions  # this is for plotting purposes later

        movement_record = animal_movement.animal_movement(properties, day=self.time, controlzone=controlzone_movement_restrictions)
        self.movement_records = pd.concat([self.movement_records, movement_record], axis=0, ignore_index=True)

        # update counts
        for i, property_i in enumerate(properties):
            property_i.update_counts()

        # Contact tracing, movement restrictions on dangerous properties, clinical checkup will be arranged for the next day
        # this could just be a list of the dangerous properties
        contact_tracing_report, traced_property_indices = management.contact_tracing(properties, first_report_i, self.movement_records, self.time)
        self.combined_narrative.append([self.time, converted_date, "tracing", first_report_i, contact_tracing_report])
        # add this as a job to the job queue for completeness
        self.job_manager.jobs_queue[reported_property.id]["ContactTracing"][str(self.time)] = [
            "complete",
            converted_date,
        ]
        self.contacts_for_plotting[first_report_i] = traced_property_indices
        for t_i in traced_property_indices:
            self.combined_narrative.append([self.time, converted_date, "tracing", t_i, "This property has been identified as a TP"])
            self.add_local_movement_restriction(properties[t_i], converted_date)

        # Then close off this day

        if self.plotting:
            simulator.plot_current_state(
                properties,
                self.time,
                self.xlims,
                self.ylims,
                self.folder_path,
                self.controlzone,
                infectionpoly=False,
                contacts_for_plotting=self.contacts_for_plotting,
            )
            # should also save things for plotting: i.e., everything that I had used to actually plot
            with open(os.path.join(self.folder_path, "plotting_data" + str(self.time)), "wb") as file:
                pickle.dump(
                    [properties, self.time, self.xlims, self.ylims, self.controlzone, self.contacts_for_plotting],
                    file,
                )

            self.save_preprocessed_plotting_information(properties)

        return (
            properties,
            first_report_i,
            traced_property_indices,
        )

    def simulate_second_day(self, properties, first_report_i, traced_property_indices):
        """Simulates the second day of the outbreak, including ACDP lab confirmation of the first LSD report

        Parameters
        ----------
        properties
            list of all the premises objects
        first_report_i : int
            index of the property that was first reportedd
        traced_property_indices : list
            list of indices of the properties that had movements connected to the reported property

        Returns
        -------
        properties
            list of all the premises objects, may have changed
        """
        reported_property = properties[first_report_i]

        self.time += 1
        converted_date = premises.convert_time_to_date(self.time)
        self.daily_statistics[converted_date] = {
            "num positive clinical": 0,
            "num lab tested": 0,
            "num confirmed infected": 0,
            "num tested negative": 0,
            "DCP tested negative": 0,
            "surveillance tested negative": 0,
        }

        FOI = self.calculate_FOI_for_each_property(properties)

        properties = self.run_infection_model_for_each_property(properties, FOI)

        # general movements of animals
        controlzone_movement_restrictions = unary_union(
            self.job_manager.local_movement_restrictions
        )  # because it is definite not none [] ; and currently there are only local movement restrictions
        self.controlzone["movement restrictions"] = controlzone_movement_restrictions

        movement_record = animal_movement.animal_movement(properties, day=self.time, controlzone=controlzone_movement_restrictions)
        self.movement_records = pd.concat([self.movement_records, movement_record], axis=0, ignore_index=True)

        # update counts
        for i, premise in enumerate(properties):
            premise.update_counts()

        # clinical check up results for traced properties
        for i in traced_property_indices:
            testing_report, positive = management.test_property(
                properties,
                i,
                self.time,
                self.job_manager.clinical_test_sensitivity,
                test_type="clinical observation",
            )

            if positive:
                properties[i].clinical_report_outcome = True
                self.daily_statistics[converted_date]["num positive clinical"] += 1
                properties[i].status = "DCP"
            else:
                properties[i].clinical_report_outcome = False

            self.combined_narrative.append([self.time, converted_date, "test", i, testing_report])
            # add this as a job to the job queue for completeness
            self.job_manager.jobs_queue[i]["ClinicalObservation"][str(self.time)] = ["complete", converted_date]

        # ACDP lab confirmation
        self.combined_narrative.append(
            [
                self.time,
                converted_date,
                "test",
                reported_property.id,
                f"ACDP lab has confirmed a POSITIVE LSD result for property {reported_property.id} ({reported_property.type})",
            ]
        )
        self.job_manager.jobs_queue[reported_property.id]["LabTesting"][str(self.time)] = ["complete", converted_date]
        self.daily_statistics[converted_date]["num lab tested"] += 1
        self.daily_statistics[converted_date]["num confirmed infected"] += 1

        premise_report = reported_property.report_only(self.time)
        self.combined_narrative.append([self.time, converted_date, "report", reported_property.id, premise_report])

        # schedule culling of property
        report = self.job_manager.decision_to_cull(reported_property.id, self.time)
        self.combined_narrative.append([self.time, converted_date, "cull", reported_property.id, report])

        # schedule ACDP lab testing for traced properties
        # & schedule contact tracing for traced properties regardless of clinical observation
        for property_index in traced_property_indices:
            property_i = properties[property_index]
            self.add_lab_testing_after_observation_job(property_i, property_index, converted_date)
            self.add_contact_tracing_job(property_index, converted_date)
        # TODO : differentiate between ACDP and EMAI? or just ignore their differences later on, e.g. increase capacity for testing, equivalently meaning that EMAI and other labs have "come online"

        # plotting

        if self.plotting:
            simulator.plot_current_state(
                properties,
                self.time,
                self.xlims,
                self.ylims,
                self.folder_path,
                self.controlzone,
                infectionpoly=False,
                contacts_for_plotting=self.contacts_for_plotting,
            )
            # should also save things for plotting: i.e., everything that I had used to actually plot
            with open(os.path.join(self.folder_path, "plotting_data" + str(self.time)), "wb") as file:
                pickle.dump(
                    [properties, self.time, self.xlims, self.ylims, self.controlzone, self.contacts_for_plotting],
                    file,
                )
            self.save_preprocessed_plotting_information(properties)

        return properties

    def simulate_first_two_days(self, properties, reportingregion_x, reportingregion_y, time=None):
        """Simulates the first two days of the outbreak, in particular the first suspicious report and subsequent confirmation

        Parameters
        ----------
        properties
            list of all the premises objects
        reportingregion_x : list
            contains [min_x, max_x], defining the reporting region boundaries
        reportingregion_y : list
            contains [min_y, max_y], defining the reporting region boundaries

        Returns
        -------
        properties
            list of all the premises objects, may have changed
        self.movement_records
            all historical movement information
        self.time
            current day of the simulation
        self.total_culled_animals : int
            total culled animals (zero at this point)
        self.job_manager : JobManager object
            contains the current list of jobs and other functionality

        """
        if time != None:
            self.time = time

        if self.folder_path == "":
            raise Warning("Default folder path hasn't changed - recommend that set_plotting_parameters() be run first")

        properties, first_report_i, traced_property_indices = self.simulate_first_day(properties, reportingregion_x, reportingregion_y)

        properties = self.simulate_second_day(properties, first_report_i, traced_property_indices)

        simulator.save_outbreak_state(
            properties,
            self.time,
            self.folder_path,
            self.unique_output,
            total_culled_animals=self.total_culled_animals,
            movement_records=self.movement_records,
            job_manager=self.job_manager,
        )

        animal_movement.save_movement_record(self.folder_path, self.movement_records)
        self.save_reports(properties)
        self.job_manager.save_jobs_queue(self.folder_path)

        return properties, self.movement_records, self.time, self.total_culled_animals, self.job_manager

    def check_if_national_standstill(self, management_parameters):
        """Code to check if the management parameters involve a national standstill

        To be used if the function simulate_national_standstill(...) is merged in with the main management simulation

        Parameters
        ----------
        management_parameters : list of dicts
            dictionaries in list define the management type and associated parameters

        Returns
        -------
        bool
            True if there is a National Standstill, False otherwise

        """
        if isinstance(management_parameters, list):
            for item in management_parameters:
                if item["type"] == "national_standstill":
                    return True
        elif isinstance(management_parameters, dict):
            if "movement_restrictions" in management_parameters:
                if "national_standstill" in management_parameters["movement_restrictions"]:
                    return True
        return False

    def simulate_national_standstill(self, properties, days_to_run_for, time=None):
        """Run the national standstill proportion, assuming no movement, and only contact tracing

        Assumes that lab testing will be done regardless of whether clinical observation is positive or not;
        And also assumes no resourcing restrictions at this stage - only doing contact tracing

        Parameters
        ----------
        properties
            list of all the premises objects
        management_parameters : list of dicts
            dictionaries in list define the management type and associated parameters
        days_to_run_for : int
            number of days to run this particular set of management strategies

        Returns
        -------
        properties
            list of all the premises objects, may have changed
        self.movement_records
            all historical movement information
        self.time
            current day of the simulation
        self.total_culled_animals : int
            total culled animals
        self.job_manager : JobManager object
            contains the current list of jobs and other functionality
        """

        if time != None:
            self.time = time

        if self.folder_path == "":
            raise Warning("Default folder path hasn't changed - recommend that set_plotting_parameters() be run first")

        # national standstill - control zone defined for plotting purposes
        controlzone_large_movement_restrictions = spatial_setup.Australia_shape()
        controlzone_movement_restrictions = controlzone_large_movement_restrictions

        self.controlzone["movement restrictions"] = controlzone_movement_restrictions  # this is for plotting purposes later

        time_list = []
        stop_time = self.time + days_to_run_for
        while self.time < stop_time:
            self.time += 1
            converted_date = premises.convert_time_to_date(self.time)
            self.daily_statistics[converted_date] = {
                "num positive clinical": 0,
                "num lab tested": 0,
                "num confirmed infected": 0,
                "num tested negative": 0,
                "DCP tested negative": 0,
                "surveillance tested negative": 0,
            }
            # calculate FOI for each property
            FOI = self.calculate_FOI_for_each_property(properties)

            # check if any property wants to report
            self.simulate_property_reporting(properties)

            # run infection model for each property
            properties = self.run_infection_model_for_each_property(properties, FOI)

            # go through job queue
            new_combined_narrative, local_movement_restrictions, newly_culled_animals, contacts_for_plotting, stats = self.job_manager.run_jobs(
                self.time, properties, self.movement_records, converted_date
            )

            self.combined_narrative.extend(new_combined_narrative)
            self.contacts_for_plotting = contacts_for_plotting
            self.total_culled_animals += newly_culled_animals
            (
                num_positive_clinical,
                num_lab_tested,
                num_confirmed_infected,
                num_tested_negative,
                DCP_tested_negative,
                surveillance_tested_negative,
            ) = stats
            self.daily_statistics[converted_date]["num positive clinical"] += num_positive_clinical
            self.daily_statistics[converted_date]["num lab tested"] += num_lab_tested
            self.daily_statistics[converted_date]["num confirmed infected"] += num_confirmed_infected
            self.daily_statistics[converted_date]["num tested negative"] += num_tested_negative
            self.daily_statistics[converted_date]["DCP tested negative"] += DCP_tested_negative
            self.daily_statistics[converted_date]["surveillance tested negative"] += surveillance_tested_negative

            # and then go through job queue again in 0.5 time,

            new_combined_narrative, local_movement_restrictions, newly_culled_animals, contacts_for_plotting, stats = self.job_manager.run_jobs(
                self.time + 0.5, properties, self.movement_records, converted_date
            )
            self.combined_narrative.extend(new_combined_narrative)
            self.contacts_for_plotting.update(contacts_for_plotting)
            self.total_culled_animals += newly_culled_animals
            (
                num_positive_clinical,
                num_lab_tested,
                num_confirmed_infected,
                num_tested_negative,
                DCP_tested_negative,
                surveillance_tested_negative,
            ) = stats
            self.daily_statistics[converted_date]["num positive clinical"] += num_positive_clinical
            self.daily_statistics[converted_date]["num lab tested"] += num_lab_tested
            self.daily_statistics[converted_date]["num confirmed infected"] += num_confirmed_infected
            self.daily_statistics[converted_date]["num tested negative"] += num_tested_negative
            self.daily_statistics[converted_date]["DCP tested negative"] += DCP_tested_negative
            self.daily_statistics[converted_date]["surveillance tested negative"] += surveillance_tested_negative

            # no movement of animals

            # update counts of infected/clinical/etc animals on each farm (important too if any animals have moved locations)
            for i, premise in enumerate(properties):
                premise.update_counts()

            # then close off this day
            time_list.append(self.time)
            if self.plotting:
                simulator.plot_current_state(
                    properties,
                    self.time,
                    self.xlims,
                    self.ylims,
                    self.folder_path,
                    self.controlzone,
                    infectionpoly=False,
                    contacts_for_plotting=self.contacts_for_plotting,
                )
                # should also save things for plotting: i.e., everything that I had used to actually plot
                with open(os.path.join(self.folder_path, "plotting_data" + str(self.time)), "wb") as file:
                    pickle.dump(
                        [properties, self.time, self.xlims, self.ylims, self.controlzone, self.contacts_for_plotting],
                        file,
                    )

        if self.plotting:
            output.make_video(self.folder_path, "map_underlying", times=time_list)
            output.make_video(self.folder_path, "map_apparent", times=time_list)

        simulator.save_outbreak_state(
            properties,
            self.time,
            self.folder_path,
            self.unique_output,
            total_culled_animals=self.total_culled_animals,
            movement_records=self.movement_records,
            job_manager=self.job_manager,
        )

        animal_movement.save_movement_record(self.folder_path, self.movement_records)
        self.save_reports(properties)
        self.job_manager.save_jobs_queue(self.folder_path)
        self.save_daily_statistics()

        return properties, self.movement_records, self.time, self.total_culled_animals, self.job_manager

    def simulate_outbreak_management(
        self,
        properties,
        management_parameters,
        days_to_run_for,
        resource_setting="default",
        vaccination=False,
        time=None,
        decision=None,  # introduced for v04
    ):
        """Run simulated outbreak with management, for spread starting from self.time+1 for days_to_run_for, with management

        Parameters
        ----------
        properties
            list of all the premises objects
        management_parameters : list of dicts
            dictionaries in list define the management type and associated parameters
        days_to_run_for : int
            number of days to run this particular set of management strategies
        resource_setting : string
            "default": the 'default', i.e., the first two weeks
            "high": high management, more resources etc., i.e. second two weeks
            "low": less management, radius, decreased resources etc, i.e. for second two weeks

        Returns
        -------
        TODO
        """

        if time != None:
            self.time = time

        if self.folder_path == "":
            raise Warning("Default folder path hasn't changed - recommend that set_plotting_parameters() be run first")

        time_list = []
        stop_time = self.time + days_to_run_for
        nothing_left_to_do = False
        while self.time < stop_time and not nothing_left_to_do:
            self.time += 1
            converted_date = premises.convert_time_to_date(self.time)
            self.daily_statistics[converted_date] = {
                "num positive clinical": 0,
                "num lab tested": 0,
                "num confirmed infected": 0,
                "num tested negative": 0,
                "DCP tested negative": 0,
                "surveillance tested negative": 0,
            }

            # calculate FOI for each property
            FOI = self.calculate_FOI_for_each_property(properties)

            # check if any property wants to report
            self.simulate_property_reporting(properties)

            # run infection model for each property
            properties = self.run_infection_model_for_each_property(properties, FOI)

            # TODO enact any management, before animal movements, so that we can calculate control zones I guess
            # schedule all tasks, and then will prioritise later

            source_indices = []
            for i, premise in enumerate(properties):
                # also need to add in DCPs. This could either be: (1) properties with positive clinical result (well, at least), or more broadly could be (2) any properties currently on the contact tracing list/undergoing testing
                # to get the properties currently undergoing contact tracing or testing, I would need to go through the job queue, and find active jobs, and find the properties currently under active management
                if premise.reported_status == True or premise.clinical_report_outcome == True or premise.status == "DCP":
                    source_indices.append(i)

            # list_of_premises = self.job_manager.get_premises_under_active_jobs()
            # source_indices.extend(list_of_premises)
            # source_indices = list(set(source_indices))

            # Get current control/etc zones
            # Restricted area: highly restricted
            if isinstance(management_parameters, dict) and "movement_restrictions" in management_parameters:
                if "national_standstill" in management_parameters["movement_restrictions"]:
                    Australia_shape = spatial_setup.Australia_shape()
                    restricted_area = Australia_shape
                elif "restricted_area" in management_parameters["movement_restrictions"]:
                    restricted_area = management.define_control_zone_polygons(
                        properties,
                        source_indices,
                        management_parameters["movement_restrictions"]["restricted_area"],
                        convex=False,
                    )  # should be zero movement
                else:
                    raise ValueError("Movement restrictions that aren't national standstill not yet implemented")
            else:
                restricted_area = management.define_control_zone_polygons(
                    properties,
                    source_indices,
                    80,  # 5 km
                    convex=False,
                )  # should be zero movement

                # define restricted zone for all of Queensland and add to large_movement_restrictions
                if resource_setting in ["default", "high"]:
                    Queenslandshape = spatial_setup.get_Queensland_shape()
                    restricted_area = unary_union([restricted_area, Queenslandshape])

            self.controlzone["restricted area"] = restricted_area

            controlzone_large_movement_restrictions = restricted_area

            # Control area: less restricted
            if isinstance(management_parameters, dict) and "movement_restrictions" in management_parameters:
                if "national_standstill" in management_parameters["movement_restrictions"]:
                    control_area = Australia_shape
                elif "control_area" in management_parameters["movement_restrictions"]:
                    control_area = management.define_control_zone_polygons(
                        properties,
                        source_indices,
                        management_parameters["movement_restrictions"]["control_area"],  # 30 km
                        convex=False,
                    )
                    control_area = spatial_functions.expand_polygon_to_SALs(control_area)
                else:
                    raise ValueError("Control area restrictions that aren't national standstill not yet implemented")
            else:
                control_area = management.define_control_zone_polygons(
                    properties,
                    source_indices,
                    100,  # 100 km
                    convex=False,
                )
                # TODO: idk if I should include Queensland into the controlzone too or not ah.

                if resource_setting in ["default", "high"]:
                    # I want to do this buffer but it keeps breaking my laptop
                    # control_area = spatial_functions.geodesic_polygon_buffer(properties[0].y, properties[0].x, restricted_area, 80)
                    # control_area = spatial_functions.expand_polygon_to_LGAs(control_area)
                    control_area = spatial_functions.expand_polygon_to_SALs(control_area)
                else:
                    pass  # the control area will just be a circle around properties

            self.controlzone["control area"] = control_area

            # rough surveillance
            if resource_setting in ["default", "low"]:
                low_priority_surveillance_zone = management.define_control_zone_polygons(
                    properties,
                    source_indices,
                    50,  # 50 km
                    convex=False,
                )
                high_priority_surveillance_zone = control_area.difference(low_priority_surveillance_zone)
            else:  # resource_setting == "high"
                high_priority_surveillance_zone = control_area

            self.controlzone["surveillance area"] = high_priority_surveillance_zone

            if decision == "surveillancefocused":
                self.controlzone["surveillance area"] = control_area
                if self.time > 91:  # making it the convex hull, to give more jobs
                    self.controlzone["surveillance area"] = control_area.convex_hull

            # TODO expand more zones to match LGA and other boundaries?

            # assign new jobs - i.e. surveillance based on the control zones
            for i, premise in enumerate(properties):
                if (
                    not (premise.reported_status or premise.culled_status)
                    and premise.status != "DCP"
                    and premise.polygon.intersects(self.controlzone["surveillance area"])
                ):
                    self.combined_narrative.append(
                        [
                            self.time,
                            converted_date,
                            "surveillance",
                            i,
                            "This property has been identified for surveillance",
                        ]
                    )
                    report, scheduled_successful = self.job_manager.schedule_clinical_observation(i, self.time)
                    self.combined_narrative.append([time, converted_date, "test", i, report])
                    if scheduled_successful:
                        premise.undergoing_testing = True

            vaccination_zone = None
            if vaccination:
                vaccination_zone = high_priority_surveillance_zone  # leaving it as this for now, for easiness
                # assigning properties for vaccination

                if decision == "vaccinationfocused":
                    vaccination_zone = control_area
                    if self.time > 91:  # making it the convex hull, to give more jobs
                        vaccination_zone = control_area.convex_hull

                for i, premise in enumerate(properties):
                    if (
                        not (premise.reported_status or premise.culled_status)
                        and premise.status != "DCP"
                        and premise.polygon.intersects(vaccination_zone)
                    ):
                        self.combined_narrative.append(
                            [
                                self.time,
                                converted_date,
                                "vaccination",
                                i,
                                "This property has been shortlisted for vaccination",
                            ]
                        )
                        report, scheduled_successful = self.job_manager.schedule_vaccination(i, self.time)
                        self.combined_narrative.append([time, converted_date, "vaccination", i, report])

            # TODO: prioritise jobs based on zoning

            # for management_policy in management_parameters:
            #     if management_policy["type"] == "national_standstill":
            #         controlzone_large_movement_restrictions = (
            #             spatial_setup.Australia_shape()
            #         )  # TODO...should just read this once rather than multiple times?
            #     elif management_policy["type"] == "movement_restriction":
            #         controlzone_large_movement_restrictions = management.define_control_zone_polygons(
            #             properties,
            #             source_indices,
            #             management_policy["radius_km"],
            #             convex=management_policy["convex"],
            #         )
            #     elif management_policy["type"] == "conditional_movement":
            #         # TODO
            #         pass  #    {"type": "conditional_movement", "radius_km": 80, "convex": False, "probability_reduction": 0.1},
            #     elif management_policy["type"] == "ring_surveillance":
            #         # TODO
            #         pass  #  {"type": "ring_surveillance", "radius_km": 80, "convex": False},
            #     else:
            #         raise ValueError(
            #             f"Management policy type {management_policy['type']} doesn't exist, or is not yet implemented"
            #         )

            # TODO need to go through job queue, and prioritise tasks

            # go through job queue
            new_combined_narrative, local_movement_restrictions, newly_culled_animals, contacts_for_plotting, stats = self.job_manager.run_jobs(
                self.time,
                properties,
                self.movement_records,
                converted_date,
                resource_setting=resource_setting,
                v4decision=decision,
            )
            self.combined_narrative.extend(new_combined_narrative)
            self.contacts_for_plotting = contacts_for_plotting
            self.total_culled_animals += newly_culled_animals
            (
                num_positive_clinical,
                num_lab_tested,
                num_confirmed_infected,
                num_tested_negative,
                DCP_tested_negative,
                surveillance_tested_negative,
            ) = stats
            self.daily_statistics[converted_date]["num positive clinical"] += num_positive_clinical
            self.daily_statistics[converted_date]["num lab tested"] += num_lab_tested
            self.daily_statistics[converted_date]["num confirmed infected"] += num_confirmed_infected
            self.daily_statistics[converted_date]["num tested negative"] += num_tested_negative
            self.daily_statistics[converted_date]["DCP tested negative"] += DCP_tested_negative
            self.daily_statistics[converted_date]["surveillance tested negative"] += surveillance_tested_negative

            # define movement control zones, and conduct animal movement where possible
            controlzone_movement_restrictions = controlzone_large_movement_restrictions
            # movement of animals

            if self.job_manager.local_movement_restrictions != []:
                if controlzone_movement_restrictions == None:
                    controlzone_movement_restrictions = unary_union(self.job_manager.local_movement_restrictions)
                else:
                    controlzone_movement_restrictions = unary_union(
                        [
                            controlzone_movement_restrictions,
                            unary_union(self.job_manager.local_movement_restrictions),
                        ]
                    )

            # run animal movements
            # includes reduced movements in certain areas
            # TODO: add in illegal movement
            # TODO: add in a low probability of unreported movement (i.e., movement that can't be traced)
            if resource_setting == "default" or resource_setting == "low":
                movement_reduction_factor = 0.2  # 80% reduction / 20% chance of movement
            elif resource_setting == "high":
                movement_reduction_factor = 0.05  # 95% reduction / 5% chance of movement

            movement_record = animal_movement.animal_movement(
                properties,
                day=self.time,
                controlzone=controlzone_movement_restrictions,
                reduced_movement_zone=control_area,
                movement_reduction_factor=movement_reduction_factor,
                all_movement_reduction_factor=0.8,  # reducing probability of overall movement
            )
            self.movement_records = pd.concat([self.movement_records, movement_record], axis=0, ignore_index=True)

            self.controlzone["movement restrictions"] = controlzone_movement_restrictions  # this is for plotting purposes later
            # update counts of infected/clinical/etc animals on each farm (important too if any animals have moved locations)
            for i, premise in enumerate(properties):
                premise.update_counts()

            # and then go through job queue again in 0.5 time,
            new_combined_narrative, local_movement_restrictions, newly_culled_animals, contacts_for_plotting, stats = self.job_manager.run_jobs(
                self.time + 0.5,
                properties,
                self.movement_records,
                converted_date,
                resource_setting=resource_setting,
            )
            self.combined_narrative.extend(new_combined_narrative)
            self.contacts_for_plotting.update(contacts_for_plotting)
            self.total_culled_animals += newly_culled_animals
            (
                num_positive_clinical,
                num_lab_tested,
                num_confirmed_infected,
                num_tested_negative,
                DCP_tested_negative,
                surveillance_tested_negative,
            ) = stats
            self.daily_statistics[converted_date]["num positive clinical"] += num_positive_clinical
            self.daily_statistics[converted_date]["num lab tested"] += num_lab_tested
            self.daily_statistics[converted_date]["num confirmed infected"] += num_confirmed_infected
            self.daily_statistics[converted_date]["num tested negative"] += num_tested_negative
            self.daily_statistics[converted_date]["DCP tested negative"] += DCP_tested_negative
            self.daily_statistics[converted_date]["surveillance tested negative"] += surveillance_tested_negative

            # update counts of infected/clinical/etc animals on each farm (important too if any animals have moved locations)
            for i, premise in enumerate(properties):
                premise.update_counts()

            # then close off this day
            time_list.append(self.time)
            if self.plotting:
                simulator.plot_current_state(
                    properties,
                    self.time,
                    self.xlims,
                    self.ylims,
                    self.folder_path,
                    self.controlzone,
                    infectionpoly=False,
                    contacts_for_plotting=self.contacts_for_plotting,
                )
                # # should also save things for plotting: i.e., everything that I had used to actually plot
                # with open(os.path.join(self.folder_path, "plotting_data" + str(self.time)), "wb") as file:
                #     pickle.dump(
                #         [properties, self.time, self.xlims, self.ylims, self.controlzone, self.contacts_for_plotting],
                #         file,
                #     )

                self.save_preprocessed_plotting_information(properties)

        with open(os.path.join(self.folder_path, "plotting_data" + str(self.time)), "wb") as file:
            pickle.dump(
                [properties, self.time, self.xlims, self.ylims, self.controlzone, self.contacts_for_plotting],
                file,
            )

        # if self.plotting:
        #     output.make_video(self.folder_path, "map_underlying", times=time_list)
        #     output.make_video(self.folder_path, "map_apparent", times=time_list)

        #  plot more zoomed up versions...
        # NSW closeup
        output.plot_map(
            properties,
            self.time,
            xlims=[140, 154],
            ylims=[-38, -28],
            folder_path=self.folder_path,
            real_situation=False,
            controlzone=self.controlzone,
            infectionpoly=False,
            contacts_for_plotting=self.contacts_for_plotting,
            save_suffix="_NSW",
        )

        # QLD closeup
        output.plot_map(
            properties,
            self.time,
            xlims=[137, 154],
            ylims=[-29, -10],
            folder_path=self.folder_path,
            real_situation=False,
            controlzone=self.controlzone,
            infectionpoly=False,
            contacts_for_plotting=self.contacts_for_plotting,
            save_suffix="_QLD",
        )

        # VIC closeup
        output.plot_map(
            properties,
            self.time,
            xlims=[140, 152],
            ylims=[-40, -33],
            folder_path=self.folder_path,
            real_situation=False,
            controlzone=self.controlzone,
            infectionpoly=False,
            contacts_for_plotting=self.contacts_for_plotting,
            save_suffix="_VIC",
        )

        # SA closeup
        output.plot_map(
            properties,
            self.time,
            xlims=[self.xlims[0], 142],
            ylims=[-39, -25],
            folder_path=self.folder_path,
            real_situation=False,
            controlzone=self.controlzone,
            infectionpoly=False,
            contacts_for_plotting=self.contacts_for_plotting,
            save_suffix="_SA",
        )

        simulator.save_outbreak_state(
            properties,
            self.time,
            self.folder_path,
            self.unique_output,
            total_culled_animals=self.total_culled_animals,
            movement_records=self.movement_records,
            job_manager=self.job_manager,
        )

        animal_movement.save_movement_record(self.folder_path, self.movement_records)
        self.save_reports(properties, restricted_area, control_area)
        self.job_manager.save_jobs_queue(self.folder_path)
        self.save_daily_statistics()

        # TODO: add in a "total" column? or add in relative costs/estimated costs and a total estimated cost...
        self.job_manager.calculate_resources_used(self.folder_path)

        dates_list = [premises.convert_time_to_date(t) for t in range(self.first_detection_day, self.time + 1)]
        # print(dates_list)
        daily_notifs = [0] * len(dates_list)

        for property_i in properties:
            notif_date = property_i.notification_date
            if notif_date != "NA":
                index = dates_list.index(notif_date)
                daily_notifs[index] += 1

        save_name = "daily_notifications"

        output.plot_daily_notifications_over_time(dates_list, daily_notifs, self.folder_path, save_name)

        output.plot_total_notifs_over_time(dates_list, daily_notifs, self.folder_path, save_name="total_notifs")

        daily_notifs_by_state = {}
        for property_i in properties:
            notif_date = property_i.notification_date
            if notif_date != "NA":
                if property_i.state not in daily_notifs_by_state:
                    daily_notifs_by_state[property_i.state] = [0] * len(dates_list)
                index = dates_list.index(notif_date)
                daily_notifs_by_state[property_i.state][index] += 1
        for state in daily_notifs_by_state.keys():
            output.plot_daily_notifications_over_time(dates_list, daily_notifs_by_state[state], self.folder_path, "daily_notifs_" + state)
            output.plot_total_notifs_over_time(dates_list, daily_notifs_by_state[state], self.folder_path, save_name="total_notifs_" + state)

        return properties, self.movement_records, self.time, self.total_culled_animals, self.job_manager

    def update_negative_status_based_on_zones(facility, restricted_area, control_area):
        if facility.polygon.intersects(restricted_area):
            facility.status = "ARP"  # at risk premises
        elif facility.polygon.intersects(control_area):
            # if it contains chickens -> POR -> Premises of relevance
            if facility.get_num_chickens() > 0 or facility.get_num_eggs() > 0 or facility.get_num_fertilised_eggs() > 0:
                facility.status = "POR"
            else:
                facility.status = "ZP"
        else:
            facility.status = "NA"

    def update_status_based_on_zones(self, properties, restricted_area, control_area, converted_date):
        # TODO could probably make this better (like everything else)
        higher_priority_statuses = ["IP", "DCP", "TP", "SP", "DCPF", "RP"]

        for facility in properties:
            if facility.polygon.intersects(restricted_area):  # restricted area is the tighter one
                if facility.status not in higher_priority_statuses:
                    OG_status = facility.status
                    facility.status = "ARP"  # at risk premises
                    if facility.case_id == None:
                        self.case_id_counter += 1
                        facility.case_id = self.case_id_counter

                    if OG_status != facility.status:
                        self.combined_narrative.append(
                            [
                                self.time,
                                converted_date,
                                "status_update",
                                facility.id,
                                f"{facility.type} (sim_id {facility.id}) has updated status: {facility.status} due to being in an RA and containing susceptible animal(s) (prior status: {OG_status})",
                                facility.case_id,
                            ]
                        )
            elif facility.polygon.intersects(control_area):  # control area is the disease free buffer
                if facility.status not in higher_priority_statuses:
                    # if it contains chickens -> POR -> Premises of relevance
                    if (
                        (facility.known_birds != "" and facility.known_birds > 0)
                        or facility.get_num_eggs() > 0
                        or facility.get_num_fertilised_eggs() > 0
                    ):
                        OG_status = facility.status

                        if facility.case_id == None:
                            self.case_id_counter += 1
                            facility.case_id = self.case_id_counter

                        facility.status = "POR"
                        if OG_status != facility.status:
                            self.combined_narrative.append(
                                [
                                    self.time,
                                    converted_date,
                                    "status_update",
                                    facility.id,
                                    f"{facility.type} (sim_id {facility.id}) has updated status: {facility.status} due to being in an CA and containing susceptible animal(s) (prior status: {OG_status})",
                                    facility.case_id,
                                ]
                            )

                    elif facility.known_birds != "" and facility.known_birds == 0:
                        OG_status = facility.status
                        if facility.case_id == None:
                            self.case_id_counter += 1
                            facility.case_id = self.case_id_counter
                        facility.status = "ZP"
                        if OG_status != facility.status:
                            self.combined_narrative.append(
                                [
                                    self.time,
                                    converted_date,
                                    "status_update",
                                    facility.id,
                                    f"{facility.type} (sim_id {facility.id}) has updated status: {facility.status} due to being in an CA with zero susceptible animals (prior status: {OG_status})",
                                    facility.case_id,
                                ]
                            )
                    elif facility.data_source != "":
                        OG_status = facility.status
                        facility.status = "UP"
                        if facility.case_id == None:
                            self.case_id_counter += 1
                            facility.case_id = self.case_id_counter
                        if OG_status != facility.status:
                            self.combined_narrative.append(
                                [
                                    self.time,
                                    converted_date,
                                    "status_update",
                                    facility.id,
                                    f"{facility.type} (sim_id {facility.id}) has updated status: {facility.status} due to being in an CA with unknown animal status (prior status: {OG_status})",
                                    facility.case_id,
                                ]
                            )
                    # else - we don't know about it, so we can't assign it any particular status!

    def simulate_HPAI_outbreak_management(
        self,
        properties,
        property_jobs,
        zones_based_jobs,
        property_based_zones,
        days_to_run_for,
        outbreak_sim="HPAI",
        time=None,
        restricted_emergency_zone=None,
        control_emergency_zone=None,
        output_suffix="",
    ):

        if time != None:
            self.time = time
        if self.folder_path == "":
            raise Warning("Default folder path hasn't changed - recommend that set_plotting_parameters() be run first")

        time_list = []
        stop_time = self.time + days_to_run_for

        while self.time < stop_time:
            self.time += 1
            converted_date = premises.convert_time_to_date(self.time)
            self.daily_statistics[converted_date] = {
                "num self-reported": 0,
                "num positive clinical": 0,
                "num lab tested": 0,
                "num confirmed infected": 0,
                "num tested negative": 0,
                "DCP tested negative": 0,
                "surveillance tested negative": 0,
                "culled birds": 0,
                "destroyed eggs": 0,
                "vaccinated birds": 0,
            }

            HPAI_functions.advance_chicken_egg_ages(properties)
            HPAI_functions.egg_production(properties)
            HPAI_functions.finish_cleaning_sheds(properties, self.time)

            # calculate FOI for each property
            FOI = self.calculate_FOI_for_each_property(properties, outbreak_sim, self.time)

            # check if any property wants to report
            EPS_df = property_based_zones[property_based_zones["zone_type"] == "Enhanced Passive Surveillance"]
            EPS_geo_list = []
            enhanced_reporting_factor = 1
            for i, row in EPS_df.iterrows():

                enhanced_passive_surveillance_area = management.define_control_zone_polygons(
                    properties,
                    [row["ID"]],
                    row["radius_km"],
                    convex=False,
                )  # should be zero movement
                EPS_geo_list.append(enhanced_passive_surveillance_area)
                if isinstance(row["zone_parameter"], float):
                    enhanced_reporting_factor = row["zone_parameter"]
                elif row["zone_parameter"].isnull() and enhanced_reporting_factor == 1:
                    enhanced_reporting_factor = 2
                else:
                    pass

            enhanced_passive_surveillance_area = unary_union(EPS_geo_list)

            for i, facility in enumerate(properties):
                if facility.polygon.intersects(enhanced_passive_surveillance_area):
                    increased_reporting_factor = enhanced_reporting_factor
                else:
                    increased_reporting_factor = 1

                if facility.type == "backyard":
                    reporting_probability = self.prob_report_backyard
                else:
                    reporting_probability = self.prob_report_commercial

                if (
                    not facility.culled_status
                    and not facility.reported_status
                    and (facility.status not in ["SP", "DCP", "IP"])  # self reported status
                    and facility.prob_of_reporting_only(
                        self.clinical_reporting_threshold, reporting_probability * increased_reporting_factor
                    )  # TODO: this is the place to add in false positives
                ):
                    self.make_report(facility, converted_date, i)
                    self.daily_statistics[converted_date]["num self-reported"] += 1

            # run infection model for each property
            properties = self.run_infection_model_for_each_property(properties, FOI)

            # get control zones - TODO - should move this out of the disease simulation component??? and just input in restricted area and control area directly
            RA_df = property_based_zones[property_based_zones["zone_type"] == "RA"]
            RA_geo_list = []
            for i, row in RA_df.iterrows():

                restricted_area = management.define_control_zone_polygons(
                    properties,
                    [row["ID"]],
                    row["radius_km"],
                    convex=False,
                )  # should be zero movement
                RA_geo_list.append(restricted_area)
            if restricted_emergency_zone != None:
                RA_geo_list.append(restricted_emergency_zone)

            restricted_area = unary_union(RA_geo_list)

            CA_df = property_based_zones[property_based_zones["zone_type"] == "CA"]
            CA_geo_list = []
            for i, row in CA_df.iterrows():

                control_area = management.define_control_zone_polygons(
                    properties,
                    [row["ID"]],
                    row["radius_km"],
                    convex=False,
                )  # should be zero movement
                CA_geo_list.append(control_area)
            if control_emergency_zone != None:
                CA_geo_list.append(control_emergency_zone)

            control_area = unary_union(CA_geo_list)

            self.controlzone["restricted area"] = restricted_area
            self.controlzone["control area"] = control_area

            # update statuses based on the zones
            self.update_status_based_on_zones(properties, restricted_area, control_area, converted_date)
            contacts_for_plotting = {}

            ################################################################################################################################
            # MANAGEMENT ACTIONS
            print(converted_date)
            converted_date_dt = dt.strptime(converted_date, "%d/%m/%Y")
            # Specific property actions
            for i, row in property_jobs.iterrows():

                if row["date_scheduled"] == converted_date or row["date_scheduled"] == converted_date_dt:
                    print(row)
                    job_type = row["action"]
                    property_index = row["ID"]
                    if job_type == "LabTesting":
                        testing_report, positive = self.job_manager.conduct_labtesting(properties, property_index, self.time)
                        full_testing_report = [self.time, converted_date, "test", property_index, testing_report, properties[property_index].case_id]
                        self.combined_narrative.append(full_testing_report)

                        DCP_status = False
                        if properties[property_index].status == "DCP":
                            DCP_status = True

                        self.daily_statistics[converted_date]["num lab tested"] += 1
                        premise = properties[property_index]
                        premise.day_of_last_lab_test = self.time
                        properties[property_index].custom_info["last_PCR_date"] = converted_date

                        if positive:
                            self.daily_statistics[converted_date]["num confirmed infected"] += 1
                            properties[property_index].custom_info["infection_data_known"] = True
                            OG_status = properties[property_index].status
                            # report property
                            premise_report = premise.report_only(self.time, next(self.notified_iter))  # updates status to IP
                            self.combined_narrative.append([self.time, converted_date, "report", property_index, premise_report, premise.case_id])

                            self.combined_narrative.append(
                                [
                                    self.time,
                                    converted_date,
                                    "status_update",
                                    properties[property_index].id,
                                    f"{properties[property_index].type} (sim_id {properties[property_index].id}) has updated status: {properties[property_index].status} (prior status: {OG_status})",
                                    properties[property_index].case_id,
                                ]
                            )

                            properties[property_index].custom_info["PCR_result"] = "positive"
                        else:
                            self.daily_statistics[converted_date]["num tested negative"] += 1
                            properties[property_index].custom_info["PCR_result"] = "negative"

                            if DCP_status:
                                self.daily_statistics[converted_date]["DCP tested negative"] += 1

                            else:
                                self.daily_statistics[converted_date]["surveillance tested negative"] += 1

                            # updating status
                            # OG_status = properties[property_index].status
                            # properties[property_index].status = properties[property_index].status + "-AN"  # assessed negative
                            # self.combined_narrative.append(
                            #     [
                            #         self.time,
                            #         converted_date,
                            #         "status_update",
                            #         properties[property_index].id,
                            #         f"{properties[property_index].type} (sim_id {properties[property_index].id}) has updated status: {properties[property_index].status} (prior status: {OG_status})",
                            #         properties[property_index].case_id,
                            #     ]
                            # )

                            # self.update_negative_status_based_on_zones(properties[property_index], restricted_area, control_area)

                        extra_job_info = testing_report

                    elif job_type == "ClinicalObservation":
                        if properties[property_index].case_id == None:
                            self.case_id_counter += 1
                            properties[property_index].case_id = self.case_id_counter

                        testing_report, positive = self.job_manager.conduct_clinicalobservation(properties, property_index, self.time)
                        self.combined_narrative.append(
                            [self.time, converted_date, "test", property_index, testing_report, properties[property_index].case_id]
                        )

                        properties[property_index].custom_info["property_data_known"] = True
                        properties[property_index].data_source = "farm inspection"
                        properties[property_index].known_sheds = properties[property_index].num_sheds
                        if not (properties[property_index].type in ["egg processing", "abbatoir", "backyard"]):
                            properties[property_index].known_area = properties[property_index].area
                            properties[property_index].known_birds = properties[property_index].get_num_chickens()
                        if properties[property_index].type == "backyard":
                            properties[property_index].known_birds = properties[property_index].get_num_chickens()

                        properties[property_index].custom_info["last_surveillance_date"] = converted_date

                        if positive:
                            self.daily_statistics[converted_date]["num positive clinical"] += 1
                            properties[property_index].custom_info["animals_clinical"] = True
                            OG_status = properties[property_index].status
                            if OG_status not in ["IP", "SP", "RP"]:
                                properties[property_index].status = "SP"
                                self.combined_narrative.append(
                                    [
                                        self.time,
                                        converted_date,
                                        "status_update",
                                        properties[property_index].id,
                                        f"{properties[property_index].type} (sim_id {properties[property_index].id}) has updated status: {properties[property_index].status} due to positive clinical signs (prior status: {OG_status})",
                                        properties[property_index].case_id,
                                    ]
                                )
                        else:
                            properties[property_index].custom_info["animals_clinical"] = False
                            OG_status = properties[property_index].status
                            properties[property_index].status = "DCP"
                            self.combined_narrative.append(
                                [
                                    self.time,
                                    converted_date,
                                    "status_update",
                                    properties[property_index].id,
                                    f"{properties[property_index].type} (sim_id {properties[property_index].id}) has updated status: {properties[property_index].status} due to negative clinical signs (prior status: {OG_status})",
                                    properties[property_index].case_id,
                                ]
                            )

                        extra_job_info = testing_report
                    elif job_type == "Surveillance":
                        if isinstance(row["detection_prob"], float):
                            detection_prob = row["detection_prob"]
                        else:
                            if row["specific_action"] == "Phone Surveillance":
                                if properties[property_index].type == "backyard":
                                    detection_prob = 0.95 * 0.5
                                else:
                                    detection_prob = 0.95 * 0.95
                            elif row["specific_action"] == "Field Surveillance":
                                detection_prob = 0.95
                            elif row["specific_action"] == "Self-reporting Surveillance":
                                if properties[property_index].type == "backyard":
                                    detection_prob = 0.95 * 0.45
                                else:
                                    detection_prob = 0.95 * 0.90
                            else:
                                raise ValueError(f"{row['specific_action']} not expected")

                        # TODO : something complicated here about being able to select sick birds and identifying that visually
                        number_infected_on_property = properties[property_index].number_infected
                        prop_clinical = properties[property_index].prop_clinical

                        testing_report, positive = management.test_property(
                            properties, property_index, self.time, test_sensitivity=detection_prob, test_type=row["specific_action"]
                        )

                        if positive:  #  and row["specific_action"] in ["Field Surveillance", "Phone Surveillance"]:
                            properties[property_index].clinical_report_outcome = True

                        if properties[property_index].case_id == None:
                            self.case_id_counter += 1
                            properties[property_index].case_id = self.case_id_counter

                        self.combined_narrative.append(
                            [self.time, converted_date, "surveillance", property_index, testing_report, properties[property_index].case_id]
                        )

                        properties[property_index].custom_info["property_data_known"] = True
                        properties[property_index].data_source = row["specific_action"]
                        properties[property_index].known_sheds = properties[property_index].num_sheds
                        if not (properties[property_index].type in ["egg processing", "abbatoir", "backyard"]):
                            properties[property_index].known_area = properties[property_index].area
                            properties[property_index].known_birds = properties[property_index].get_num_chickens()
                        if properties[property_index].type == "backyard":
                            properties[property_index].known_birds = properties[property_index].get_num_chickens()

                        properties[property_index].custom_info["last_surveillance_date"] = converted_date

                        if positive:
                            self.daily_statistics[converted_date]["num positive clinical"] += 1
                            properties[property_index].custom_info["animals_clinical"] = True
                            OG_status = properties[property_index].status
                            if OG_status not in ["IP", "SP", "RP"]:
                                properties[property_index].status = "SP"
                                self.combined_narrative.append(
                                    [
                                        self.time,
                                        converted_date,
                                        "status_update",
                                        properties[property_index].id,
                                        f"{properties[property_index].type} (sim_id {properties[property_index].id}) has updated status: {properties[property_index].status} due to positive clinical signs (prior status: {OG_status})",
                                        properties[property_index].case_id,
                                    ]
                                )
                        else:
                            properties[property_index].custom_info["animals_clinical"] = False
                            OG_status = properties[property_index].status
                            self.daily_statistics[converted_date]["surveillance tested negative"] += 1
                            if OG_status in ["SP", "TP"]:
                                properties[property_index].status = "DCP"
                                self.combined_narrative.append(
                                    [
                                        self.time,
                                        converted_date,
                                        "status_update",
                                        properties[property_index].id,
                                        f"{properties[property_index].type} (sim_id {properties[property_index].id}) has updated status: {properties[property_index].status} due to negative clinical signs (prior status: {OG_status})",
                                        properties[property_index].case_id,
                                    ]
                                )
                            else:
                                print(f"OG status of a property in negative surveillance job: {OG_status}")

                        extra_job_info = testing_report
                        job_type = row["specific_action"]

                    elif job_type == "Cull":
                        num_animals_to_cull = int(row["num"])

                        facility = properties[property_index]
                        facility.custom_info["last_cull_date"] = converted_date

                        num_eggs = properties[property_index].get_num_eggs() + properties[property_index].get_num_fertilised_eggs()
                        if num_eggs > 0:
                            if "destroyed_eggs" in properties[property_index].custom_info:
                                properties[property_index].custom_info["destroyed_eggs"] += num_eggs
                            else:
                                properties[property_index].custom_info["destroyed_eggs"] = num_eggs
                            properties[property_index].eggs = 0
                            for shed_i, shed_info in facility.sheds.items():
                                if "eggs" in shed_info:
                                    shed_info["eggs"] = []  # removing fertlised eggs from existence

                        num_chickens_left = properties[property_index].get_num_chickens()
                        if num_chickens_left <= num_animals_to_cull:
                            # cull everything
                            for shed_i, shed_info in facility.sheds.items():
                                if "chickens" in shed_info:
                                    shed_info["chickens"] = []  # removing them from existence
                                    # TODO: technically could set the sheds to "clean"

                            if "culled_birds" in properties[property_index].custom_info:
                                properties[property_index].custom_info["culled_birds"] += num_chickens_left
                            else:
                                properties[property_index].custom_info["culled_birds"] = num_chickens_left

                            newly_culled_animals = num_chickens_left
                            properties[property_index].known_birds = properties[property_index].known_birds - num_chickens_left
                        else:
                            # there are more chickens than capacity to cull
                            chickens_left_to_cull_today = num_animals_to_cull
                            newly_culled_animals = num_animals_to_cull

                            if "culled_birds" in properties[property_index].custom_info:
                                properties[property_index].custom_info["culled_birds"] += num_animals_to_cull
                            else:
                                properties[property_index].custom_info["culled_birds"] = num_animals_to_cull

                            # calling this function actually "pops" out the chickens for us
                            chickens_to_cull = HPAI_functions.chickens_to_cull(properties, property_index, self.time, chickens_left_to_cull_today)

                            properties[property_index].known_birds = properties[property_index].get_num_chickens()

                        premise_report = f"DAY {converted_date} - {facility.type} (sim_id {facility.id}), case_id {facility.case_id} {facility.status}, IP {facility.ip}) at ({round(facility.x,2)}, {round(facility.y,2)}), {facility.get_location()}: \nA total of {newly_culled_animals} animal(s) have been culled and {num_eggs} egg(s) destroyed."
                        self.combined_narrative.append([self.time, converted_date, "cull", property_index, premise_report, facility.case_id])

                        if facility.get_num_chickens() == 0:
                            facility.culled_status = 1
                            facility.removal_date = converted_date
                            facility.infection_status = 0
                            OG_status = facility.status
                            facility.status = "RP"
                            self.combined_narrative.append(
                                [
                                    self.time,
                                    converted_date,
                                    "status_update",
                                    properties[property_index].id,
                                    f"{properties[property_index].type} (sim_id {properties[property_index].id}) has updated status: {properties[property_index].status} (prior status: {OG_status})",
                                    properties[property_index].case_id,
                                ]
                            )

                        self.total_culled_animals += newly_culled_animals
                        self.daily_statistics[converted_date]["culled birds"] += newly_culled_animals
                        self.daily_statistics[converted_date]["destroyed eggs"] += num_eggs

                        extra_job_info = f"{newly_culled_animals} chickens culled, {num_eggs} eggs destroyed"
                        if facility.infection_status == 0:
                            extra_job_info += "; culling on property complete"

                    elif job_type == "ContactTracing":
                        contact_tracing_report, traced_property_indices = management.contact_tracing(
                            properties, property_index, self.movement_records, self.time
                        )
                        self.combined_narrative.append(
                            [self.time, converted_date, "tracing", property_index, contact_tracing_report, properties[property_index].case_id]
                        )

                        properties[property_index].custom_info["last_conducted_contact_tracing"] = converted_date

                        contacts_for_plotting[property_index] = traced_property_indices

                        for t_i in traced_property_indices:
                            OG_status = properties[t_i].status
                            if OG_status not in ["IP", "DCP", "TP", "SP", "DCPF", "RP"]:
                                properties[t_i].status = "TP"
                                self.combined_narrative.append(
                                    [
                                        self.time,
                                        converted_date,
                                        "status_update",
                                        properties[t_i].id,
                                        f"{properties[t_i].type} (sim_id {properties[t_i].id}) has updated status: {properties[t_i].status} (prior status: {OG_status})",
                                        properties[t_i].case_id,
                                    ]
                                )
                            if properties[t_i].case_id == None:
                                self.case_id_counter += 1
                                properties[t_i].case_id = self.case_id_counter
                                self.combined_narrative.append(
                                    [
                                        self.time,
                                        converted_date,
                                        "status_update",
                                        properties[t_i].id,
                                        f"{properties[t_i].type} (sim_id {properties[t_i].id}) has been assigned case id {properties[t_i].case_id} {properties[t_i].status}",
                                        properties[t_i].case_id,
                                    ]
                                )
                            if properties[t_i].data_source == "":
                                properties[t_i].data_source = "tracing"  # for e.g. backyard premises

                        extra_job_info = contact_tracing_report

                    elif job_type == "Vaccination":
                        num_animals_to_vaccinate = int(row["num"])
                        total_animals = properties[property_index].get_num_chickens()
                        properties[property_index].custom_info["last_vaccination_date"] = converted_date

                        if properties[property_index].case_id == None:
                            self.case_id_counter += 1
                            properties[property_index].case_id = self.case_id_counter
                            self.combined_narrative.append(
                                [
                                    self.time,
                                    converted_date,
                                    "status_update",
                                    properties[property_index].id,
                                    f"{properties[property_index].type} (sim_id {properties[property_index].id}) has been assigned case id {properties[property_index].case_id} {properties[property_index].status}; vaccination in progress",
                                    properties[property_index].case_id,
                                ]
                            )

                        # do this if there is a parameter input
                        if isinstance(row["detection_prob"], float):
                            self.set_vax_modifier(row["detection_prob"])

                        if num_animals_to_vaccinate >= total_animals:
                            properties[property_index].vaccinate(self.time)
                            if "vaccinated_birds" in properties[property_index].custom_info:
                                properties[property_index].custom_info["vaccinated_birds"] += total_animals
                            else:
                                properties[property_index].custom_info["vaccinated_birds"] = total_animals

                            self.daily_statistics[converted_date]["vaccinated birds"] += total_animals

                            num_animals_to_vaccinate = total_animals
                        else:
                            proportion_vaccinated = num_animals_to_vaccinate / total_animals
                            properties[property_index].vaccination_status = properties[property_index].vaccination_status + proportion_vaccinated

                            if "vaccinated_birds" in properties[property_index].custom_info:
                                properties[property_index].custom_info["vaccinated_birds"] += num_animals_to_vaccinate
                            else:
                                properties[property_index].custom_info["vaccinated_birds"] = num_animals_to_vaccinate

                            if properties[property_index].vaccination_status >= 1.0:
                                properties[property_index].vacc_date = converted_date

                            self.daily_statistics[converted_date]["vaccinated birds"] += num_animals_to_vaccinate

                        premise_report = f"DAY {converted_date} - {properties[property_index].type} (sim_id {properties[property_index].id}), case_id {properties[property_index].case_id} {properties[property_index].status}, IP {properties[property_index].ip}) at ({round(properties[property_index].x,2)}, {round(properties[property_index].y,2)}), {properties[property_index].get_location()}: \nA total of {num_animals_to_vaccinate} birds have been vaccinated."
                        self.combined_narrative.append([self.time, converted_date, "vaccination", property_index, premise_report, facility.case_id])

                        extra_job_info = f"{num_animals_to_vaccinate} chickens vaccinated"
                        if properties[property_index].vaccination_status >= 1.0:
                            extra_job_info += "; vaccination on property complete"

                            OG_status = properties[property_index].status
                            if OG_status == "NA":
                                properties[property_index].status = "VN"
                                self.combined_narrative.append(
                                    [
                                        self.time,
                                        converted_date,
                                        "status_update",
                                        properties[property_index].id,
                                        f"{properties[property_index].type} (sim_id {properties[property_index].id}) has updated status: {properties[property_index].status} due to vaccination (prior status: {OG_status})",
                                        properties[t_i].case_id,
                                    ]
                                )

                    if job_type not in self.job_manager.jobs_queue[property_index]:
                        self.job_manager.jobs_queue[property_index][job_type] = {}
                    self.job_manager.jobs_queue[property_index][job_type][str(self.time)] = [
                        "complete",
                        converted_date,
                        extra_job_info,
                    ]

            property_jobs = property_jobs.loc[property_jobs["date_scheduled"] != converted_date_dt]

            ######## Zone-based actions
            # Population-level surveillance: mortality sampling of known premises in the area
            population_level_surveillance_df = zones_based_jobs[zones_based_jobs["action"] == "Population-level Surveillance"]
            for i, row in population_level_surveillance_df.iterrows():

                if row["date_scheduled"] == converted_date_dt or row["date_scheduled"] == converted_date:

                    population_level_surveillance = management.define_control_zone_polygons(
                        properties,
                        [row["ID"]],
                        row["radius_km"],
                        convex=False,
                    )  # should be zero movement
                    population_surveillance_ref = row["zone_name"]
                    PCR_detection_probability = 0.98
                    if isinstance(row["zone_parameter"], float) or isinstance(row["zone_parameter"], int):
                        detection_probability_factor = row["zone_parameter"]
                    else:
                        detection_probability_factor = PCR_detection_probability

                    total_num_infected_birds_in_zone = 0
                    total_num_birds_in_zone = 0
                    facility_indices_included = []
                    for i, facility in enumerate(properties):
                        if (
                            (not facility.culled_status)
                            and (not facility.reported_status)
                            and (facility.status not in ["SP", "IP"])
                            and facility.data_source != ""
                            and facility.polygon.intersects(population_level_surveillance)
                        ):
                            total_num_infected_birds_in_zone += facility.prop_infectious * facility.size
                            total_num_birds_in_zone += facility.size
                            facility_indices_included.append(i)

                            # properties[i].custom_info["last_surveillance_date"] = converted_date # not sure about this
                    dead_birds_est = int(total_num_infected_birds_in_zone * 0.95)  # high mortality
                    positive = False
                    if total_num_birds_in_zone != 0:
                        estimated_normal_dead_birds = total_num_birds_in_zone * 0.1
                        est_infected_dead_birds = dead_birds_est / (dead_birds_est + estimated_normal_dead_birds)

                        if est_infected_dead_birds > 0:
                            probability_of_detection = est_infected_dead_birds * detection_probability_factor
                            if np.random.rand() < probability_of_detection:
                                positive = True

                    testing_report = f"DAY {converted_date} - Population-level Surveillance ({population_surveillance_ref}) report: "
                    if positive:
                        testing_report += f"PCR testing of dead birds reports POSITIVE for HPAI - included sim_ids {facility_indices_included}"

                        self.combined_narrative.append([self.time, converted_date, "surveillance", "", testing_report, ""])

                        for i in facility_indices_included:
                            if properties[i].case_id == None:
                                self.case_id_counter += 1
                                properties[i].case_id = self.case_id_counter

                            # testing_report += f"\n {premise.type}, sim_id {property_index}, case_id {premise.case_id} {premise.status}"
                            property_testing_report = f"DAY {converted_date} - POSITIVE detection for HPAI in population-level surveillance ({population_surveillance_ref}) PCR testing that included this property ({properties[i].type}, sim_id {i}, case_id {properties[i].case_id} {properties[i].status})"
                            self.combined_narrative.append(
                                [self.time, converted_date, "surveillance", i, property_testing_report, properties[i].case_id]
                            )
                            OG_status = properties[i].status
                            if OG_status not in ["SP", "TP", "IP"]:
                                properties[i].status = "DCP"
                                self.combined_narrative.append(
                                    [
                                        self.time,
                                        converted_date,
                                        "status_update",
                                        properties[i].id,
                                        f"{properties[i].type} (sim_id {properties[i].id}) has updated status: {properties[i].status} due to positive HPAI PCR in population-level surveillance testing (mortality sampling) (prior status: {OG_status})",
                                        properties[i].case_id,
                                    ]
                                )
                            else:
                                print(f"OG status of property after positive population level testing was {OG_status}")
                    else:
                        testing_report += f"PCR testing of dead birds reports NEGATIVE for HPAI - included sim_ids {facility_indices_included}"
                        self.combined_narrative.append([self.time, converted_date, "surveillance", "", testing_report, ""])

                    extra_job_info = testing_report

                    if "NA" not in self.job_manager.jobs_queue:
                        self.job_manager.jobs_queue["NA"] = {}
                    if row["action"] not in self.job_manager.jobs_queue["NA"]:
                        self.job_manager.jobs_queue["NA"][row["action"]] = {}

                    self.job_manager.jobs_queue["NA"][row["action"]][str(self.time)] = [
                        "complete",
                        converted_date,
                        extra_job_info,
                    ]

            # Wild-animal surveillance: mortality sampling of wild animals in the area
            wild_animal_surveillance_df = zones_based_jobs[zones_based_jobs["action"] == "Wild Animal Surveillance"]
            for i, row in wild_animal_surveillance_df.iterrows():

                if row["date_scheduled"] == converted_date_dt or row["date_scheduled"] == converted_date:

                    wild_animal_surveillance = management.define_control_zone_polygons(
                        properties,
                        [row["ID"]],
                        row["radius_km"],
                        convex=False,
                    )
                    surveillance_ref = row["zone_name"]

                    # TODO - implement this "properly" with an FOI
                    # PCR_detection_probability = 0.9
                    if isinstance(row["zone_parameter"], float) or isinstance(row["zone_parameter"], int):
                        detection_probability_factor = row["zone_parameter"]
                    else:
                        detection_probability_factor = 0.3  # PCR_detection_probability

                    total_num_infected_birds_in_zone = 0
                    total_num_birds_in_zone = 0
                    facility_indices_included = []
                    for i, facility in enumerate(properties):
                        if (
                            (not facility.culled_status)
                            and (not facility.reported_status)
                            and (facility.status not in ["SP", "IP"])
                            and facility.data_source != ""
                            and facility.polygon.intersects(wild_animal_surveillance)
                        ):
                            total_num_infected_birds_in_zone += facility.prop_infectious * facility.size
                            total_num_birds_in_zone += facility.size
                            facility_indices_included.append(i)

                            # properties[i].custom_info["last_surveillance_date"] = converted_date # not sure about this
                    dead_birds_est = int(total_num_infected_birds_in_zone * 0.95)  # high mortality
                    positive = False
                    if total_num_birds_in_zone != 0:
                        est_infected_dead_birds = dead_birds_est / (dead_birds_est + total_num_birds_in_zone * 0.1)

                        if est_infected_dead_birds > 0:
                            probability_of_detection = est_infected_dead_birds * detection_probability_factor
                            if np.random.rand() < probability_of_detection:
                                positive = True

                    testing_report = f"DAY {converted_date} - Wild and free-roaming animal surveillance ({surveillance_ref}) report: "
                    if positive:
                        testing_report += f"PCR testing of dead/sick wild birds reports POSITIVE for HPAI"

                        self.combined_narrative.append([self.time, converted_date, "surveillance", "", testing_report, ""])

                    else:
                        testing_report += f"PCR testing of dead/sick birds reports NEGATIVE for HPAI"
                        self.combined_narrative.append([self.time, converted_date, "surveillance", "", testing_report, ""])

                    extra_job_info = testing_report

                    if "NA" not in self.job_manager.jobs_queue:
                        self.job_manager.jobs_queue["NA"] = {}
                    if row["action"] not in self.job_manager.jobs_queue["NA"]:
                        self.job_manager.jobs_queue["NA"][row["action"]] = {}

                    self.job_manager.jobs_queue["NA"][row["action"]][str(self.time)] = [
                        "complete",
                        converted_date,
                        extra_job_info,
                    ]

            # Environmental surveillance and eDNA
            environmental_surveillance_df = zones_based_jobs[zones_based_jobs["action"] == "Environmental Surveillance"]
            for i, row in environmental_surveillance_df.iterrows():

                if row["date_scheduled"] == converted_date_dt or row["date_scheduled"] == converted_date:

                    surveillance_zone = management.define_control_zone_polygons(
                        properties,
                        [row["ID"]],
                        row["radius_km"],
                        convex=False,
                    )
                    surveillance_ref = row["zone_name"]

                    # TODO - implement this "properly" with an FOI
                    # PCR_detection_probability = 0.9
                    if isinstance(row["zone_parameter"], float) or isinstance(row["zone_parameter"], int):
                        detection_probability_factor = row["zone_parameter"]
                    else:
                        detection_probability_factor = 0.1  # feels like eDNA should be less than PCR

                    total_num_infected_birds_in_zone = 0
                    total_num_birds_in_zone = 0
                    facility_indices_included = []
                    for i, facility in enumerate(properties):
                        if (
                            (not facility.culled_status)
                            and (not facility.reported_status)
                            and (facility.status not in ["SP", "IP"])
                            and facility.data_source != ""
                            and facility.polygon.intersects(surveillance_zone)
                        ):
                            total_num_infected_birds_in_zone += facility.prop_infectious * facility.size
                            total_num_birds_in_zone += facility.size
                            facility_indices_included.append(i)

                            # properties[i].custom_info["last_surveillance_date"] = converted_date # not sure about this
                    dead_birds_est = int(total_num_infected_birds_in_zone * 0.95)  # high mortality
                    positive = False
                    if total_num_birds_in_zone != 0:
                        est_infected_dead_birds = dead_birds_est / (dead_birds_est + total_num_birds_in_zone * 0.1)

                        if est_infected_dead_birds > 0:
                            probability_of_detection = est_infected_dead_birds * detection_probability_factor
                            if np.random.rand() < probability_of_detection:
                                positive = True

                    testing_report = f"DAY {converted_date} - Environmental surveillance and eDNA ({surveillance_ref}) report: "
                    if positive:
                        testing_report += f"Environmental surveillance and eDNA reports POSITIVE for HPAI"

                        self.combined_narrative.append([self.time, converted_date, "surveillance", "", testing_report, ""])

                    else:
                        testing_report += f"Environmental surveillance and eDNA reports NEGATIVE for HPAI"
                        self.combined_narrative.append([self.time, converted_date, "surveillance", "", testing_report, ""])

                    extra_job_info = testing_report

                    if "NA" not in self.job_manager.jobs_queue:
                        self.job_manager.jobs_queue["NA"] = {}
                    if row["action"] not in self.job_manager.jobs_queue["NA"]:
                        self.job_manager.jobs_queue["NA"][row["action"]] = {}

                    self.job_manager.jobs_queue["NA"][row["action"]][str(self.time)] = [
                        "complete",
                        converted_date,
                        extra_job_info,
                    ]

            # Missing Properties Survey
            survey_df = zones_based_jobs[zones_based_jobs["action"] == "Missing Properties Survey"]
            for i, row in survey_df.iterrows():

                if row["date_scheduled"] == converted_date_dt or row["date_scheduled"] == converted_date:

                    surveillance_zone = management.define_control_zone_polygons(
                        properties,
                        [row["ID"]],
                        row["radius_km"],
                        convex=False,
                    )
                    surveillance_ref = row["zone_name"]

                    if isinstance(row["zone_parameter"], float) or isinstance(row["zone_parameter"], int):
                        detection_probability_factor = row["zone_parameter"]
                    else:
                        detection_probability_factor = 1.0  # assuming that we find all properties

                    total_properties_in_zone = 0
                    total_unknown_properties_in_zone = 0
                    for i, facility in enumerate(properties):
                        if facility.polygon.intersects(surveillance_zone):
                            total_properties_in_zone += 1
                            if facility.data_source == "":
                                total_unknown_properties_in_zone += 1
                                facility.data_source = "Missing Properties Survey"

                    testing_report = f"DAY {converted_date} - Missing Properties Survey ({surveillance_ref}) report: {total_properties_in_zone} properties found in zone, with {total_unknown_properties_in_zone} properties previously unrecorded"

                    self.combined_narrative.append([self.time, converted_date, "surveillance", "", testing_report, ""])

                    extra_job_info = testing_report

                    if "NA" not in self.job_manager.jobs_queue:
                        self.job_manager.jobs_queue["NA"] = {}
                    if row["action"] not in self.job_manager.jobs_queue["NA"]:
                        self.job_manager.jobs_queue["NA"][row["action"]] = {}

                    self.job_manager.jobs_queue["NA"][row["action"]][str(self.time)] = [
                        "complete",
                        converted_date,
                        extra_job_info,
                    ]

            self.contacts_for_plotting = contacts_for_plotting

            controlzone_movement_restrictions = restricted_area
            movement_reduction_factor = 0.2  # 80% reduction / 20% chance of movement

            movement_record, number_of_movement_requests = HPAI_functions.animal_movement(
                properties,
                day=self.time,
                controlzone=controlzone_movement_restrictions,
                reduced_movement_zone=control_area,
                movement_reduction_factor=movement_reduction_factor,
                all_movement_reduction_factor=0.8,  # reducing probability of movement in RA and CA
            )
            self.movement_records = pd.concat([self.movement_records, movement_record], axis=0, ignore_index=True)
            self.combined_narrative.append(
                [
                    self.time,
                    converted_date,
                    "movement",
                    "",
                    f"There are {number_of_movement_requests} movement permit requests from premises within the control area",
                    "",
                ]
            )

            self.controlzone["movement restrictions"] = controlzone_movement_restrictions  # this is for plotting purposes later

            # update counts of infected/clinical/etc animals on each farm
            for i, premise in enumerate(properties):
                premise.update_counts()

            # then close off this day
            time_list.append(self.time)
            if self.plotting:
                simulator.plot_current_state(  # TODO - simulator is a weird place to put plotting, probably...
                    properties,
                    self.time,
                    self.xlims,
                    self.ylims,
                    self.folder_path,
                    self.controlzone,
                    infectionpoly=False,
                    contacts_for_plotting=self.contacts_for_plotting,
                    apparent_situation_plot=True,
                )

                self.save_preprocessed_plotting_information(properties)

        with open(os.path.join(self.folder_path, "plotting_data" + str(self.time)), "wb") as file:
            pickle.dump(
                [properties, self.time, self.xlims, self.ylims, self.controlzone, self.contacts_for_plotting],
                file,
            )

        simulator.save_outbreak_state(
            properties,
            self.time,
            self.folder_path,
            self.unique_output,
            total_culled_animals=0,
            movement_records=self.movement_records,
            job_manager=self.job_manager,
        )

        fixed_spatial_setup.save_chicken_property_csv(properties, self.time, self.folder_path, self.unique_output)

        animal_movement.save_movement_record(self.folder_path, self.movement_records)
        self.save_reports(properties, restricted_area, control_area, output_suffix=output_suffix)
        self.job_manager.save_jobs_HPAI(self.folder_path, f"completed_jobs{output_suffix}.csv")
        self.save_daily_statistics(output_suffix=output_suffix)

        self.job_manager.calculate_resources_used(self.folder_path, output_suffix)

        dates_list = [premises.convert_time_to_date(t) for t in range(self.first_detection_day, self.time + 1)]
        # print(dates_list)
        daily_notifs = [0] * len(dates_list)

        for property_i in properties:
            notif_date = property_i.notification_date
            if notif_date != "NA":
                index = dates_list.index(notif_date)
                daily_notifs[index] += 1

        save_name = "daily_notifications"
        output.plot_daily_notifications_over_time(dates_list, daily_notifs, self.folder_path, save_name)

        output.plot_total_notifs_over_time(dates_list, daily_notifs, self.folder_path, save_name="total_notifs")

        output.plot_HPAI_outbreak_apparent(
            properties, restricted_area, control_area, enhanced_passive_surveillance_area, self.xlims, self.ylims, self.folder_path, self.time
        )

        return properties, self.movement_records, self.time, self.total_culled_animals, self.job_manager
