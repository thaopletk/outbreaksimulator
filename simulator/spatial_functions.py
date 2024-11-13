""" Management

This script contains several functions that involve spatial stuff

"""

import geopandas as gpd
import pyproj
from functools import partial
from shapely.geometry import Polygon, Point, LineString, MultiPolygon
from shapely.ops import transform, unary_union
import numpy as np
import math
from area import area


def geodesic_point_buffer(lat, lon, km):
    """Returns a circle around a point

    Based on an azimuthal equidistant projection

    """

    proj_wgs84 = pyproj.Proj(init="epsg:4326")

    aeqd_proj = "+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0"
    project = partial(
        pyproj.transform, pyproj.Proj(aeqd_proj.format(lat=lat, lon=lon)), proj_wgs84
    )
    buf = Point(0, 0).buffer(km * 1000)  # distance in metres
    return transform(project, buf).exterior.coords[:]


# https://stackoverflow.com/questions/15736995/how-can-i-quickly-estimate-the-distance-between-two-latitude-longitude-points
def quick_distance_haversine(coords1, coords2):
    """Get the distance between two points

    Calculates the great circle distance between two points
    on the earth (specified in decimal degrees) and converts it to kilometers

    Parameters
    ----------
    coords1 : list of doubles [x1, y1]
        coordinates of the first point, where x1 is longitude and y1 is latitude
    coords1 : list of doubles [x2, y2]
        coordinates of the second point, where x2 is longitude and y2 is latitude

    Returns
    -------
    km : double
        distance between the two points in kilometers
    """

    x1, y1 = coords1
    x2, y2 = coords2

    lon1 = x1
    lat1 = y1
    lon2 = x2
    lat2 = y2

    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))
    # Radius of earth in kilometers is 6371
    km = 6371 * c
    return km


def calculate_area(polygon):
    """Calculate area of a polygon, in hectares

    bounding_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [xrange[0], yrange[0]],
                [xrange[1], yrange[0]],
                [xrange[1], yrange[1]],
                [xrange[0], yrange[1]],
                [xrange[0], yrange[0]],
            ]
        ],
    }

    """

    sq_to_ha = 0.0001

    # first check if it is in dictionary form or not
    if type(polygon) != dict:
        # in this case, it should be a polygon (normal shapely polygon)
        polygon = {
            "type": "Polygon",
            "coordinates": [polygon.exterior.coords[:]],
        }

    poly_area = area(
        polygon
    )  # it's not exact-exact but should be good enough, value in square metres

    area_in_hectares = sq_to_ha * poly_area

    return area_in_hectares


def convert_dict_poly_to_Polygon(poly_to_convert):
    """Converts dictionaries of the following type into Shapely Polygons:

    {"type": "Polygon",
    "coordinates": [ [ [x0, y0],...] ]}

    """
    # possible extension - to check that input is in the right format

    return Polygon([(x, y) for x, y in poly_to_convert["coordinates"][0]])


def geodesic_polygon_buffer(lat, lon, poly_to_buff, km):
    """Expands a polygon by a certain radius (makes it more puffy by adding a buffer around it)"""

    if type(poly_to_buff) == dict:
        poly_to_buff = convert_dict_poly_to_Polygon(poly_to_buff)

    # Azimuthal equidistant projection
    proj_wgs84 = pyproj.Proj("EPSG:4326")

    aeqd_proj = "+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0"
    project = partial(
        pyproj.transform,
        pyproj.Proj(aeqd_proj.format(lat=lat, lon=lon)),
        proj_wgs84,
        always_xy=True,
    )
    buf = poly_to_buff.buffer(km * 1000)  # distance in metres
    return Polygon(transform(project, buf).exterior.coords[:])
