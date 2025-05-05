""" Management

This script contains several functions used to implement various control actions, including:

    * defining general control zones
    * conducting contact tracing
    * conducting testing.


"""

import geopandas as gpd
import pyproj
from functools import partial
from shapely.geometry import Polygon, Point, LineString, MultiPolygon
from shapely.ops import transform, unary_union
from simulator.premises import convert_time_to_date
import numpy as np
from simulator.spatial_functions import *
from enum import Enum
import warnings
from simulator.premises import convert_time_to_date as convert_time_to_date
import os
import pandas as pd
import random
import shapely

job_types = ["LabTesting", "ClinicalObservation", "Cull", "ContactTracing"]


# TODO should this be moved into the job manager class or into spatial functions?
def define_control_zone_polygons(properties, source_indices, radius_km, convex=False):
    """Creates control zones around properties"""
    list_of_polygons = []

    for i in source_indices:
        # time to puff these polygons up

        poly = properties[i].polygon
        lat = properties[i].coordinates[1]  # y
        lon = properties[i].coordinates[0]  # x
        puff_p1 = geodesic_polygon_buffer(lat, lon, poly, radius_km)
        list_of_polygons.append(puff_p1)

    controlzone = unary_union(list_of_polygons)

    if convex:
        controlzone = controlzone.convex_hull

    return controlzone


# TODO - there should be a more complex version where the zones actually follow LGA borders, i.e., expands out...


# TODO should move this into the job manager, I guess?
def contact_tracing(properties, property_index, movement_records, time):
    """Contact tracing

    Parameters
    ----------
    properties
        list of properties
    property_index : int
        property from which we are tracing
    movement records : dataframe
        dataframe of historical movement records

    """

    contact_tracing_report = f"DAY {convert_time_to_date(time)} - contact tracing report compiled for movements to/from IP {properties[property_index].ip} (ID {properties[property_index].id}) in {properties[property_index].state}\n"
    traced_property_indices = []

    properties_found = False

    timeframe = movement_records.loc[movement_records["day"] >= time - 56]
    forward = timeframe.loc[timeframe["to"] == property_index]
    if not forward.empty:
        properties_found = True
        traced_property_indices.extend(forward["from"].tolist())
        for movement_text in forward["report"].tolist():
            contact_tracing_report = contact_tracing_report + " - " + movement_text + "\n"

    backward = timeframe.loc[timeframe["from"] == property_index]
    if not backward.empty:
        properties_found = True
        traced_property_indices.extend(backward["to"].tolist())
        for movement_text in backward["report"].tolist():
            contact_tracing_report = contact_tracing_report + " - " + movement_text + "\n"

    if not properties_found:
        contact_tracing_report += " - no movements found\n"
    else:
        for t_i in traced_property_indices:
            if properties[t_i].status == "NA":
                properties[t_i].status = "TP"

    return contact_tracing_report, traced_property_indices


def test_property(properties, property_index, time, test_sensitivity, test_type="Lab test"):
    """Conducts a test on a property (could be lab or clinical - the test_sensitivity and test_type can be changed as wished)"""
    # TODO should move this into the job manager, I guess?

    positive = False
    premise = properties[property_index]

    testing_report = f"DAY {convert_time_to_date(time)} - {test_type} report for property index {property_index}: "

    if premise.culled_status:
        testing_report += f"No testing: property index {property_index} (IP {premise.ip}) has already been culled"
    elif premise.infection_status:
        prob_successful = np.random.rand()
        if prob_successful < test_sensitivity:
            x, y = premise.coordinates
            testing_report += (
                f"Property index {property_index} at location (x,y)=({round(x,2)}, {round(y,2)}) report POSITIVE result"
            )
            positive = True
        else:
            testing_report += f"Property index {property_index} report negative result"
    else:
        testing_report += f"Property index {property_index} report negative result"
    return testing_report, positive


class JobManager:
    jobs_queue = {}  # [property_i][job_type][day]=status # TODO: need to refactor  the jobs queue
    new_jobs = []
    local_movement_restrictions = []

    def __init__(
        self,
        n,
        lab_test_sensitivity,
        clinical_test_sensitivity,
        cull_delay=1,
        contact_tracing_delay=0.5,
        lab_test_delay=1.5,
        clinical_delay=0.5,
    ):
        self.lab_test_sensitivity = lab_test_sensitivity
        self.clinical_test_sensitivity = clinical_test_sensitivity
        self.cull_delay = cull_delay
        self.contact_tracing_delay = contact_tracing_delay
        self.lab_test_delay = lab_test_delay
        self.clinical_delay = clinical_delay

        self.jobs_queue = {i: {job_type: {} for job_type in job_types} for i in range(n)}

    def save_jobs_queue(self, folder_path):

        header = ["day_scheduled", "date_scheduled", "property", "job_type", "status", "completion_date"]
        jobs = []
        for property_index in self.jobs_queue.keys():
            for job_type in self.jobs_queue[property_index].keys():
                for day, status in self.jobs_queue[property_index][job_type].items():
                    jobs.append([day, convert_time_to_date(float(day)), property_index, job_type, status[0], status[1]])
        # order by the date
        jobs.sort(key=lambda x: x[0])
        # convert to dataframe
        # save the dataframe
        jobs_df = pd.DataFrame(jobs, columns=header)

        jobs_df.to_csv(os.path.join(folder_path, "jobs_queue.csv"), index=False)

    def conduct_labtesting(self, properties, property_index, time):
        testing_report, positive = test_property(
            properties,
            property_index,
            time,
            self.lab_test_sensitivity,
            test_type="lab test",
        )

        return testing_report, positive

    def conduct_clinicalobservation(self, properties, property_index, time):
        testing_report, positive = test_property(
            properties,
            property_index,
            time,
            self.clinical_test_sensitivity,
            test_type="clinical observation",
        )
        if positive:
            properties[property_index].clinical_report_outcome = True
        else:
            properties[property_index].clinical_report_outcome = False

        return testing_report, positive

    def check_if_recent_job_already_exists(self, property_i, scheduled_day, job_type):
        results_dict = self.jobs_queue[property_i][job_type]

        for day in results_dict.keys():
            if float(day) <= scheduled_day and float(day) >= scheduled_day - 7:
                return True
        return False

    def decision_to_cull(self, property_i, time):
        # TODO - there should be some check that the property hasn't been culled yet...
        # well, the other jobs should also have that check
        scheduled_day = time + self.cull_delay
        job_type = "Cull"

        if self.check_if_recent_job_already_exists(property_i, scheduled_day, job_type) == True:
            report = f"Property {property_i} has already been recently scheduled for depopulation"
        else:
            self.jobs_queue[property_i][job_type][str(scheduled_day)] = ["in progress", "NA"]
            report = f"Property {property_i} has been scheduled for depopulation"

        return report

    def schedule_contract_tracing(self, property_i, time):
        scheduled_day = time + self.contact_tracing_delay
        job_type = "ContactTracing"

        if self.check_if_recent_job_already_exists(property_i, scheduled_day, job_type) == True:
            report = f"Property {property_i} has already been recently scheduled for contact tracing"
        else:
            self.jobs_queue[property_i][job_type][str(scheduled_day)] = ["in progress", "NA"]
            report = f"Property {property_i} has been scheduled for contact tracing"

        return report

    def schedule_lab_testing(self, property_i, time):
        scheduled_day = time + self.lab_test_delay
        job_type = "LabTesting"

        scheduled_successful = False
        if self.check_if_recent_job_already_exists(property_i, scheduled_day, job_type) == True:
            report = f"Property {property_i} has already been recently scheduled for lab testing"
        else:
            self.jobs_queue[property_i][job_type][str(scheduled_day)] = ["in progress", "NA"]
            report = f"Property {property_i} has been scheduled for lab testing"
            scheduled_successful = True

        return report, scheduled_successful

    def schedule_lab_testing_after_observation(self, property_i, time):
        scheduled_day = time + self.lab_test_delay - 0.5
        job_type = "LabTesting"
        scheduled_successful = False
        if self.check_if_recent_job_already_exists(property_i, scheduled_day, job_type) == True:
            report = f"Property {property_i} has already been recently scheduled for lab testing"
        else:
            self.jobs_queue[property_i][job_type][str(scheduled_day)] = ["in progress", "NA"]
            report = f"Property {property_i} has been scheduled for lab testing"
            scheduled_successful = True

        return report, scheduled_successful

    def schedule_clinical_observation(self, property_i, time):
        scheduled_day = time + self.clinical_delay
        job_type = "ClinicalObservation"
        scheduled_successful = False
        if self.check_if_recent_job_already_exists(property_i, scheduled_day, job_type) == True:
            report = f"Property {property_i} has already been recently scheduled for clinical evaluation"
        else:
            self.jobs_queue[property_i][job_type][str(scheduled_day)] = ["in progress", "NA"]
            report = f"Property {property_i} has been scheduled for clinical evaluation"
            scheduled_successful = True

        return report, scheduled_successful

    def run_lab_testing_now(self, properties, property_index, time, converted_date):
        new_combined_narrative = []

        testing_report, positive = self.conduct_labtesting(properties, property_index, time)

        new_combined_narrative.append([time, converted_date, "test", property_index, testing_report])

        DCP_status = False
        if properties[property_index].status == "DCP":
            DCP_status = True

        if positive:
            premise = properties[property_index]

            # report property
            premise_report = premise.report_only(time)
            new_combined_narrative.append([time, converted_date, "report", property_index, premise_report])

            # schedule culling
            report = self.decision_to_cull(property_index, time)
            new_combined_narrative.append([time, converted_date, "cull", property_index, report])

            # enact local movement restrictions around this property, just in case
            self.local_movement_restrictions.append(properties[property_index].polygon)
            new_combined_narrative.append(
                [
                    time,
                    converted_date,
                    "control",
                    property_index,
                    f"No movements are allowed to or from property {property_index} ({properties[property_index].type})",
                ]
            )

            report = self.schedule_contract_tracing(property_index, time)
            new_combined_narrative.append([time, converted_date, "tracing", report])
        else:
            # remove TP status...convert to NA status again for now
            # otherwise, I could shift it to "SP" status if we want to keep track for some reason
            properties[property_index].status = "NA"

            # remove any local movement restrictions
            try:
                self.local_movement_restrictions.remove(properties[property_index].polygon)
                new_combined_narrative.append(
                    [
                        time,
                        converted_date,
                        "control",
                        property_index,
                        f"Local movement restrictions lifted for property {property_index} (other movement controls still in place)",
                    ]
                )
            except:
                warnings.warn("Local polygon doesn't exist in the local movement restrictions for some reason...")

            # may have ongoing surveillance here in the future
        return new_combined_narrative, positive, DCP_status

    def run_jobs(
        self, time, properties, movement_records, converted_date, control_area=None, resource_setting="default"
    ):
        """Run jobs, without prioritisation and without consideration of personel requirements

        THE VERSION WHERE REGARDLESS OF CLINICAL OBSERVATION, lab testing and contact tracing are done anyway

        Parameters
        ----------
        time
            current simulation day
        properties
            list of all the premises objects
        management_parameters : list of dicts
            dictionaries in list define the management type and associated parameters
        movement_records :
            dataframe with historical movements

        Returns
        -------


        """

        total_culled_animals = 0
        contacts_for_plotting = {}  # from property, to properties
        new_combined_narrative = []
        num_positive_clinical = 0
        num_lab_tested = 0
        num_confirmed_infected = 0
        num_tested_negative = 0
        DCP_tested_negative = 0
        surveillance_tested_negative = 0

        # go through the jobs queue & look for "in progress" jobs
        # TODO this probably affects the lab testing of newly DCPs hmm, though maybe that's also fine for now / fix later
        other_jobs_today = []
        culling_jobs_today = []
        jobs_outside_control_area = []  # which will be the first basic prioritisation
        for property_index in self.jobs_queue.keys():
            for job_type in self.jobs_queue[property_index].keys():
                for day, status in self.jobs_queue[property_index][job_type].items():
                    if status[0] == "in progress" and float(day) <= time:
                        if job_type == "Cull":
                            culling_jobs_today.append([property_index, job_type, day, status])
                        else:
                            if control_area != None and not shapely.contains(
                                control_area, Point(properties[property_index])
                            ):
                                jobs_outside_control_area.append([property_index, job_type, day, status])
                            else:
                                other_jobs_today.append([property_index, job_type, day, status])

        total_jobs = len(other_jobs_today) + len(culling_jobs_today) + len(jobs_outside_control_area)

        # TODO : put in some proper prioritisation based on zoning
        if resource_setting == "default":
            # for now, just randomly halve / get a max of say 100 jobs a day / need to be scaled by the number of properties
            max_jobs_today = min(int(total_jobs * 0.7), int(len(properties) / 50), 500) + np.random.randint(
                int(len(properties) / 100)
            )

            if len(jobs_outside_control_area) <= max_jobs_today:
                jobs_today = jobs_outside_control_area
            else:
                jobs_today = random.sample(jobs_outside_control_area, max_jobs_today)

            # should deprioritised culling, which means that the culling number should be kept down (e.g., as a fixed fraction for now)
            # TODO - improve
            extra_culling_jobs = int(0.3 * max_jobs_today)
            if len(culling_jobs_today) > extra_culling_jobs:
                culling_jobs_today = random.sample(culling_jobs_today, extra_culling_jobs)

            extra_other_jobs = int(0.2 * max_jobs_today) + (max_jobs_today - len(jobs_today))
            if extra_other_jobs >= len(other_jobs_today):
                extra_other_jobs_today = other_jobs_today
            else:
                extra_other_jobs_today = random.sample(other_jobs_today, extra_other_jobs)
        elif resource_setting == "high":  # resource values increased randomly...
            # for now, just randomly halve / get a max of say 100 jobs a day / need to be scaled by the number of properties
            max_jobs_today = min(int(total_jobs * 0.8), int(len(properties) / 5), 1000) + np.random.randint(
                int(len(properties) / 30)
            )

            if len(jobs_outside_control_area) <= max_jobs_today:
                jobs_today = jobs_outside_control_area
            else:
                jobs_today = random.sample(jobs_outside_control_area, max_jobs_today)

            # should deprioritised culling, which means that the culling number should be kept down (e.g., as a fixed fraction for now)
            # TODO - improve
            extra_culling_jobs = int(0.5 * max_jobs_today)
            if len(culling_jobs_today) > extra_culling_jobs:
                culling_jobs_today = random.sample(culling_jobs_today, extra_culling_jobs)

            extra_other_jobs = int(0.4 * max_jobs_today) + (max_jobs_today - len(jobs_today))
            if extra_other_jobs >= len(other_jobs_today):
                extra_other_jobs_today = other_jobs_today
            else:
                extra_other_jobs_today = random.sample(other_jobs_today, extra_other_jobs)
        elif resource_setting == "low":  # reducing culling resources

            max_jobs_today = min(int(total_jobs * 0.5), int(len(properties) / 20), 500) + np.random.randint(
                int(len(properties) / 150)
            )

            if len(jobs_outside_control_area) <= max_jobs_today:
                jobs_today = jobs_outside_control_area
            else:
                jobs_today = random.sample(jobs_outside_control_area, max_jobs_today)

            extra_culling_jobs = max(int(0.1 * max_jobs_today), 1)
            if len(culling_jobs_today) > extra_culling_jobs:
                culling_jobs_today = random.sample(culling_jobs_today, extra_culling_jobs)

            extra_other_jobs = int(0.2 * max_jobs_today) + (max_jobs_today - len(jobs_today))
            if extra_other_jobs >= len(other_jobs_today):
                extra_other_jobs_today = other_jobs_today
            else:
                extra_other_jobs_today = random.sample(other_jobs_today, extra_other_jobs)

        jobs_today.extend(culling_jobs_today)
        jobs_today.extend(extra_other_jobs_today)

        for job in jobs_today:
            property_index, job_type, day, status = job
            if job_type == "LabTesting":
                # run the lab test and subsequent actionns
                temp_combined_narrative, labresult, DCP_status = self.run_lab_testing_now(
                    properties, property_index, time, converted_date
                )
                num_lab_tested += 1
                if labresult:  # is positive
                    num_confirmed_infected += 1
                else:
                    num_tested_negative += 1
                    if DCP_status:
                        DCP_tested_negative += 1
                    else:
                        surveillance_tested_negative += 1

                # save the report appropriately
                new_combined_narrative.extend(temp_combined_narrative)

                properties[property_index].undergoing_testing = False
                properties[property_index].day_of_last_lab_test = time

                # mark this job as done, and the date of completion, in the job_queue
                self.jobs_queue[property_index][job_type][day] = ["complete", converted_date]

            elif job_type == "ClinicalObservation":
                # run the lab test and subsequent actionns
                testing_report, positive = self.conduct_clinicalobservation(properties, property_index, time)
                new_combined_narrative.append([time, converted_date, "test", property_index, testing_report])

                if positive:
                    num_positive_clinical += 1
                    properties[property_index].status = "DCP"
                else:
                    # TODO: could make it DCP even if negative observation, if it's close to another infected property OR if the property is truly infected
                    pass

                self.jobs_queue[property_index][job_type][day] = ["complete", converted_date]

                # regardless of whether positive:
                # schedule contact tracing
                report = self.schedule_contract_tracing(property_index, time)
                new_combined_narrative.append([time, converted_date, "tracing", property_index, report])

                # schedule lab testing (if not yet done)
                report, scheduled_successful = self.schedule_lab_testing_after_observation(property_index, time)
                new_combined_narrative.append([time, converted_date, "test", property_index, report])
                if scheduled_successful:
                    properties[property_index].undergoing_testing = True

            elif job_type == "Cull":
                premise = properties[property_index]
                premise_report, culled_animals = premise.cull_only(time)
                new_combined_narrative.append([time, converted_date, "cull", property_index, premise_report])
                total_culled_animals += culled_animals

                self.jobs_queue[property_index][job_type][day] = ["complete", converted_date]

                # TODO - should also remove ANY OTHER JOBS related to this property (hm, except for maybe contact tracing?)

            elif job_type == "ContactTracing":
                contact_tracing_report, traced_property_indices = contact_tracing(
                    properties, property_index, movement_records, time
                )
                self.jobs_queue[property_index][job_type][day] = ["complete", converted_date]

                new_combined_narrative.append([time, converted_date, "tracing", property_index, contact_tracing_report])

                contacts_for_plotting[property_index] = traced_property_indices

                for t_i in traced_property_indices:
                    # check if property is not yet culled
                    if not properties[t_i].culled_status and not properties[t_i].reported_status:
                        new_combined_narrative.append(
                            [
                                time,
                                converted_date,
                                "tracing",
                                t_i,
                                "This property has been identified as a TP",
                            ]
                        )

                        # schedule movement restrictions right away
                        self.local_movement_restrictions.append(properties[t_i].polygon)
                        new_combined_narrative.append(
                            [
                                time,
                                converted_date,
                                "control",
                                t_i,
                                f"No movements are allowed to or from property {t_i} ({properties[t_i].type})",
                            ]
                        )

                        report, scheduled_successful = self.schedule_clinical_observation(t_i, time)
                        new_combined_narrative.append([time, converted_date, "test", t_i, report])
                        if scheduled_successful:
                            properties[t_i].undergoing_testing = True

        stats = [
            num_positive_clinical,
            num_lab_tested,
            num_confirmed_infected,
            num_tested_negative,
            DCP_tested_negative,
            surveillance_tested_negative,
        ]

        return (
            new_combined_narrative,
            self.local_movement_restrictions,
            total_culled_animals,
            contacts_for_plotting,
            stats,
        )

    def calculate_resources_used(self, folder_path):
        # there's probably a dataframes way to do this

        header = ["completion_date", "LabTesting", "ClinicalObservation", "Cull", "ContactTracing"]
        resources = {}
        for property_index in self.jobs_queue.keys():
            for job_type in self.jobs_queue[property_index].keys():
                for day, status in self.jobs_queue[property_index][job_type].items():
                    if status[0] == "complete":
                        try:
                            resources[status[1]][job_type] += 1
                        except:
                            resources[status[1]] = {j: 0 for j in job_types}
                            resources[status[1]][job_type] += 1
        jobs = []

        for key, value in resources.items():
            jobs.append(
                [key, value["LabTesting"], value["ClinicalObservation"], value["Cull"], value["ContactTracing"]]
            )
        # order by the date
        jobs.sort(key=lambda x: x[0])
        # convert to dataframe
        # save the dataframe
        jobs_df = pd.DataFrame(jobs, columns=header)

        jobs_df.to_csv(os.path.join(folder_path, "resources_used.csv"), index=False)

    def get_premises_under_active_jobs(self):
        list_of_premises = []
        for property_index in self.jobs_queue.keys():
            for job_type in self.jobs_queue[property_index].keys():
                for day, status in self.jobs_queue[property_index][job_type].items():
                    if status[0] == "in progress":
                        list_of_premises.append(property_index)
        return list_of_premises
