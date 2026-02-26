"""SEIR (susceptible, exposed, infectious, recovered)

Adapted from FOI_calculation_fns.py in FMD_modelling
"""

import sys
import os
import rasterio
import numpy as np
import geopandas as gpd
import xarray as xr

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "FMD_modelling"))
import FMD_modelling.FOI_calculation_fns as FOI_calculation_fns
from simulator.spatial_functions import (
    calculate_area,
    quick_distance_haversine,
    geodesic_point_buffer,
)
import functools
import datetime

from shapely.ops import nearest_points
from shapely.geometry import Point, Polygon
from simulator.premises import convert_date_to_time, get_current_datetime


# https://stackoverflow.com/questions/8118679/python-rounding-by-quarter-intervals
def roundPartial(value, resolution):
    return round(value / resolution) * resolution


@functools.lru_cache(maxsize=None)
def get_wind_direction_dict(time):
    """Wind direction

    Data downloaded from https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels?tab=download

    """
    current_datetime = get_current_datetime(time)
    if current_datetime >= datetime.datetime(year=2026, month=1, day=31):
        dataset = "climatedatastore_wind_2026-01-31-0900.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=30):
        dataset = "climatedatastore_wind_2026-01-28-1800.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=29):
        dataset = "climatedatastore_wind_2026-01-29-0900.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=28):
        dataset = "climatedatastore_wind_2026-01-28-1700.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=27):
        dataset = "climatedatastore_wind_2026-01-22-2200.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=26):
        dataset = "climatedatastore_wind_2026-01-26-1600.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=25):
        dataset = "climatedatastore_wind_2026-01-25-1500.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=24):
        dataset = "climatedatastore_wind_2026-01-24-1400.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=23):
        dataset = "climatedatastore_wind_2026-01-23-1300.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=22):
        dataset = "climatedatastore_wind_2026-01-22-2000.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=21):
        dataset = "climatedatastore_wind_2026-01-21-1200.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=20):
        dataset = "climatedatastore_wind_2026-01-20-1100.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=19):
        dataset = "climatedatastore_wind_2026-01-19-1000.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=18):
        dataset = "climatedatastore_wind_2026-01-18-0500.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=17):
        dataset = "climatedatastore_wind_2026-01-17-0600.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=16):
        dataset = "climatedatastore_wind_2026-01-16-1500.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=15):
        dataset = "climatedatastore_wind_2026-01-15-1100.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=12):
        dataset = "climatedatastore_wind_2026-01-12-1600.nc"
    elif current_datetime >= datetime.datetime(year=2026, month=1, day=9):
        dataset = "climatedatastore_wind_2026-01-09-0900.nc"
    else:
        dataset = "climatedatastore_wind_2026-01-01-1300.nc"

    ds = xr.open_dataset(os.path.join(os.path.dirname(__file__), "..", "data", "wind", dataset))
    df = ds.to_dataframe()
    wind_direction_dict = df.groupby(["longitude", "latitude"]).apply(lambda x: x[["u10", "v10"]].to_dict(orient="records")).to_dict()

    return wind_direction_dict


def get_wind_direction(coordinates, time):
    wind_direction_dict = get_wind_direction_dict(time)

    rounded_coords = (roundPartial(coordinates[0], 0.25), roundPartial(coordinates[1], 0.25))

    u10 = wind_direction_dict[rounded_coords][0]["u10"]
    v10 = wind_direction_dict[rounded_coords][0]["v10"]

    return u10, v10


@functools.lru_cache(maxsize=None)
def get_ducks():
    ducks_file = os.path.join(os.path.dirname(__file__), "..", "data", "wildlife", "pabduc1_abundance_seasonal_year_round_mean_2023.tif")
    ducks_img = rasterio.open(ducks_file)
    return ducks_img, ducks_img.statistics(1).max  # around 100


def vector_val_HPAI(premise_coordinates):
    ducks_img, max_val = get_ducks()

    points = gpd.GeoSeries([Point(premise_coordinates[0], premise_coordinates[1])], crs=4326)  # Geographic WGS 84 - degrees
    points = points.to_crs(8857)  # Projected WGS 84 - meters - format the tif file is in
    vector_val = ([x for x in ducks_img.sample([[points.x[0], points.y[0]]])][0][0]) / max_val * 10

    return vector_val


def wind_dispersal_FOI(properties, premise_index, r_wind, beta_wind, vector_mortality_rate=0.04, outbreak_sim="LSD", time=0):
    """Adapted from FMD modelling code

    In order to change the definition of circle creation

    """
    FOI = 0

    if outbreak_sim == "LSD":
        # vector modification
        vectors_file = os.path.join(
            os.path.dirname(__file__), "vectors_rangebag.tif"
        )  # Proj_current_Philaenus.spumarius..Linnaeus..1758._rangebag.tif from Biosecurity Commons
        vectors_img = rasterio.open(vectors_file)
        vector_val = [x for x in vectors_img.sample([properties[premise_index].coordinates])][0][0]
    else:
        vector_val = vector_val_HPAI(properties[premise_index].coordinates)

    # contribution from property i (on itself???)
    C_i = properties[premise_index].cumulative_infections
    A_i = properties[premise_index].area

    # area of safe radius disc
    # unsafe dist is the puffed polygons!
    # unsafe_disc_i = properties[premise_index].puff_poly
    A_is = properties[premise_index].puffed_poly_area

    if isinstance(beta_wind, dict):
        animal_type_i = properties[premise_index].animal_type
        FOI += vector_val * beta_wind[animal_type_i] * C_i * A_i / A_is
    else:
        FOI += vector_val * beta_wind * C_i * A_i / A_is

    property_i_polygon = properties[premise_index].polygon

    # contributions from neighbouring properties
    for [index, dist_centres] in properties[premise_index].neighbourhood:
        if outbreak_sim == "HPAI":
            # check if the neighbouring property is along the correct wind direction
            neighbour = properties[index]
            u10, v10 = get_wind_direction(neighbour.coordinates, time)

            x0, y0 = neighbour.coordinates
            minx, miny, maxx, maxy = neighbour.puffed_poly.bounds

            if u10 > 0 and v10 > 0:
                # top right
                sector_square = Polygon([(x0, y0), (maxx, y0), (maxx, maxy), (x0, maxy), (x0, y0)])
            elif u10 > 0 and v10 < 0:
                # bottom  right
                sector_square = Polygon([(x0, y0), (maxx, y0), (maxx, miny), (x0, miny), (x0, y0)])
            elif u10 < 0 and v10 < 0:
                # bottom left
                sector_square = Polygon([(x0, y0), (x0, miny), (minx, miny), (minx, y0), (x0, y0)])
            elif u10 < 0 and v10 > 0:
                # top left
                sector_square = Polygon([(x0, y0), (minx, y0), (minx, maxy), (x0, maxy), (x0, y0)])
            else:
                raise ValueError(f"Unexpected u10 {u10}, v10 {v10}")

            unsafe_disc_j = sector_square.intersection(neighbour.puffed_poly)
            A_js = calculate_area(unsafe_disc_j)
        else:
            # calculating area overlap
            unsafe_disc_j = properties[index].puffed_poly
            A_js = properties[index].puffed_poly_area  # area of unsafe_disc_j of properties[index]

        C_j = properties[index].cumulative_infections
        A_ijs = calculate_area(property_i_polygon.intersection(unsafe_disc_j))

        # calculating min distance centre j to boundary of i, in km
        p1, p2 = nearest_points(property_i_polygon, Point(*properties[index].coordinates))

        d_ij = quick_distance_haversine([p1.x, p1.y], [p2.x, p2.y])
        distance_modifier = max(0.001, 1 - (d_ij / r_wind))

        if outbreak_sim == "LSD":
            # vector-relevant parts
            vector_val_neighbour = [x for x in vectors_img.sample([properties[index].coordinates])][0][0]
            # also, if this neighbouring property has already been culled, then calculate how long they have been culled, and implement a basic death rate for the vectors
            vector_mortality_adjustment = 1
            if properties[index].culled_status:
                days_since_culled = convert_date_to_time(properties[index].removal_date)
                vector_mortality_adjustment = 0.1 * np.exp(-vector_mortality_rate * days_since_culled)
            elif properties[index].reported_status or properties[index].clinical_report_outcome == True:
                vector_mortality_adjustment = 0.3  # assuming that they enact some vector control just in case
            elif properties[index].undergoing_testing:
                vector_mortality_adjustment = 0.5  # assuming they do some just in case
        elif outbreak_sim == "HPAI":
            vector_val_neighbour = vector_val_HPAI(properties[index].coordinates)
            vector_mortality_adjustment = 1  # TODO | this basically assumes that the virus remains in the environment....

        # update FOI
        if isinstance(beta_wind, dict):
            animal_type_j = properties[index].animal_type
            FOI += vector_mortality_adjustment * vector_val_neighbour * beta_wind[animal_type_j] * C_j * distance_modifier * A_ijs / A_js
        else:
            FOI += vector_mortality_adjustment * vector_val_neighbour * beta_wind * C_j * distance_modifier * A_ijs / A_js

    return FOI


def calculate_force_of_infection(properties, premise_index, vax_modifier, r_wind, beta_wind, beta_animal, outbreak_sim="LSD", time=0):
    """Calculate the force of infection
    Adapted from the FOI calculations from the FMD modelling code
    Reason: due to the differing units...
    """
    vax_status = (vax_modifier - 1) * properties[premise_index].vaccination_status + 1

    FOI_wind = wind_dispersal_FOI(properties, premise_index, r_wind, beta_wind, outbreak_sim=outbreak_sim, time=time)
    if isinstance(beta_animal, dict):
        animal_type_i = properties[premise_index].animal_type
        FOI_animal = FOI_calculation_fns.animal_FOI(properties[premise_index], {"beta_animal": beta_animal[animal_type_i]})
    else:
        FOI_animal = FOI_calculation_fns.animal_FOI(properties[premise_index], {"beta_animal": beta_animal})

    FOI = vax_status * (FOI_animal + FOI_wind)

    return FOI


def calculate_FOI_point_properties(premise, params, infected_props):
    """Calculates the force of infections, assuming point-properties (no area used)
    From FMD_modelling, before area was implemented
    """

    x = 0

    vax_status = (params["vax_modifier"] - 1) * premise.vaccination_status + 1

    # farm = [index, dist]
    for farm in premise.neighbourhood:
        index = farm[0]
        dist = farm[1]
        x += (1 - (dist / params["r"])) * infected_props[index]

    FOI = (params["beta_between"] * x + params["beta_within"] * premise.prop_infectious) * vax_status

    return FOI
