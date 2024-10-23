import geopandas as gpd
import pyproj
from functools import partial
from shapely.geometry import Polygon, Point, LineString, MultiPolygon
from shapely.ops import transform, unary_union
from simulator.premises import convert_time_to_date


def geodesic_point_buffer(lat, lon, km):
    # Azimuthal equidistant projection
    proj_wgs84 = pyproj.Proj(init="epsg:4326")

    aeqd_proj = "+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0"
    project = partial(
        pyproj.transform, pyproj.Proj(aeqd_proj.format(lat=lat, lon=lon)), proj_wgs84
    )
    buf = Point(0, 0).buffer(km * 1000)  # distance in metres
    return transform(project, buf).exterior.coords[:]


def define_control_zone_circles(coordinates, radius_km):
    list_of_polygons = []

    for site in coordinates:
        x = site[0]  # longitude
        y = site[1]  # latitude
        points_in_circle = geodesic_point_buffer(y, x, radius_km)
        poly = Polygon(points_in_circle)
        list_of_polygons.append(poly)

    controlzone = unary_union(list_of_polygons)

    return controlzone


# could probably run this recursively
def contact_tracing(property_index, movement_records, time):
    """Contact tracing

    assumes records in form [time, property index from, property index to, string-report] (should do a check)

    """

    contact_tracing_report = f"DAY {convert_time_to_date(time)} - contact tracing report compiled for movements from property index {property_index}\n"
    traced_property_indices = []

    if len(movement_records) != 0:
        # check the length of movement records (a minimum requirement)
        if len(movement_records[0]) == 4:

            # go through the movement records, and look for animal movements off the property
            for record in movement_records:
                if record[1] == property_index:
                    traced_property_indices.append(record[2])
                    contact_tracing_report = (
                        contact_tracing_report + " - " + record[3] + "\n"
                    )

    return contact_tracing_report, traced_property_indices


def testing(properties, property_indices, time):
    """Testing

    Conducts testing on the property indices

    """
    pass
