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


# TODO: incomplete start to a class system for jobs
# """
#     Class for jobs - basic policy framework, which defines what kind of jobs come next after it
# """
# class JobPolicy:

#     def __init__(self, job_type : jobtype, delay : float, yes_jobs = [], no_jobs = None):
#         self.job_type = job_type
#         self.delay = delay
#         self.yes_jobs = yes_jobs
#         self.no_jobs = no_jobs

#     # def run_job(self,params):
#     #     result = self.job_function(**params)
#     #     if result == True:
#     #         return self.yes_jobs
#     #     else:
#     #         return self.no_jobs


# class Culling(JobPolicy):
#     def __init__(self, delay):
#         super().__init(self, jobtype.Culling, delay, None, None) # there are no follow-on jobs from culling

#     def start_job(self, start_day : float, property_to_cull):
#         super().start_job(start_day)
#         report = ""
#         anticipated_completion = start_day + self.delay
#         return report, anticipated_completion

#     def finish_job(self, day, property_to_cull):
#         pass


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

    contact_tracing_report = f"DAY {convert_time_to_date(time)} - contact tracing report compiled for movements from IP {properties[property_index].ip} (ID {properties[property_index].id})\n"
    traced_property_indices = []

    properties_found = False

    if len(movement_records) != 0:
        # check the length of movement records (a minimum requirement)
        if len(movement_records[0]) == 4:

            # go through the movement records, and look for animal movements off the property
            for record in movement_records:
                if record[1] == property_index:
                    properties_found = True
                    traced_property_indices.append(record[2])
                    contact_tracing_report = (
                        contact_tracing_report + " - " + record[3] + "\n"
                    )
    if not properties_found:
        contact_tracing_report += " - no movements found\n"

    return contact_tracing_report, traced_property_indices


def test_property(
    properties, property_index, time, test_sensitivity, test_type="Lab test"
):
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
            testing_report += (
                f"Property index {property_index} report negative result\n"
            )
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
        small_testing_report, positive = test_property(
            properties, index, time, test_sensitivity
        )
        testing_report += small_testing_report

        if positive:
            positive_indices.append(index)

    return testing_report, positive_indices
