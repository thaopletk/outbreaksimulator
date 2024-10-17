import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),".."))

import simulator.spatial_setup as spatial_setup

def test_assign_coordinates():
    num = 5
    assert len(spatial_setup.assign_coordinates(num))==num

def test_assign_property_locations():
    num = 5 
    xrange = [150.2503,151.39695]
    yrange = [-32.61181, -31.60829]
    results =  spatial_setup.assign_property_locations(num, xrange, yrange)
    assert len(results)==3

    property_coordinates, property_polygons, property_areas = results 

    # test that the values lie within the stated range

    assert all(property_coordinates[:,0]>=xrange[0]) 
    assert all(property_coordinates[:,0]<=xrange[1]) 
    assert all(property_coordinates[:,1]>=yrange[0]) 
    assert all(property_coordinates[:,1]<=yrange[1]) 

    # test that all polygons are non-overlapping...
    # TODO