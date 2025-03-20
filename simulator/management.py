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


# discrete job type list syntax
class jobtype(Enum):
    LabTesting = 1
    ClinicalObservation = 2
    Cull = 3
    ContactTracing = 4
    # SelfReport = 1
    # LocalMovementRestriction = 2
    # LargeMovementRestriction = 3
    # LabTestingStart = 4
    # LabTestingResults = 5
    # ClinicalTestingStart = 6
    # ClinicalTestingResults = 7
    # ContactTracingStart = 8
    # ContactTracingResults = 9
    # DecisionToCull = 10
    # Culling = 11
    # RingManagement = 12


job_types = ["LabTesting", "ClinicalObservation", "Cull", "ContactTracing"]


def define_control_zone_circles(coordinates, radius_km):
    """Creates control zones around coordinates and joins them together"""
    list_of_polygons = []

    for site in coordinates:
        x = site[0]  # longitude
        y = site[1]  # latitude
        points_in_circle = geodesic_point_buffer(y, x, radius_km)
        poly = Polygon(points_in_circle)
        list_of_polygons.append(poly)

    controlzone = unary_union(list_of_polygons)

    return controlzone


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


# could probably run this recursively
def contact_tracing(properties, property_index, movement_records, time):
    """Contact tracing

    Parameters
    ----------
    properties
        list of properties
    property_index : int
        property from which we are tracing
    movement records : list of lists
        assumes records in form [time (int), property index from (int), property index to (int), report  (string)] (TODO: should do a check)

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
    positive = False
    premise = properties[property_index]

    testing_report = f"DAY {convert_time_to_date(time)} - {test_type} report for property index {property_index}\n"

    if premise.culled_status:
        testing_report += f"No testing: property index {property_index} (IP {premise.ip}) has already been culled\n"
    elif premise.infection_status:
        prob_successful = np.random.rand()
        if prob_successful < test_sensitivity:
            x, y = premise.coordinates
            testing_report += f"Property index {property_index} at location (x,y)=({round(x,2)}, {round(y,2)}) report POSITIVE result\n"
            positive = True
        else:
            testing_report += f"Property index {property_index} report negative result\n"
    else:
        testing_report += f"Property index {property_index} report negative result\n"
    return testing_report, positive


def testing(properties, property_indices, time, test_sensitivity):
    """Testing

    Conducts testing on the input property_indices

    """
    testing_report = ""  #  f"DAY {convert_time_to_date(time)} - testing report\n"
    positive_indices = []

    for index in property_indices:
        small_testing_report, positive = test_property(properties, index, time, test_sensitivity)
        testing_report += small_testing_report

        if positive:
            positive_indices.append(index)

    return testing_report, positive_indices


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

    def add_job_to_queue(self, job):
        exists = False
        # TODO could probably add in checks around whether this premise still exists and still needs to have this job completed or not
        for j in self.jobs_queue:
            if j["status"] == "in progress" and j["type"] == job["type"] and j["property_i"] == job["property_i"]:
                if j["day"] > job["day"]:
                    self.jobs_queue.remove(j)
                    self.jobs_queue.append(job)
                    return 0
                else:
                    exists = True
                    break

        if not exists:
            self.jobs_queue.append(job)

        return 0

    def conduct_labtesting(self, properties, job, time):
        testing_report, positive = test_property(
            properties,
            job["property_i"],
            time,
            self.lab_test_sensitivity,
            test_type="lab test",
        )
        job["status"] = "complete"  # mark job as complete, slated for removal from the job queue
        return testing_report, positive

    def conduct_clinicalobservation(self, properties, job, time):
        testing_report, positive = test_property(
            properties,
            job["property_i"],
            time,
            self.clinical_test_sensitivity,
            test_type="clinical observation",
        )
        job["status"] = "complete"  # mark job as complete, slated for removal from the job queue
        return testing_report, positive

    def decision_to_cull(self, property_i, time):
        report = f"Property {property_i} has been scheduled for culling\n"

        # add culling job to the jobs_queue, as it has a delay
        new_job = {
            "status": "in progress",
            "day": time + self.cull_delay,
            "type": jobtype.Cull,
            "property_i": property_i,
        }
        self.new_jobs.append(new_job)

        return report

    def check_if_recent_job_already_exists(self, property_i, scheduled_day, job_type):
        results_dict = self.jobs_queue[property_i][job_type]

        for day in results_dict.keys():
            if float(day) <= scheduled_day and float(day) >= scheduled_day - 14:
                return True
        return False

    def schedule_contract_tracing(self, property_i, time):
        scheduled_day = time + self.contact_tracing_delay
        job_type = "ContactTracing"

        if self.check_if_recent_job_already_exists(property_i, scheduled_day, job_type) == True:
            report = f"Property {property_i} has already been recently scheduled for contact tracing"
        else:
            self.jobs_queue[property_i][job_type][str(scheduled_day)] = "in progress"
            report = f"Property {property_i} has been scheduled for contact tracing"

        # new_job = {
        #     "status": "in progress",
        #     "day": time + self.contact_tracing_delay,
        #     "type": jobtype.ContactTracing,
        #     "property_i": property_i,
        # }

        # self.new_jobs.append(new_job)

        return report

    def schedule_lab_testing(self, property_i, time):
        new_job = {
            "status": "in progress",
            "day": time + self.lab_test_delay,
            "type": jobtype.LabTesting,
            "property_i": property_i,
        }
        self.new_jobs.append(new_job)

        mini_report = f"Personnel will be sent to property {property_i} for lab testing\n"
        return mini_report

    def schedule_lab_testing_after_observation(self, property_i, time):
        # reduced delay
        new_job = {
            "status": "in progress",
            "day": time + self.lab_test_delay - 0.5,
            "type": jobtype.LabTesting,
            "property_i": property_i,
        }
        self.new_jobs.append(new_job)

        mini_report = f"Personnel will be sent to property {property_i} for lab testing\n"
        return mini_report

    def schedule_clinical_observation(self, property_i, time):
        new_job = {
            "status": "in progress",
            "day": time + self.clinical_delay,
            "type": jobtype.ClinicalObservation,
            "property_i": property_i,
        }
        self.new_jobs.append(new_job)

    def run_lab_testing_now(self, properties, job, time):
        new_report = ""
        new_testing_reports = ""
        new_combined_narrative = ""

        testing_report, positive = self.conduct_labtesting(properties, job, time)

        new_testing_reports += testing_report
        new_combined_narrative += testing_report
        if positive:
            premise = properties[job["property_i"]]

            # report property
            premise_report = premise.report_only(time)
            new_report += premise_report
            new_combined_narrative += premise_report

            # schedule culling
            report = self.decision_to_cull(job["property_i"], time)
            new_report += report
            new_combined_narrative += report

            # enact local movement restrictions around this property, just in case
            self.local_movement_restrictions.append(properties[job["property_i"]].polygon)

            report = self.schedule_contract_tracing(job["property_i"], time)
            new_combined_narrative += report
        else:
            # remove any local movement restrictions
            try:
                self.local_movement_restrictions.remove(properties[job["property_i"]].polygon)
            except:
                warnings.warn("Local polygon doesn't exist in the local movement restrictions for some reason...")

            # may have ongoing surveillance here in the future
        return new_report, new_testing_reports, new_combined_narrative

    def job_manager(self, time, properties, movement_records):
        new_report = ""
        new_testing_reports = ""
        new_combined_narrative = ""
        new_contact_tracing_reports = ""
        total_culled_animals = 0
        contacts_for_plotting = {}  # from property, to properties

        # add in new jobs; this checks for any repeat jobs and doesn't add repeat jobs
        for job in self.new_jobs:
            self.add_job_to_queue(job)
        self.new_jobs = []

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

        # clean up job queue
        self.jobs_queue = [job for job in self.jobs_queue if job["status"] == "in progress"]

        # add in new jobs; this checks for any repeat jobs and doesn't add repeat jobs
        for job in self.new_jobs:
            self.add_job_to_queue(job)
        self.new_jobs = []

        return (
            new_report,
            new_testing_reports,
            new_combined_narrative,
            new_contact_tracing_reports,
            self.local_movement_restrictions,
            total_culled_animals,
            contacts_for_plotting,
        )
