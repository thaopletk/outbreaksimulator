""" Spatial setup

    Original code written by Isobel Abell and adapted by Thao Le     (overriding the spatial setup code from FMD_modelling from generate_property_grid.py)

    This script generates random properties (i.e. farms) across the landscape, in latitude,longitude coordinates and areas in hectares and distances in kilometers (where relevant)

    Some of the functions are adapted from elsewhere, noted down at each function description.

"""

import numpy as np
import math
import os
import matplotlib.pyplot as plt
import simulator.random_rectangles as random_rectangles
import pyproj
from shapely.geometry import shape, Polygon, Point
from area import area
import pyproj
from functools import partial
from shapely.ops import transform
from simulator.spatial_functions import *
import rasterio as rio
from pyproj import Proj, itransform


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
                dist = quick_distance_haversine(property_coordinates[p1], property_coordinates[p2])  # distance in km

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
            plt.scatter(property_coordinates[i, 0], property_coordinates[i, 1], color="red")
        else:
            plt.scatter(property_coordinates[i, 0], property_coordinates[i, 1], color="purple")

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

    area_in_hectares = calculate_area(bounding_polygon)

    num_recs_to_generate = int(np.ceil(area_in_hectares / average_property_ha))
    num_rectangles = num_recs_to_generate  # n  # keeping all generated rectangles for now

    #  x1, y1, x2, y2
    region = random_rectangles.Rect(xrange[0], yrange[0], xrange[1], yrange[1])
    random_recs = random_rectangles.return_random_rectangles(num_rectangles, num_recs_to_generate, region)
    # the resultant rectangles could become properties

    # Read in Australia shapefile
    Australia_gdf = gpd.read_file(
        os.path.join(os.path.dirname(__file__), "..", "data", "AUS_2021_AUST_SHP_GDA2020", "AUS_2021_AUST_GDA2020.shp")
    )
    print(Australia_gdf)
    Australia_only = Australia_gdf.loc[Australia_gdf["AUS_NAME21"] == "Australia", :]
    # Australia_gdf['geometry'] - multipolygon
    Australiashape = Australia_only["geometry"][0]
    # print(Australiashape)

    property_coordinates = np.zeros((n, 2))
    property_polygons = []
    property_areas = []

    # With more complicated checking for landuse codes
    landuse_geotiff = os.path.join(os.path.dirname(__file__), "..", "data", "clum_50m_2023_v2", "clum_50m_2023_v2.tif")
    with rio.Env():
        with rio.open(landuse_geotiff) as geotiff_src:
            # print(geotiff_src.bounds)

            # x = (geotiff_src.bounds.left + geotiff_src.bounds.right) / 2.0
            # y = (geotiff_src.bounds.bottom + geotiff_src.bounds.top) / 2.0

            # for val in geotiff_src.sample([(x, y)]):
            #     print(val)

            meta = geotiff_src.meta
            print(meta)
            i_random_recs = -1
            for i in range(n):
                insideAustralia = False
                while not insideAustralia:
                    i_random_recs += 1
                    if i_random_recs >= len(random_recs):
                        raise Exception("Not enough generated rectangles within Australia!")
                    rectangle = random_recs[i_random_recs]
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
                    Polygon_obj = convert_dict_poly_to_Polygon(property_polygon)  # Shapely Polygon object

                    # check if the polygon is inside Australia or not
                    if Australiashape.contains(Polygon_obj):
                        # now also check if the landuse type is okay or not, by checking if the center point land use is okay
                        acceptable_land_use_codes = [
                            210,
                            320,
                            3221,
                            322,
                            323,
                            324,
                            325,
                            330,
                            360,
                            361,
                            362,
                            363,
                            264,
                            420,
                            421,
                            422,
                            423,
                            424,
                            430,
                            461,
                            462,
                            463,
                            464,
                            520,
                            521,
                            522,
                            523,
                            524,
                            526,
                            527,
                            528,
                            535,
                            540,
                            542,
                            545,
                        ]  # ALUM codes

                        # acceptable_land_use_RBG = [[255,255,229], # grazing native vegetation
                        #                            [255, 211, 127], # grazing modified pastures
                        #                            [255, 255, 0], #dryland cropping
                        #                            [255, 170, 0], #Irrigated pastures
                        #                             [201,184,84], # irrigated cropping
                        #                             [255,201,190], # intensive horticulture and animal production
                        #                             [178,178, 178], #rural residental and farm infrastructure
                        #                            ]

                        # center point
                        x_coord = (rectangle.min.x + rectangle.max.x) / 2
                        y_coord = (rectangle.min.y + rectangle.max.y) / 2

                        # print(f"x,y coords are {x}, {y}")

                        # for val in  geotiff_src.sample([(x_coord,y_coord)]):
                        #     print(f"val with untransformed coords is {val}")

                        p1 = Proj("epsg:4326", preserve_units=False)
                        p2 = Proj("epsg:3577", preserve_units=False)
                        for pt in itransform(p1, p2, [(x_coord, y_coord)], always_xy=True):
                            # print(f"transformed x,y coords (pt) are {pt}")
                            x_coord, y_coord = pt
                        # transformer = pyproj.Transformer.from_crs("epsg:4326", "epsg:3577", )
                        # new_point = transformer.transform()
                        # # Use the transform in the metadata and your coordinates
                        # rowcol = rio.transform.rowcol(meta['transform'], xs=x_coord, ys=y_coord)
                        # print(f"rowcol is {rowcol}")
                        # w = geotiff_src.read(1, window=rio.windows.Window(rowcol[0], rowcol[1], 1, 1))
                        # print(f"w - rio read is {w}")

                        for val in geotiff_src.sample([(x_coord, y_coord)]):
                            if len(val) > 1:
                                print(f"something off with expected val {val}")
                            sub_val = val[0]  # there should only be one val
                            # print(f"val with transformed coords is {val}")
                            if sub_val in acceptable_land_use_codes:
                                # all good
                                insideAustralia = True
                                print(f"Land use good! {sub_val}")
                            elif insideAustralia == False:
                                print(f"landuse not okay? {sub_val}")

                    else:
                        pass
                        # print("not inside Australia...")

                property_areas.append(calculate_area(property_polygon))

                property_polygons.append(Polygon_obj)

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

    for p1 in range(0, n):
        p1_poly = property_polygons[p1]
        lat = property_coordinates[p1][1]  # y
        lon = property_coordinates[p1][0]  # x
        puff_p1 = geodesic_polygon_buffer(lat, lon, p1_poly, r)
        property_polygons_puffed.append(puff_p1)

    for p1 in range(0, n):
        neighbourhoods.append([])

        puff_p1 = property_polygons_puffed[p1]

        # loop over property list
        for p2 in range(0, n):
            # don't consider property whose neighbourhood we're calculating
            if p1 != p2:
                # calculate distance between centres
                # dist = np.linalg.norm(np.array(property_coordinates[p1]) - np.array(property_coordinates[p2]))
                dist_centres = quick_distance_haversine(
                    property_coordinates[p1], property_coordinates[p2]
                )  # distance in km

                # calculate whether they're wind-neighbours
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


def generate_properties(n, r, xrange=[150.2503, 151.39695], yrange=[-32.61181, -31.60829]):
    """Generates point-properties, without land"""

    # randomly place properties within a rectangle (bounded by xrange, yrange)
    property_coordinates = assign_coordinates(n, xrange, yrange)

    # find neighbours given neighbourhood radius
    adjacency_matrix, neighbour_pairs, neighbourhoods = assign_neighbours(property_coordinates, n, r)

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

    adjacency_matrix, neighbour_pairs, neighbourhoods, property_polygons_puffed = assign_neighbours_with_land(
        property_coordinates, property_polygons, n, wind_r
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
