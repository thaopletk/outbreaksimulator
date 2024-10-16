#
# Spatial setup
# Written by Isobel Abell and adapted by Thao Le
# (overriding the spatial setup code from FMD_modelling)
# i.e. from generate_property_grid.py
#

import numpy as np 
import math
import matplotlib.pyplot as plt
import simulator.random_rectangles as random_rectangles
import pyproj
from shapely.geometry import shape
from area import area


# Generate random graph given n and r
def assign_coordinates(n, xrange = [150.2503,151.39695], yrange = [-32.61181, -31.60829]):
    property_coordinates = np.zeros((n, 2))
    for i in range(n):
        x = np.random.uniform(*xrange)
        y = np.random.uniform(*yrange)
        property_coordinates[i,0] = x
        property_coordinates[i,1] = y

    return property_coordinates


def assign_property_locations(n, xrange = [150.2503,151.39695], yrange = [-32.61181, -31.60829]):
    # first, make rectangles

    # to estimate the number of rectangles, I need to get the total area of xrange, yrange, and divide it up by the average property size that I want
    # the average property size is 300 hectares, or 3 km^2, taken from https://www.agriculture.gov.au/abares/research-topics/surveys/dairy#farm-characteristics 

    bounding_polygon =  {'type':'Polygon','coordinates':[[[xrange[0],yrange[0]],[xrange[1],yrange[0]],[xrange[1],yrange[1]],[xrange[0],yrange[1]],[xrange[0],yrange[0]]]]}
    bounding_area = area(bounding_polygon) # it's not exact-exact but should be good enough, value in square metres
    sq_to_ha = 0.0001
    area_in_hectares = sq_to_ha*bounding_area
    average_property_ha = 300

    num_recs_to_generate = int(np.ceil(area_in_hectares/average_property_ha))
    num_rectangles = n 

    #  x1, y1, x2, y2
    region = random_rectangles.Rect(xrange[0], yrange[0], xrange[1], yrange[1])
    random_recs = random_rectangles.return_random_rectangles(num_rectangles, num_recs_to_generate, region )
    # the resultant rectangles are the properties 

    property_coordinates = np.zeros((n, 2))
    property_polygons = []

    for i in range(n):
        rectangle = random_recs[i]
        # make polygons 
        property_polygon = {'type':'Polygon',
                            'coordinates':[[ [rectangle.min.x,rectangle.min.y],
                                             [rectangle.max.x,rectangle.min.y],
                                             [rectangle.max.x,rectangle.max.y],
                                             [rectangle.min.x,rectangle.max.y],
                                             [rectangle.min.x,rectangle.min.y]]]}
        property_polygons.append(property_polygon)

        property_coordinates[i,0] = (rectangle.min.x+rectangle.max.x)/2
        property_coordinates[i,1] = (rectangle.min.y+rectangle.max.y)/2

    return property_coordinates, property_polygons


#https://stackoverflow.com/questions/15736995/how-can-i-quickly-estimate-the-distance-between-two-latitude-longitude-points
def quick_distance_haversine(coords1,coords2):
    x1,y1 = coords1
    x2,y2 = coords2

    lon1 =x1
    lat1 = y1
    lon2 =x2
    lat2 = y2
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    # Radius of earth in kilometers is 6371
    km = 6371 * c
    return km


def assign_neighbours(property_coordinates, n, r):
    adjacency_matrix = np.zeros((n,n))
    neighbourhoods = []
    neighbour_pairs = []

    for p1 in range(n): 
        neighbourhoods.append([])
        for p2 in range(n):
            if p1 != p2:
                # dist = np.linalg.norm(np.array(property_coordinates[p1]) - np.array(property_coordinates[p2]))
                dist = quick_distance_haversine(property_coordinates[p1], property_coordinates[p2]) # distance in km

                if dist <= r:
                    # close enough => neighbours
                    adjacency_matrix[p1, p2] = 1
                    adjacency_matrix[p2, p1] = 1
                    x = [property_coordinates[p1, 0], property_coordinates[p2, 0]]
                    y = [property_coordinates[p1, 1], property_coordinates[p2, 1]]

                    # indices of properties neighbouring property p1
                    neighbourhoods[p1].append([p2, dist, dist]) # TODO technically there should be multiple distances here, between boundaries and between centers

                    neighbour_pairs.append([x,y])

    return adjacency_matrix, neighbour_pairs, neighbourhoods


def assign_neighbours_with_land(property_coordinates,property_polygons, n, r):
    adjacency_matrix = np.zeros((n,n))
    neighbourhoods = []
    neighbour_pairs = []

    for p1 in range(n): 
        neighbourhoods.append([])
        # loop over property list
        for p2 in range(n):
            # don't consider property whose neighbourhood we're calculating
            if p1 != p2:
                # calculate distance between centres
                # dist = np.linalg.norm(np.array(property_coordinates[p1]) - np.array(property_coordinates[p2]))
                dist_centres = quick_distance_haversine(property_coordinates[p1], property_coordinates[p2]) # distance in km

                # calculate minimum distance between borders
                # TODO/ in progress


def plot_coordinates(property_coordinates, neighbour_pairs):
    plt.figure()
    
    # nodes 
    for i in range(len(property_coordinates)):
        if i == 3:
            plt.scatter(property_coordinates[i,0], property_coordinates[i,1], color = 'red')
        else:
            plt.scatter(property_coordinates[i,0], property_coordinates[i,1], color = 'purple')

    # edges
    for node_coordinates in neighbour_pairs:
        plt.plot(node_coordinates[0], node_coordinates[1], alpha = 0.2)

    plt.show()

    return 


def generate_properties(n, r,  xrange = [150.2503,151.39695], yrange = [-32.61181, -31.60829]):

    # randomly place properties within a rectangle (bounded by xrange, yrange)
    property_coordinates = assign_coordinates(n, xrange, yrange)

    # find neighbours given neighbourhood radius
    adjacency_matrix, neighbour_pairs, neighbourhoods = assign_neighbours(property_coordinates, n, r)

    # plot_coordinates(property_coordinates, neighbour_pairs)

    return property_coordinates, adjacency_matrix, neighbour_pairs, neighbourhoods