"""Disease Simulator

    Creates a DiseaseSimulator object to run spread simulation

    Typical workflow involves calling:
    * init
    * set_plotting_parameters
    * simulator function of choice... making sure to reset set_plotting_parameters for different parts
        * simulate_outbreak_til_first_report
        * simulate_outbreak_management

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
        self.beta_wind = disease_parameters["beta_wind"]
        self.beta_animal = disease_parameters["beta_animal"]
        self.latent_period = disease_parameters["latent_period"]
        self.infectious_period = disease_parameters["infectious_period"]
        self.preclinical_period = disease_parameters["preclinical_period"]

        self.r_wind = spatial_only_parameters["r_wind"]

        self.clinical_reporting_threshold = scenario_parameters["clinical_reporting_threshold"]
        self.prob_report = scenario_parameters["prob_report"]

        self.vax_modifier = 0  # TODO - can set up a function to input in vaccination-relevant parameters

        self.combined_narrative = ""
        self.contact_tracing_reports = ""
        self.testing_reports = ""
        self.other_reports = ""

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
        self.total_culled_animals = 0
        self.controlzone = {}  # empty control zone
        self.contacts_for_plotting = {}  # empty, as no contact tracing will occur here

    def set_plotting_parameters(self, xlims, ylims, plotting=True, folder_path="", unique_output=""):
        """Sets the plotting parameters, especially important to update regularly if you want things to output to a different folder"""
        self.xlims = xlims
        self.ylims = ylims
        self.plotting = plotting
        self.folder_path = folder_path
        self.unique_output = unique_output

    def save_reports(self, properties):
        """Saves the text reports"""
        total_culled = 0
        total_vaccinated = 0
        for property in properties:
            if property.culled_status:
                total_culled += 1
            if property.vaccination_status:
                total_vaccinated += 1

        to_save_narrative = (
            self.combined_narrative
            + f"\n==============\nTotal culled properties: {total_culled}; total vaccinated properties: {total_vaccinated}; total culled animals: {self.total_culled_animals}"
        )

        # output "reports" report
        with open(os.path.join(self.folder_path, "report.txt"), "w") as file:
            file.write(self.other_reports)

        # output contact tracing reports
        with open(os.path.join(self.folder_path, "report_contact_tracing.txt"), "w") as file:
            file.write(self.contact_tracing_reports)

        # output testing reports
        with open(os.path.join(self.folder_path, "report_testing.txt"), "w") as file:
            file.write(self.testing_reports)

        # output the inter-twined narrative (of known occurences)
        with open(os.path.join(self.folder_path, "report_combined_narrative.txt"), "w") as file:
            file.write(to_save_narrative)

    def simulate_property_reporting(self, properties):
        """Simulates property reporting, outside of the job management system"""
        # Though possible TODO is to actually move this into the job management system (i.e., trigger the "clinical observation positive" knock-on events)

        did_any_properties_report = False

        for i, property_i in enumerate(properties):
            if not property_i.culled_status and property_i.prob_of_reporting_only(
                self.clinical_reporting_threshold, self.prob_report
            ):
                # essentially the same as a positive clinical observation
                did_any_properties_report = True

                report = property_i.report_suspicion(self.time)
                self.other_reports += report
                self.combined_narrative += report

                # enact local movement restrictions around this property, just in case
                self.job_manager.local_movement_restrictions.append(property_i.polygon)
                report = "No movements are now allowed to or from this property.\n"
                self.other_reports += report
                self.combined_narrative += report

                # schedule contact tracing
                s_report = self.job_manager.schedule_contract_tracing(i, self.time)
                self.contact_tracing_reports += s_report
                self.combined_narrative += s_report

                # schedule lab testing
                report = self.job_manager.schedule_lab_testing_after_observation(i, self.time)
                self.other_reports += report  #  TODO should this actually go in testing reports?
                self.combined_narrative += report

                property_i.undergoing_testing = True

        # TODO: should update the JobManager so that I don't have to do this
        for job in self.job_manager.new_jobs:
            self.job_manager.add_job_to_queue(job)
        self.job_manager.new_jobs = []

        return did_any_properties_report

    def simulate_outbreak_spread_only(self, properties, time=None, stop_time=7):
        """Run simulated outbreak, for undetected spread between (self.time (or time parameter if not NA)+1) and (stop_time) [inclusive], with no management"""

        if time != None:
            self.time = time

        if self.folder_path == "":
            raise Warning("Default folder path hasn't changed - recommend that set_plotting_parameters() be run first")

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

        first_report_flag = False

        FOI = list(np.zeros(len(properties)))
        time_list = []
        while first_report_flag == False:
            self.time += 1

            # calculate FOI for each property
            for i, property_i in enumerate(properties):
                if not property_i.culled_status:
                    FOI[i] = SEIR.calculate_force_of_infection(
                        properties, i, self.vax_modifier, self.r_wind, self.beta_wind, self.beta_animal
                    )

            # check if any property wants to report
            did_any_properties_report = self.simulate_property_reporting(properties)
            if did_any_properties_report:
                first_report_flag = True

            # run infection model for each property
            for i, property_i in enumerate(properties):
                property_i.infection_model(
                    self.latent_period, self.infectious_period, self.preclinical_period, FOI[i], self.time
                )

            # movement of animals
            # there may be movement restrictions if a property has reported, so this needs to be checked
            controlzone_movement_restrictions = None
            if self.job_manager.local_movement_restrictions != []:
                controlzone_movement_restrictions = unary_union(self.job_manager.local_movement_restrictions)
                self.controlzone["movement restrictions"] = controlzone_movement_restrictions

            movement_record = animal_movement.trialsimex_animal_movement(
                properties, day=self.time, controlzone=controlzone_movement_restrictions
            )
            if movement_record != []:
                self.movement_records.extend(movement_record)

            # update counts
            for i, property_i in enumerate(properties):
                property_i.update_counts()

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

            # advance time by a half, to see if there are any jobs that should now be complete
            # Go through jobs in the queue
            (
                new_report,
                new_testing_reports,
                new_combined_narrative,
                new_contact_tracing_reports,
                local_movement_restrictions,
                newly_culled_animals,
                contacts_for_plotting,
            ) = self.job_manager.job_manager(self.time + 0.5, properties, self.movement_records)

            self.contacts_for_plotting = contacts_for_plotting
            self.combined_narrative += new_combined_narrative
            self.contact_tracing_reports += new_contact_tracing_reports
            self.testing_reports += new_testing_reports
            self.other_reports += new_report
            self.total_culled_animals += newly_culled_animals

            # movement restrictions might have changed, so control zones may need to be re-calculated
            controlzone_movement_restrictions = None
            if self.job_manager.local_movement_restrictions != []:
                controlzone_movement_restrictions = unary_union(self.job_manager.local_movement_restrictions)
                self.controlzone["movement restrictions"] = controlzone_movement_restrictions

            time_list.append(self.time + 0.5)
            if self.plotting:
                simulator.plot_current_state(
                    properties,
                    self.time + 0.5,
                    self.xlims,
                    self.ylims,
                    self.folder_path,
                    self.controlzone,
                    infectionpoly=False,
                    contacts_for_plotting=self.contacts_for_plotting,
                )
                # should also save things for plotting: i.e., everything that I had used to actually plot
                with open(os.path.join(self.folder_path, "plotting_data" + str(self.time + 0.5)), "wb") as file:
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

        simulator.save_movement_record(self.folder_path, self.movement_records)

        self.save_reports(properties)

        return properties, self.movement_records, self.time, self.total_culled_animals, self.job_manager

    def simulate_outbreak_management(self, properties, management_parameters, days_to_run_for, time=None):
        """Run simulated outbreak with management, for spread starting from self.time+1 for days_to_run_for, with potential management"""

        if time != None:
            self.time = time

        if self.folder_path == "":
            raise Warning("Default folder path hasn't changed - recommend that set_plotting_parameters() be run first")

        FOI = list(np.zeros(len(properties)))
        time_list = []
        stop_time = self.time + days_to_run_for
        nothing_left_to_do = False
        while self.time < stop_time and not nothing_left_to_do:
            self.time += 1
            # calculate FOI for each property
            for i, property_i in enumerate(properties):
                if not property_i.culled_status:
                    FOI[i] = SEIR.calculate_force_of_infection(
                        properties, i, self.vax_modifier, self.r_wind, self.beta_wind, self.beta_animal
                    )

            # go through jobs in the queue
            (
                new_report,
                new_testing_reports,
                new_combined_narrative,
                new_contact_tracing_reports,
                local_movement_restrictions,
                newly_culled_animals,
                contacts_for_plotting,
            ) = self.job_manager.job_manager(self.time + 0.5, properties, self.movement_records)

            self.contacts_for_plotting = contacts_for_plotting
            self.combined_narrative += new_combined_narrative
            self.contact_tracing_reports += new_contact_tracing_reports
            self.testing_reports += new_testing_reports
            self.other_reports += new_report
            self.total_culled_animals += newly_culled_animals

            # conduct any management:

            # first, calculate the properties around which movement restrictions/other policies are enacted
            # TODO: need to think about whether there would be movement restrictions/actions around suspect properties, or only around confirmed properties; currently, it should only be around confirmed properties (i.e., after lab testing)
            source_indices = []
            for i, premise in enumerate(properties):
                if premise.reported_status == True:
                    source_indices.append(i)
            controlzone_large_movement_restrictions = None
            movement_standstill = False
            for management_policy in management_parameters:
                if management_policy["type"] == "movement_standstill":
                    movement_standstill = True
                    map_polygon = {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [self.xlims[0], self.ylims[0]],
                                [self.xlims[1], self.ylims[0]],
                                [self.xlims[1], self.ylims[1]],
                                [self.xlims[0], self.ylims[1]],
                                [self.xlims[0], self.ylims[0]],
                            ]
                        ],
                    }
                    controlzone_large_movement_restrictions = spatial_setup.convert_dict_poly_to_Polygon(map_polygon)
                elif management_policy["type"] == "movement_restriction":
                    if source_indices != []:
                        controlzone_large_movement_restrictions = management.define_control_zone_polygons(
                            properties,
                            source_indices,
                            management_policy["radius_km"],
                            convex=management_policy["convex"],
                        )
                elif management_policy["type"] == "ring_culling":
                    if source_indices != []:
                        controlzone_ring_culling = management.define_control_zone_polygons(
                            properties,
                            source_indices,
                            management_policy["radius_km"],
                            convex=management_policy["convex"],
                        )
                        if "ring culling" in self.controlzone:
                            difference = controlzone_ring_culling.difference(self.controlzone["ring culling"])
                        else:
                            difference = controlzone_ring_culling

                        for property_i in properties:
                            if not (
                                property_i.reported_status or property_i.culled_status
                            ) and property_i.polygon.intersects(difference):
                                premise_report, culled_animals = property_i.cull_without_reporting(self.time)
                                self.total_culled_animals += culled_animals
                                self.other_reports += premise_report
                                self.combined_narrative += premise_report

                        self.controlzone["ring culling"] = controlzone_ring_culling

                elif management_policy["type"] == "ring_testing":
                    # ring testing is probably a combination of clinical observation and lab testing
                    if source_indices != []:
                        controlzone_ring_testing = management.define_control_zone_polygons(
                            properties,
                            source_indices,
                            management_policy["radius_km"],
                            convex=management_policy["convex"],
                        )

                    # if "ring testing" in self.controlzone:
                    #     difference = controlzone_ring_testing.difference(self.controlzone["ring testing"])
                    # else:
                    #     difference = controlzone_ring_testing

                    for i, premise in enumerate(properties):
                        if not (premise.reported_status or premise.culled_status) and premise.polygon.intersects(
                            controlzone_ring_testing
                        ):
                            if premise.day_of_last_lab_test == None or (
                                self.time - premise.day_of_last_lab_test > 13
                            ):  # at least two weeks between testing
                                # clinical observation is immediate
                                job = {
                                    "status": "in progress",
                                    "day": self.time,
                                    "type": management.jobtype.ClinicalObservation,
                                    "property_i": i,
                                }
                                testing_report, positive = self.job_manager.conduct_clinicalobservation(
                                    properties, job, self.time
                                )
                                self.testing_reports += testing_report
                                self.combined_narrative += testing_report

                                # regardless of whether or not it's a positive result

                                # enact local movement restrictions around this property, just in case (will be removed after negative test lab result)
                                self.job_manager.local_movement_restrictions.append(premise.polygon)
                                # TODO there should be a report here, like
                                # report = "No movements are now allowed to or from this property.\n"
                                # new_report += report
                                # new_combined_narrative += report

                                # and regardless of whether or not it's a positive result, schedule lab testing
                                report = self.job_manager.schedule_lab_testing_after_observation(i, self.time)
                                new_report += report
                                new_combined_narrative += report

                                premise.undergoing_testing = True

                                # however, if it is positive, then do contact tracing too
                                if positive:
                                    # schedule contact tracing
                                    report = self.job_manager.schedule_contract_tracing(i, self.time)
                                    self.combined_narrative += report

                    self.controlzone["ring testing"] = controlzone_ring_testing

                elif management_policy["type"] == "ring_vaccination":
                    controlzone_ring_vaccination = management.define_control_zone_polygons(
                        properties,
                        source_indices,
                        management_policy["radius_km"],
                        convex=management_policy["convex"],
                    )

                    if "ring vaccination" in self.controlzone:
                        difference = controlzone_ring_vaccination.difference(self.controlzone["ring vaccination"])
                    else:
                        difference = controlzone_ring_vaccination

                    for premise in properties:
                        if not (premise.reported_status or premise.culled_status) and premise.polygon.intersects(
                            difference
                        ):
                            premise.vaccinate(self.time)

                    self.controlzone["ring vaccination"] = controlzone_ring_vaccination
                else:
                    raise ValueError(
                        f"Management policy type {management_policy['type']} doesn't exist, or is not yet implemented"
                    )

            for job in self.job_manager.new_jobs:
                self.job_manager.add_job_to_queue(job)
            self.job_manager.new_jobs = []

            # check if any property wants to report
            self.simulate_property_reporting(properties)

            # run infection model for each property
            for i, property_i in enumerate(properties):
                property_i.infection_model(
                    self.latent_period, self.infectious_period, self.preclinical_period, FOI[i], self.time
                )

            # movement of animals
            # there may be movement restrictions if a property has reported, so this needs to be checked
            controlzone_movement_restrictions = controlzone_large_movement_restrictions  # this could just be None
            if self.job_manager.local_movement_restrictions != []:
                if controlzone_movement_restrictions == None:
                    controlzone_movement_restrictions = unary_union(self.job_manager.local_movement_restrictions)
                else:
                    controlzone_movement_restrictions = unary_union(
                        [controlzone_movement_restrictions, unary_union(self.job_manager.local_movement_restrictions)]
                    )
            self.controlzone["movement restrictions"] = controlzone_movement_restrictions

            if not movement_standstill:
                movement_record = animal_movement.trialsimex_animal_movement(
                    properties, day=self.time, controlzone=controlzone_movement_restrictions
                )
                if movement_record != []:
                    self.movement_records.extend(movement_record)

            # update counts
            for i, property_i in enumerate(properties):
                property_i.update_counts()

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

            # advance time by a half, to see if there are any jobs that should now be complete
            # Go through jobs in the queue
            (
                new_report,
                new_testing_reports,
                new_combined_narrative,
                new_contact_tracing_reports,
                local_movement_restrictions,
                newly_culled_animals,
                contacts_for_plotting,
            ) = self.job_manager.job_manager(self.time + 0.5, properties, self.movement_records)

            self.contacts_for_plotting = contacts_for_plotting
            self.combined_narrative += new_combined_narrative
            self.contact_tracing_reports += new_contact_tracing_reports
            self.testing_reports += new_testing_reports
            self.other_reports += new_report
            self.total_culled_animals += newly_culled_animals

            # there may have been more confirmations, so control zones may have changed
            # other "active" policies don't happen twice a day
            for management_policy in management_parameters:
                if management_policy["type"] == "movement_restrictions":
                    # calculate the properties around which movement restrictions are enacted
                    # TODO: need to think about whether there would be movement restrictions around suspect properties, or only around confirmed properties; currently, it should only be around confirmed properties (i.e., after lab testing)
                    source_indices = []
                    for i, premise in enumerate(properties):
                        if premise.reported_status == True:
                            source_indices.append(i)

                    if source_indices != []:
                        controlzone_large_movement_restrictions = management.define_control_zone_polygons(
                            properties,
                            source_indices,
                            management_policy["radius_km"],
                            convex=management_policy["convex"],
                        )

            # the local_movement_restrictions might have changed, so re-calculate the control zone for movement
            controlzone_movement_restrictions = controlzone_large_movement_restrictions  # this could just be None
            if self.job_manager.local_movement_restrictions != []:
                if controlzone_movement_restrictions == None:
                    controlzone_movement_restrictions = unary_union(self.job_manager.local_movement_restrictions)
                else:
                    controlzone_movement_restrictions = unary_union(
                        [controlzone_movement_restrictions, unary_union(self.job_manager.local_movement_restrictions)]
                    )
            self.controlzone["movement restrictions"] = controlzone_movement_restrictions

            time_list.append(self.time + 0.5)
            if self.plotting:
                simulator.plot_current_state(
                    properties,
                    self.time + 0.5,
                    self.xlims,
                    self.ylims,
                    self.folder_path,
                    self.controlzone,
                    infectionpoly=False,
                    contacts_for_plotting=self.contacts_for_plotting,
                )
                # should also save things for plotting: i.e., everything that I had used to actually plot
                with open(os.path.join(self.folder_path, "plotting_data" + str(self.time + 0.5)), "wb") as file:
                    pickle.dump(
                        [properties, self.time, self.xlims, self.ylims, self.controlzone, self.contacts_for_plotting],
                        file,
                    )

            # NOTE: taken the following code out, because even if there are no infected properties, there might still be vectors carrying disease
            # check if there are no more infected properties
            # and check if there are no more jobs
            # if len(self.job_manager.jobs_queue) == 0 and len(self.job_manager.new_jobs) == 0:
            # infected_sum = 0
            # for i, premise in enumerate(properties):
            #     if not premise.culled_status:
            #         infected_sum += premise.number_infected
            # if infected_sum >0:
            #     nothing_left_to_do = True

            #     print( f"Job manager queue with no more infection: {len(self.job_manager.jobs_queue)}" )

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

        simulator.save_movement_record(self.folder_path, self.movement_records)

        self.save_reports(properties)

        return properties, self.movement_records, self.time, self.total_culled_animals, self.job_manager
