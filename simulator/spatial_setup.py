#
# Spatial setup
# Written by Isobel Abell and adapted by Thao Le
# (overriding the spatial setup code from FMD_modelling)
#

import numpy as np 
import math
import matplotlib.pyplot as plt

# Generate random graph given n and r
def assign_coordinates(n, xrange = [150.2503,151.39695], yrange = [-32.61181, -31.60829]):
    property_coordinates = np.zeros((n, 2))
    for i in range(n):
        x = np.random.uniform(*xrange)
        y = np.random.uniform(*yrange)
        property_coordinates[i,0] = x
        property_coordinates[i,1] = y

    return property_coordinates



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
                    neighbourhoods[p1].append([p2, dist])

                    neighbour_pairs.append([x,y])

    return adjacency_matrix, neighbour_pairs, neighbourhoods


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