import geopandas as gpd
import pyproj
from functools import partial
from shapely.geometry import Polygon,Point, LineString, MultiPolygon
from shapely.ops import transform, unary_union

def geodesic_point_buffer(lat, lon, km):
    # Azimuthal equidistant projection
    proj_wgs84 = pyproj.Proj(init='epsg:4326')


    aeqd_proj = '+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0'
    project = partial(
        pyproj.transform,
        pyproj.Proj(aeqd_proj.format(lat=lat, lon=lon)),
        proj_wgs84)
    buf = Point(0, 0).buffer(km * 1000)  # distance in metres
    return transform(project, buf).exterior.coords[:]

def define_control_zone_circles(coordinates,radius_km):
    list_of_polygons = []


    for site in coordinates:
        x = site[0] # longitude
        y = site[1] # latitude
        points_in_circle = geodesic_point_buffer(y, x,  radius_km)
        poly = Polygon(points_in_circle)
        list_of_polygons.append(poly)

    controlzone = unary_union(list_of_polygons)

    return controlzone
    