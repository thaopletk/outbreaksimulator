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

    contact_tracing_report = f"DAY {convert_time_to_date(time)} - contact tracing report compiled for movements to/from IP {properties[property_index].ip} (ID {properties[property_index].id})\n"
    traced_property_indices = []

    properties_found = False

    timeframe = movement_records.loc[movement_records["day"] >= time - 14]
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
        return testing_report, positive

    def check_if_recent_job_already_exists(self, property_i, scheduled_day, job_type):
        results_dict = self.jobs_queue[property_i][job_type]

        for day in results_dict.keys():
            if float(day) <= scheduled_day and float(day) >= scheduled_day - 14:
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

        new_combined_narrative.append([time, converted_date, "test", testing_report])

        if positive:
            premise = properties[property_index]

            # report property
            premise_report = premise.report_only(time)
            new_combined_narrative.append([time, converted_date, "report", premise_report])

            # schedule culling
            report = self.decision_to_cull(property_index, time)
            new_combined_narrative.append([time, converted_date, "cull", report])

            # enact local movement restrictions around this property, just in case
            self.local_movement_restrictions.append(properties[property_index].polygon)
            new_combined_narrative.append(
                [
                    time,
                    converted_date,
                    "control",
                    f"No movements are allowed to or from property {property_index} ({properties[property_index].type})",
                ]
            )

            report = self.schedule_contract_tracing(property_index, time)
            new_combined_narrative.append([time, converted_date, "tracing", report])
        else:
            # remove any local movement restrictions
            try:
                self.local_movement_restrictions.remove(properties[property_index].polygon)
                new_combined_narrative.append(
                    [
                        time,
                        converted_date,
                        "control",
                        f"Local movement restrictions lifted for property {property_index} (other movement controls still in place)",
                    ]
                )
            except:
                warnings.warn("Local polygon doesn't exist in the local movement restrictions for some reason...")

            # may have ongoing surveillance here in the future
        return new_combined_narrative

    def run_jobs(self, time, properties, movement_records, converted_date):
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

        # go through the jobs queue & look for "in progress" jobs
        jobs_today = []
        for property_index in self.jobs_queue.keys():
            for job_type in self.jobs_queue[property_index].keys():
                for day, status in self.jobs_queue[property_index][job_type].items():
                    if status[0] == "in progress" and float(day) <= time:
                        jobs_today.append([property_index, job_type, day, status])

        # TODO run the jobs
        for job in jobs_today:
            property_index, job_type, day, status = job
            if job_type == "LabTesting":
                # run the lab test and subsequent actionns
                temp_combined_narrative = self.run_lab_testing_now(properties, property_index, time, converted_date)

                # save the report appropriately
                new_combined_narrative.extend(temp_combined_narrative)

                properties[property_index].undergoing_testing = False
                properties[property_index].day_of_last_lab_test = time

                # mark this job as done, and the date of completion, in the job_queue
                self.jobs_queue[property_index][job_type][day] = ["complete", converted_date]

            elif job_type == "ClinicalObservation":
                # run the lab test and subsequent actionns
                testing_report, positive = self.conduct_clinicalobservation(properties, property_index, time)
                new_combined_narrative.append([time, converted_date, "test", testing_report])

                self.jobs_queue[property_index][job_type][day] = ["complete", converted_date]

                # regardless of whether positive:
                # schedule contact tracing
                report = self.schedule_contract_tracing(property_index, time)
                new_combined_narrative.append([time, converted_date, "tracing", report])

                # schedule lab testing (if not yet done)
                report, scheduled_successful = self.schedule_lab_testing_after_observation(property_index, time)
                new_combined_narrative.append([time, converted_date, "test", report])
                if scheduled_successful:
                    properties[property_index].undergoing_testing = True

            elif job_type == "Cull":
                premise = properties[property_index]
                premise_report, culled_animals = premise.cull_only(time)
                new_combined_narrative.append([time, converted_date, "cull", premise_report])
                total_culled_animals += culled_animals

                self.jobs_queue[property_index][job_type][day] = ["complete", converted_date]

                # TODO - should also remove ANY OTHER JOBS related to this property

            elif job_type == "ContactTracing":
                contact_tracing_report, traced_property_indices = contact_tracing(
                    properties, property_index, movement_records, time
                )
                self.jobs_queue[property_index][job_type][day] = ["complete", converted_date]

                new_combined_narrative.append([time, converted_date, "tracing", contact_tracing_report])

                contacts_for_plotting[property_index] = traced_property_indices

                for t_i in traced_property_indices:
                    # check if property is not yet culled
                    if not properties[t_i].culled_status:

                        # schedule movement restrictions right away
                        self.local_movement_restrictions.append(properties[property_index].polygon)
                        new_combined_narrative.append(
                            [
                                time,
                                converted_date,
                                "control",
                                f"No movements are allowed to or from property {property_index} ({properties[property_index].type})",
                            ]
                        )

                        report, scheduled_successful = self.schedule_clinical_observation(t_i, time)
                        new_combined_narrative.append([time, converted_date, "test", report])
                        if scheduled_successful:
                            properties[t_i].undergoing_testing = True

        return new_combined_narrative, self.local_movement_restrictions, total_culled_animals, contacts_for_plotting

    def job_manager(self, time, properties, movement_records):
        new_report = ""
        new_testing_reports = ""
        new_combined_narrative = ""
        new_contact_tracing_reports = ""
        total_culled_animals = 0
        contacts_for_plotting = {}  # from property, to properties

        # TODO go through the jobs queue
        # TODO look for "in progress" jobs
        # TODO do some kind of prioritisation
        # in terms of adding things to the combined narrative, then it might make more sense to run each job inside the disease simulation itself, rather than here
        # so, this function could just return active jobs?
        # TODO run the jobs
        # and TODO schedule any new jobs as necessary

        for job in self.jobs_queue:
            if job["status"] == "in progress" and job["day"] <= time:
                # job should now be complete
                if job["type"] == jobtype.LabTesting:
                    temp_report, temp_testing_reports, temp_combined_narrative = self.run_lab_testing_now(
                        properties, job, time
                    )
                    new_report += temp_report
                    new_testing_reports += temp_testing_reports
                    new_combined_narrative += temp_combined_narrative

                    properties[job["property_i"]].undergoing_testing = False
                    properties[job["property_i"]].day_of_last_lab_test = time

                elif job["type"] == jobtype.ClinicalObservation:
                    testing_report, positive = self.conduct_clinicalobservation(properties, job, time)
                    new_testing_reports += testing_report
                    new_combined_narrative += testing_report

                    if positive:
                        premise = properties[job["property_i"]]

                        # enact local movement restrictions around this property, just in case
                        self.local_movement_restrictions.append(properties[job["property_i"]].polygon)
                        # TODO there should be a report here, like
                        # report = "No movements are now allowed to or from this property.\n"
                        # new_report += report
                        # new_combined_narrative += report

                        # schedule contact tracing
                        report = self.schedule_contract_tracing(job["property_i"], time)
                        new_combined_narrative += report

                        # schedule lab testing (if not yet done)
                        report = self.schedule_lab_testing_after_observation(job["property_i"], time)
                        new_report += report
                        new_combined_narrative += report

                        properties[job["property_i"]].undergoing_testing = True

                    else:
                        # remove any local movement restrictions
                        # technically, should check if it's still under lab testing, which means we might still want some movement restrictions lol...
                        pass
                        # self.local_movement_restrictions.remove(properties[job["property_i"]].polygon)

                        # may have ongoing surveillance here in the future
                elif job["type"] == jobtype.Cull:
                    premise = properties[job["property_i"]]
                    premise_report, culled_animals = premise.cull_only(time)
                    total_culled_animals += culled_animals
                    new_report += premise_report
                    new_combined_narrative += premise_report

                    job["status"] = "complete"  # mark job as complete, slated for removal from the job queue

                    # TODO - should also remove ANY OTHER JOBS related to this property

                elif job["type"] == jobtype.ContactTracing:
                    contact_tracing_report, traced_property_indices = contact_tracing(
                        properties, job["property_i"], movement_records, time
                    )
                    new_contact_tracing_reports += contact_tracing_report
                    new_combined_narrative += contact_tracing_report

                    contacts_for_plotting[job["property_i"]] = traced_property_indices

                    for t_i in traced_property_indices:
                        # check if property is not yet culled
                        if not properties[t_i].culled_status:

                            # to be honest, this kind of thing should only be notified after successful adding, not before TODO
                            mini_report = f"Personnel will be sent to traced property {t_i} for clinical observation and lab testing\n"
                            new_report += mini_report
                            new_combined_narrative += mini_report

                            self.schedule_clinical_observation(t_i, time)

                            # schedule lab testing (if not yet done)
                            # technically this might require a longer delay...

                            report = self.schedule_lab_testing(t_i, time)
                            new_report += report

                            properties[t_i].undergoing_testing = True

                    job["status"] = "complete"  # mark job as complete, slated for removal from the job queue

        return (
            new_report,
            new_testing_reports,
            new_combined_narrative,
            new_contact_tracing_reports,
            self.local_movement_restrictions,
            total_culled_animals,
            contacts_for_plotting,
        )
