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


def testing(properties, property_indices, time, test_sensitivity):
    """Testing

    Conducts testing on the input property_indices

    """
    testing_report = f"DAY {convert_time_to_date(time)} - testing report\n"
    positive_indices = []

    for index in property_indices:
        premise = properties[index]
        if premise.culled_status:
            testing_report += f"No testing: property index {index} (IP {premise.ip}) has already been culled\n"
        elif premise.infection_status:
            prob_successful = np.random.rand()
            if prob_successful < test_sensitivity:
                x, y = premise.coordinates
                testing_report += f"Tested: property index {index} at location (x,y)=({round(x,2)}, {round(y,2)}) report POSITIVE result\n"
                positive_indices.append(index)
            else:
                testing_report += (
                    f"Tested: property index {index} report negative result\n"
                )
        else:
            testing_report += f"Tested: property index {index} report negative result\n"

    return testing_report, positive_indices
