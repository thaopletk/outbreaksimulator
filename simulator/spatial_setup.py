""" Spatial setup

    Original code written by Isobel Abell and adapted by Thao Le     (overriding the spatial setup code from FMD_modelling from generate_property_grid.py)

    This script generates random properties (i.e. farms) across the landscape, in latitude,longitude coordinates and areas in hectares and distances in kilometers (where relevant)

    Some of the functions are adapted from elsewhere, noted down at each function description.

"""

import numpy as np
import math
import matplotlib.pyplot as plt
import simulator.random_rectangles as random_rectangles
import pyproj
from shapely.geometry import shape, Polygon, Point
from area import area
import pyproj
from functools import partial
from shapely.ops import transform


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


def assign_coordinates(n, xrange=[150.2503, 151.39695], yrange=[-32.61181, -31.60829]):
    """Generates n random properties within the xrange, yrange region"""
    property_coordinates = np.zeros((n, 2))
    for i in range(n):
        x = np.random.uniform(*xrange)
        y = np.random.uniform(*yrange)
        property_coordinates[i, 0] = x
        property_coordinates[i, 1] = y

    return property_coordinates


def assign_neighbours(property_coordinates, n, r):
    """Assign wind-neighbours, assuming point-properties

    Parameters
    ----------
    property_coordinates : list
        list of coordinates of the properties
    n : int
        number of properties
    r : double or int
        radius (in kilometers) in which properties are considered "neighbours"

    Returns
    -------
    adjacency_matrix : (n,n) matrix
        symmetric adjacency matrix describing if properties are neighbours of each other or not
        adjacency_matrix[p1, p2] = 1 means that p1 and p2 are neighbours

    neighbour_pairs : list of list of separated coordinates
        Describes the coordinates of pairs of neighbours (can be used to plot lines between neighbours)
        List of [x, y] pairs, where x = [x coord of p1, x coord of p2] and y = [y coord of p1, y coord of p2]

    neighbourhoods : list of list of neighbours
        List of neighbours for each property
        i.e., for property i, neighbours[i] is a list of property i's neighbours's index and distance

    """

    adjacency_matrix = np.zeros((n, n))
    neighbourhoods = []
    neighbour_pairs = []

    for p1 in range(n):
        neighbourhoods.append([])
        for p2 in range(
            n
        ):  # this could be simplified by choosing on p2 in range (p1+1, n), and changing p1 to range (0,n-1), given the symmetry...

            if p1 != p2:
                # dist = np.linalg.norm(np.array(property_coordinates[p1]) - np.array(property_coordinates[p2]))
                dist = quick_distance_haversine(
                    property_coordinates[p1], property_coordinates[p2]
                )  # distance in km

                if dist <= r:
                    # close enough => neighbours
                    adjacency_matrix[p1, p2] = 1
                    adjacency_matrix[p2, p1] = 1
                    x = [property_coordinates[p1, 0], property_coordinates[p2, 0]]
                    y = [property_coordinates[p1, 1], property_coordinates[p2, 1]]

                    # indices of properties neighbouring property p1
                    neighbourhoods[p1].append([p2, dist])

                    neighbour_pairs.append([x, y])

    return adjacency_matrix, neighbour_pairs, neighbourhoods


def plot_coordinates(property_coordinates, neighbour_pairs):
    """Basic plotting for property coordinates (centers) and wind-neighbours"""
    plt.figure()

    # nodes
    for i in range(len(property_coordinates)):
        if i == 3:
            plt.scatter(
                property_coordinates[i, 0], property_coordinates[i, 1], color="red"
            )
        else:
            plt.scatter(
                property_coordinates[i, 0], property_coordinates[i, 1], color="purple"
            )

    # edges
    for node_coordinates in neighbour_pairs:
        plt.plot(node_coordinates[0], node_coordinates[1], alpha=0.2)

    plt.show()

    return


# possible extensions: boundaries along roads, more jagged shapes, avoid areas like parks and nature reserves, add some level of clustering
def assign_property_locations(
    n,
    xrange=[150.2503, 151.39695],
    yrange=[-32.61181, -31.60829],
    average_property_ha=300,
):
    """Generates n random properties (with rectangular shapes)  within the xrange, yrange region

    Parameters
    ----------
    n : int
        number of properties to generate
    xrange : list
        x (longitude) width
    yrange  : list
        y (latitude) width
    average_property_ha : double or int
        a rough target for the average property size, in hectares

    Returns
    -------
    property_coordinates : list
        list of coordinates of the properties (center)
    property_polygons : list of Polygons
        the list containing the properties' shapely Polygon shape
    property_areas : list
        list of sizes/areas (in hectares) of the generated properties

    """

    # first, make rectangles

    # to estimate the number of rectangles, I need to get the total area of xrange, yrange, and divide it up by the average property size that I want
    # the average property size is 300 hectares, or 3 km^2, taken from https://www.agriculture.gov.au/abares/research-topics/surveys/dairy#farm-characteristics

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
    bounding_area = area(
        bounding_polygon
    )  # it's not exact-exact but should be good enough, value in square metres
    sq_to_ha = 0.0001
    area_in_hectares = sq_to_ha * bounding_area

    num_recs_to_generate = int(np.ceil(area_in_hectares / average_property_ha))
    num_rectangles = n

    #  x1, y1, x2, y2
    region = random_rectangles.Rect(xrange[0], yrange[0], xrange[1], yrange[1])
    random_recs = random_rectangles.return_random_rectangles(
        num_rectangles, num_recs_to_generate, region
    )
    # the resultant rectangles are the properties

    property_coordinates = np.zeros((n, 2))
    property_polygons = []
    property_areas = []

    for i in range(n):
        rectangle = random_recs[i]
        # make polygons
        property_polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    [rectangle.min.x, rectangle.min.y],
                    [rectangle.max.x, rectangle.min.y],
                    [rectangle.max.x, rectangle.max.y],
                    [rectangle.min.x, rectangle.max.y],
                    [rectangle.min.x, rectangle.min.y],
                ]
            ],
        }

        property_areas.append(sq_to_ha * area(property_polygon))

        property_polygons.append(
            convert_dict_poly_to_Polygon(property_polygon)
        )  # Shapely Polygon object needed for the rest of the code

        property_coordinates[i, 0] = (rectangle.min.x + rectangle.max.x) / 2
        property_coordinates[i, 1] = (rectangle.min.y + rectangle.max.y) / 2

    return property_coordinates, property_polygons, property_areas


def assign_neighbours_with_land(property_coordinates, property_polygons, n, r):
    """Assign wind-neighbours, assuming properties with physical size

    Parameters
    ----------
    property_coordinates : list
        list of coordinates of the properties
    property_polygons : list of Polygons
        the list containing the properties' shapely Polygon shape
    n : int
        number of properties
    r : double or int
        radius (in kilometers) in which properties are considered "neighbours"

    Returns
    -------
    adjacency_matrix : (n,n) matrix
        symmetric adjacency matrix describing if properties are neighbours of each other or not
        adjacency_matrix[p1, p2] = 1 means that p1 and p2 are neighbours

    neighbour_pairs : list of list of separated coordinates
        Describes the coordinates of pairs of neighbours (can be used to plot lines between neighbours)
        List of [x, y] pairs, where x = [x coord of p1, x coord of p2] and y = [y coord of p1, y coord of p2]

    neighbourhoods : list of list of neighbours
        List of neighbours for each property
        i.e., for property i, neighbours[i] is a list of property i's neighbours's index and distance

    property_polygons_puffed : list of polygons
        Puffed up polygons, showing the "wind range" of each property

    """
    adjacency_matrix = np.zeros((n, n))
    neighbourhoods = []
    neighbour_pairs = []
    property_polygons_puffed = []

    for p1 in range(n):
        neighbourhoods.append([])
        # loop over property list
        for p2 in range(n):
            # don't consider property whose neighbourhood we're calculating
            if p1 != p2:
                # calculate distance between centres
                # dist = np.linalg.norm(np.array(property_coordinates[p1]) - np.array(property_coordinates[p2]))
                dist_centres = quick_distance_haversine(
                    property_coordinates[p1], property_coordinates[p2]
                )  # distance in km

                # calculate whether they're wind-neighbours
                # step 1: puff up p1
                p1_poly = property_polygons[p1]
                lat = property_coordinates[p1][1]  # y
                lon = property_coordinates[p1][0]  # x
                puff_p1 = geodesic_polygon_buffer(lat, lon, p1_poly, r)
                property_polygons_puffed.append(puff_p1)

                p2_poly = property_polygons[p2]

                if puff_p1.intersects(p2_poly):
                    # they're wind-neighbours, congrats
                    adjacency_matrix[p1, p2] = 1

                    # coordinates of properties
                    x = [property_coordinates[p1, 0], property_coordinates[p2, 0]]
                    y = [property_coordinates[p1, 1], property_coordinates[p2, 1]]

                    # append neighbour pair list with coordinates of each property (used for plotting)
                    neighbour_pairs.append([x, y])

                    # append neighbourhood list with index of neighbour and distance between boundaries
                    # dist_boundaries = dist_centres # dummy value at the moment, it's not used anyway

                    neighbourhoods[p1].append([p2, dist_centres])

    return adjacency_matrix, neighbour_pairs, neighbourhoods, property_polygons_puffed


def generate_properties(
    n, r, xrange=[150.2503, 151.39695], yrange=[-32.61181, -31.60829]
):
    """Generates point-properties, without land"""

    # randomly place properties within a rectangle (bounded by xrange, yrange)
    property_coordinates = assign_coordinates(n, xrange, yrange)

    # find neighbours given neighbourhood radius
    adjacency_matrix, neighbour_pairs, neighbourhoods = assign_neighbours(
        property_coordinates, n, r
    )

    # plot_coordinates(property_coordinates, neighbour_pairs)

    return property_coordinates, adjacency_matrix, neighbour_pairs, neighbourhoods


def generate_properties_with_land(
    n,
    wind_r,
    xrange=[150.2503, 151.39695],
    yrange=[-32.61181, -31.60829],
    average_property_ha=300,
):
    """Generates properties, with land

    Parameters
    ----------
    n : int
        number of properties
    wind_r : double or int
        radius (in kilometers) in which properties are considered "neighbours"
    xrange : list
        x (longitude) width
    yrange  : list
        y (latitude) width
    average_property_ha : double or int
        a rough target for the average property size, in hectares

    Returns
    -------
    property_coordinates : list
        list of coordinates of the properties (center)
    adjacency_matrix : (n,n) matrix
        symmetric adjacency matrix describing if properties are neighbours of each other or not
        adjacency_matrix[p1, p2] = 1 means that p1 and p2 are neighbours
    neighbour_pairs : list of list of separated coordinates
        Describes the coordinates of pairs of neighbours (can be used to plot lines between neighbours)
        List of [x, y] pairs, where x = [x coord of p1, x coord of p2] and y = [y coord of p1, y coord of p2]
    neighbourhoods : list of list of neighbours
        List of neighbours for each property
        i.e., for property i, neighbours[i] is a list of property i's neighbours's index and distance
    property_polygons : list of Polygons
        the list containing the properties' shapely Polygon shape
    property_polygons_puffed : list of polygons
        Puffed up polygons, showing the "wind range" of each property
    property_areas : list
        list of sizes/areas (in hectares) of the generated properties

    """

    # randomly divide the space up into rectangles (approximately), and choose some randomly to be property locations
    property_coordinates, property_polygons, property_areas = assign_property_locations(
        n, xrange, yrange, average_property_ha
    )

    # find wind-neighbours given wind-neighbourhood radius

    adjacency_matrix, neighbour_pairs, neighbourhoods, property_polygons_puffed = (
        assign_neighbours_with_land(property_coordinates, property_polygons, n, wind_r)
    )

    # possible extension is to return in a dictionary, to improve flexibility of output
    return (
        property_coordinates,
        adjacency_matrix,
        neighbour_pairs,
        neighbourhoods,
        property_polygons,
        property_polygons_puffed,
        property_areas,
    )
