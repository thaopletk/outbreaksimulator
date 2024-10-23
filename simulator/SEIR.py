import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "FMD_modelling"))
import FMD_modelling.FOI_calculation_fns as FOI_calculation_fns
from simulator.management import geodesic_point_buffer
from simulator.spatial_setup import calculate_area
from simulator.spatial_setup import quick_distance_haversine

from shapely.ops import nearest_points
from shapely.geometry import Point, Polygon


def wind_dispersal_FOI(properties, premise_index, r_wind, beta_wind):
    """Adapted from FMD modelling code

    In order to change the definition of circle creation

    """
    FOI = 0

    # contribution from property i
    C_i = properties[premise_index].cumulative_infections
    A_i = properties[premise_index].area

    # area of safe radius disc
    # unsafe dist is the puffed polygons!
    # unsafe_disc_i = properties[premise_index].puff_poly
    A_is = properties[premise_index].puffed_poly_area

    FOI += beta_wind * C_i * A_i / A_is

    property_i_polygon = properties[premise_index].polygon

    # contributions from neighbouring properties
    for [index, dist_centres] in properties[premise_index].neighbourhood:
        C_j = properties[index].cumulative_infections

        # calculating area overlap
        unsafe_disc_j = properties[index].puff_poly
        A_js = properties[
            index
        ].puffed_poly_area  # area of unsafe_disc_j of properties[index]

        A_ijs = calculate_area(property_i_polygon.intersection(unsafe_disc_j))

        # calculating min distance centre j to boundary of i, in km
        p1, p2 = nearest_points(
            property_i_polygon, Point(*properties[index].coordinates)
        )

        d_ij = quick_distance_haversine([p1.x, p1.y], [p2.x, p2.y])
        distance_modifier = max(0, 1 - (d_ij / r_wind))

        # update FOI
        FOI += beta_wind * C_j * distance_modifier * A_ijs / A_js

    return FOI


def calculate_force_of_infection(
    properties, premise_index, vax_modifier, r_wind, beta_wind, beta_animal
):
    """Calculate the force of infection
    Adapted from the FOI calculations from the FMD modelling code
    Reason: due to the differing units...
    """
    vax_status = (vax_modifier - 1) * properties[premise_index].vaccination_status + 1

    FOI_wind = wind_dispersal_FOI(properties, premise_index, r_wind, beta_wind)
    FOI_animal = FOI_calculation_fns.animal_FOI(
        properties[premise_index], {"beta_animal": beta_animal}
    )

    FOI = vax_status * (FOI_animal + FOI_wind)

    return FOI


# does not use or require property area / radius
def calculate_FOI_point_properties(premise, params, infected_props):
    # FOI = beta * [(vax - 1)*vax_status + 1] * x
    x = 0

    vax_status = (params["vax_modifier"] - 1) * premise.vaccination_status + 1

    # farm = [index, dist]
    for farm in premise.neighbourhood:
        index = farm[0]
        dist = farm[1]
        x += (1 - (dist / params["r"])) * infected_props[index]

    FOI = (
        params["beta_between"] * x + params["beta_within"] * premise.prop_infectious
    ) * vax_status

    return FOI
