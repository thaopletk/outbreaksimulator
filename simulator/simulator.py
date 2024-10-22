import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from shapely.geometry import Point
import csv
import math
import matplotlib.pyplot as plt
import simulator.spatial_setup as spatial_setup
import simulator.management as management
import simulator.premises as premises
import simulator.SEIR as SEIR
import simulator.output as output


# based from the fmdmodelling function FMD_ABM, but with modifications
# adjusted to have explicit parameter requirements rather than a dictionary with params
# average animals per hectare estimated vaguely from here, expecting that a cow needs ~10 hectares of land to raise - https://www.farmstyle.com.au/forum/raising-cattle-meat-how-many-acre


def property_setup(
    folder_path,
    n_properties=10,
    wind_r=25,
    average_property_ha=300,
    xrange=[150.2503, 151.39695],
    yrange=[-32.61181, -31.60829],
    average_animals_per_ha=0.1,
    movement_freq=14,
):

    (
        property_coordinates,
        adjacency_matrix,
        neighbour_pairs,
        neighbourhoods,
        property_polygons,
        property_polygons_puffed,
        property_areas,
    ) = spatial_setup.generate_properties_with_land(
        n_properties, wind_r, xrange, yrange, average_property_ha
    )  # uses the spatial-setup specific generator, rather than the fmdmodelling property generator

    output.plot_map_land(
        property_polygons, property_polygons_puffed, xrange, yrange, folder_path
    )

    # initialise properties
    properties = []
    for i in range(n_properties):
        # new property
        new_p = premises.Premises(
            num_animals=int(property_areas[i] * average_animals_per_ha),
            movement_freq=movement_freq,
            coordinates=property_coordinates[i],
            area_ha=property_areas[i],
            neighbourhood=neighbourhoods[i],
            property_polygon=property_polygons[i],
            property_polygon_puffed=property_polygons_puffed[i],
        )

        properties.append(new_p)
        properties[i].init_animals(
            None
        )  # init with empty "params", as no parameters are actually used to initialise animals

    property_setup_info = [
        properties,
        property_coordinates,
        adjacency_matrix,
        neighbour_pairs,
        neighbourhoods,
        property_polygons,
        property_polygons_puffed,
        property_areas,
    ]

    output.save_data_properties(property_setup_info, folder_path)

    return property_setup_info


# TODO: need to properly handle what would happen if no ideal property is found to seed
def seed_infection(xrange, yrange, properties):
    seed_property = 0  # default

    # send infection in the middle third of the map (we don't want the outbreak spreading to edges and stop simply because of the unnatural map boundaries)
    # property coordinates allocated at random, so we can just go through one-by-one to find a suitable property to see
    x_width = xrange[1] - xrange[0]
    y_width = yrange[1] - yrange[0]
    for i in range(len(properties)):
        coords = properties[i].coordinates
        if (
            coords[0] <= xrange[1] - x_width / 3
            and coords[0] >= xrange[0] + x_width / 3
            and coords[1] <= yrange[1] - y_width / 3
            and coords[1] >= yrange[0] + y_width / 3
        ):
            # seed this property
            seed_property = i
            seed_animal = 0
            break

    properties[seed_property].infection_status = 1
    properties[seed_property].animals[seed_animal].status = "infected"
    properties[seed_property].prop_infectious = 1 / properties[i].size
    properties[seed_property].cumulative_infections = 1

    return properties, seed_property


# based from the fmdmodelling function FMD_ABM, but with modifications (e.g. around saving data at various time points)
def simulate_outbreak(
    n,
    plotting,
    folder_path,
    properties,
    property_coordinates,
    xrange=[150.2503, 151.39695],
    yrange=[-32.61181, -31.60829],
    unique_output="",
    init_vax_probability=0,
    stop_time=math.inf,
):
    """Run the simulated outbreak

    n : int
        number of properties being simulated
    stop_time : int
        time in which to stop the simulation (if we want to stop it before the outbreak dies out)
    init_vax_probability : double
        the probability of properties being vaccinated before the outbreak starts spreading

    """
    total_culled = 0
    total_vaccinated = 0
    time = 0

    # limits for the figures
    xlims = [round(xrange[0], 2) - 0.005, round(xrange[1], 2) + 0.005]
    ylims = [round(yrange[0], 1) - 0.05, round(yrange[1], 1) + 0.05]

    # seed infection (in the center third)
    properties, seed_property = seed_infection(xrange, yrange, properties)

    # initialise list of cumulative infections from each property - calculated for FOI every loop
    cumulative_infection_proportions = list(np.zeros(n))
    cumulative_infection_proportions[seed_property] = (
        properties[seed_property].cumulative_infections / properties[seed_property].size
    )

    # set up some random initial vaccination
    for i, premise in enumerate(properties):
        if premise.infection_status != 1:
            premise.vaccination(
                init_vax_probability, properties, time, culled_neighbours_only=False
            )

    output.plot_map(
        properties,
        property_coordinates,
        time,
        xlims=xlims,
        ylims=ylims,
        folder_path=folder_path,
    )

    # spread begins here:

    FOI = list(np.zeros(n))
    plt.figure()
    # start time loop
    infected_properties = 1  # so the while loop begins
    while infected_properties > 0 and time < stop_time:
        time += 1

        controlzone = None

        if time >= params["policy_start"]:
            # break/remove neighbour lines at radius r<= 'policy_r' around reported properties
            coordlist_of_infected_properties = []
            for i, premise in enumerate(properties):
                if premise.reported_status == True:
                    coordlist_of_infected_properties.append(premise.coordinates)

            if coordlist_of_infected_properties != []:

                controlzone = management.define_control_zone_circles(
                    coordlist_of_infected_properties, params["policy_r"]
                )

                for i, premise in enumerate(properties):
                    if controlzone.contains(Point(premise.coordinates)):
                        old_neighbourhood = premise.neighbourhood
                        premise.neighbourhood = []
                        premise.total_neighbours = 0
                        # go through the old neighbours and remove their connection to this neighbour
                        for farm in old_neighbourhood[:]:
                            index = farm[0]
                            neighbour = properties[index]
                            neighbour_of_neighbour = neighbour.neighbourhood
                            for x in neighbour_of_neighbour[:]:
                                if x[0] == i:
                                    neighbour.neighbourhood.remove(x)
                                    break

        infected_properties = 0
        for i, premise in enumerate(properties):
            if not premise.culled_status:
                FOI[i] = SEIR.calculate_force_of_infection(properties, i, params)

        # run infection model for each property
        for i, premise in enumerate(properties):
            # if the property has not been culled
            if not premise.culled_status:
                # run infection model and update infection numbers
                premise.infection_model(params, FOI[i], time)
                cumulative_infection_proportions[i] = (
                    premise.cumulative_infections / premise.size
                )

                # does the property vaccinate?
                # property can only vaccinate if they are not infected already
                if not premise.infection_status:
                    # calculate infected neighbours
                    if len(premise.neighbourhood):  # premise has neighbours
                        neighbours = [el[0] for el in premise.neighbourhood]
                        culled_neighbours = sum(
                            [properties[i].culled_status for i in neighbours]
                        )
                        prop_culled_neighbours = (
                            culled_neighbours / premise.total_neighbours
                        )
                    else:  # no neighbours
                        prop_culled_neighbours = 0

                    premise.vaccination(params, properties, time)
                # does the property report?
                # property can only report if they are infected and have not been culled yet
                else:
                    infected_properties += 1  # counting infected properties while we're considering infected properties
                    premise.reporting(params, time)
            # if property has been culled
            else:
                # keeping track of infected_proportions for all properties
                cumulative_infection_proportions[i] = 0

        if plotting:
            # plot_graph(properties, property_coordinates, time,folder_path)
            output.plot_map(
                properties,
                property_coordinates,
                time,
                xlims=xlims,
                ylims=ylims,
                folder_path=folder_path,
                real_situation=True,
                controlzone=controlzone,
            )
            output.plot_map(
                properties,
                property_coordinates,
                time,
                xlims=xlims,
                ylims=ylims,
                folder_path=folder_path,
                real_situation=False,
                controlzone=controlzone,
            )
            output.save_data(
                properties, property_coordinates, time, controlzone, folder_path
            )

    if plotting:
        output.make_video(folder_path, "map_underlying")
        output.make_video(folder_path, "map_apparent")

    for premise in properties:
        if premise.culled_status:
            total_culled += 1
        if premise.vaccination_status:
            total_vaccinated += 1

    # print output
    header = [
        "id",
        "status",
        "ip",
        "exposure_date",
        "clinical_date",
        "notification_date",
        "removal_date",
        "recovery_date",
        "vacc_date",
        "region",
        "county",
        "cluster",
        "xcoord",
        "ycoord",
        "area",
        "type",
        "total",
    ]
    file = os.path.join(folder_path, f"fake_data{unique_output}.csv")
    with open(file, "w", newline="") as f:

        # create the csv writer
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

        for premise in properties:
            row = premise.return_output_row()
            writer.writerow(row)

    return total_culled, total_vaccinated
