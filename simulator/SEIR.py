""" SEIR (susceptible, exposed, infectious, recovered)

    Adapted from FOI_calculation_fns.py in FMD_modelling
"""

import sys
import os
import rasterio
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "FMD_modelling"))
import FMD_modelling.FOI_calculation_fns as FOI_calculation_fns
from simulator.spatial_functions import (
    calculate_area,
    quick_distance_haversine,
    geodesic_point_buffer,
)

from shapely.ops import nearest_points
from shapely.geometry import Point, Polygon
from simulator.premises import convert_date_to_time


def wind_dispersal_FOI(properties, premise_index, r_wind, beta_wind, vector_mortality_rate=0.04):
    """Adapted from FMD modelling code

    In order to change the definition of circle creation

    """
    FOI = 0

    # vector modification
    vectors_file = os.path.join(
        os.path.dirname(__file__), "vectors_rangebag.tif"
    )  # Proj_current_Philaenus.spumarius..Linnaeus..1758._rangebag.tif from Biosecurity Commons
    vectors_img = rasterio.open(vectors_file)

    # contribution from property i
    C_i = properties[premise_index].cumulative_infections
    A_i = properties[premise_index].area

    # area of safe radius disc
    # unsafe dist is the puffed polygons!
    # unsafe_disc_i = properties[premise_index].puff_poly
    A_is = properties[premise_index].puffed_poly_area

    vector_val = [x for x in vectors_img.sample([properties[premise_index].coordinates])][0][0]

    if isinstance(beta_wind, dict):
        animal_type_i = properties[premise_index].animal_type
        FOI += vector_val * beta_wind[animal_type_i] * C_i * A_i / A_is
    else:
        FOI += vector_val * beta_wind * C_i * A_i / A_is

    property_i_polygon = properties[premise_index].polygon

    # contributions from neighbouring properties
    for [index, dist_centres] in properties[premise_index].neighbourhood:
        C_j = properties[index].cumulative_infections

        # calculating area overlap
        unsafe_disc_j = properties[index].puffed_poly
        A_js = properties[index].puffed_poly_area  # area of unsafe_disc_j of properties[index]

        A_ijs = calculate_area(property_i_polygon.intersection(unsafe_disc_j))

        # calculating min distance centre j to boundary of i, in km
        p1, p2 = nearest_points(property_i_polygon, Point(*properties[index].coordinates))

        d_ij = quick_distance_haversine([p1.x, p1.y], [p2.x, p2.y])
        distance_modifier = max(0.001, 1 - (d_ij / r_wind))

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

        # update FOI
        if isinstance(beta_wind, dict):
            animal_type_j = properties[index].animal_type
            FOI += (
                vector_mortality_adjustment
                * vector_val_neighbour
                * beta_wind[animal_type_j]
                * C_j
                * distance_modifier
                * A_ijs
                / A_js
            )
        else:
            FOI += (
                vector_mortality_adjustment * vector_val_neighbour * beta_wind * C_j * distance_modifier * A_ijs / A_js
            )

    return FOI


def calculate_force_of_infection(properties, premise_index, vax_modifier, r_wind, beta_wind, beta_animal):
    """Calculate the force of infection
    Adapted from the FOI calculations from the FMD modelling code
    Reason: due to the differing units...
    """
    vax_status = (vax_modifier - 1) * properties[premise_index].vaccination_status + 1

    FOI_wind = wind_dispersal_FOI(properties, premise_index, r_wind, beta_wind)
    if isinstance(beta_animal, dict):
        animal_type_i = properties[premise_index].animal_type
        FOI_animal = FOI_calculation_fns.animal_FOI(
            properties[premise_index], {"beta_animal": beta_animal[animal_type_i]}
        )
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
