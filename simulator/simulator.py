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
import FMD_modelling.animal_movement_code as animal_movement_code


# based from the fmdmodelling function FMD_ABM, but with modifications
# adjusted to have explicit parameter requirements rather than a dictionary with params
# average animals per hectare estimated vaguely from here, expecting that a cow needs ~10 hectares of land to raise - https://www.farmstyle.com.au/forum/raising-cattle-meat-how-many-acre


# TODO this could be moved into the spatial_setup file...
def property_setup(
    folder_path,
    n=10,
    r_wind=25,
    average_property_ha=300,
    xrange=[150.2503, 151.39695],
    yrange=[-32.61181, -31.60829],
    average_animals_per_ha=0.1,
    movement_frequency=14,
    **_,
):
    """

    n: int
        Number of properties
    """

    (
        property_coordinates,
        adjacency_matrix,
        neighbour_pairs,
        neighbourhoods,
        property_polygons,
        property_polygons_puffed,
        property_areas,
    ) = spatial_setup.generate_properties_with_land(
        n, r_wind, xrange, yrange, average_property_ha
    )  # uses the spatial-setup specific generator, rather than the fmdmodelling property generator

    output.plot_map_land(
        property_polygons, property_polygons_puffed, xrange, yrange, folder_path
    )

    # initialise properties
    properties = []
    for i in range(n):
        # new property
        new_p = premises.Premises(
            num_animals=max(
                int(property_areas[i] * average_animals_per_ha), 1
            ),  # at least one animal per property
            movement_freq=movement_frequency,
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


def seed_infection(xrange, yrange, properties):
    seed_property = 0  # default
    seed_animal = 0

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
            break

    properties[seed_property].infection_status = 1
    properties[seed_property].animals[seed_animal].status = "infected"
    properties[seed_property].prop_infectious = 1 / properties[seed_property].size
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
    vax_modifier=0.4,
    r_wind=25,
    beta_wind=0.01,
    beta_animal=2,
    latent_period=2,
    infectious_period=2,
    preclinical_period=2,
    prob_vaccinate=0.5,
    clinical_reporting_threshold=0.01,
    prob_report=0.8,
    movement_frequency=10,
    movement_probability=0.1,
    movement_prop_animals=0.1,
    **_,
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
    controlzone = None

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

    if plotting:
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

    report = ""

    # spread begins here:

    FOI = list(np.zeros(n))
    plt.figure()
    # start time loop
    infected_sum = 1  # so the while loop begins
    while infected_sum > 0 and time < stop_time:
        time += 1

        # TODO : no controls for now, will update later
        # if time >= params["policy_start"]:
        #     # break/remove neighbour lines at radius r<= 'policy_r' around reported properties
        #     coordlist_of_infected_properties = []
        #     for i, premise in enumerate(properties):
        #         if premise.reported_status == True:
        #             coordlist_of_infected_properties.append(premise.coordinates)

        #     if coordlist_of_infected_properties != []:

        #         controlzone = management.define_control_zone_circles(
        #             coordlist_of_infected_properties, params["policy_r"]
        #         )

        #         for i, premise in enumerate(properties):
        #             if controlzone.contains(Point(premise.coordinates)):
        #                 old_neighbourhood = premise.neighbourhood
        #                 premise.neighbourhood = []
        #                 premise.total_neighbours = 0
        #                 # go through the old neighbours and remove their connection to this neighbour
        #                 for farm in old_neighbourhood[:]:
        #                     index = farm[0]
        #                     neighbour = properties[index]
        #                     neighbour_of_neighbour = neighbour.neighbourhood
        #                     for x in neighbour_of_neighbour[:]:
        #                         if x[0] == i:
        #                             neighbour.neighbourhood.remove(x)
        #                             break

        # calculate FOI for each property

        for i, premise in enumerate(properties):
            if not premise.culled_status:
                FOI[i] = SEIR.calculate_force_of_infection(
                    properties, i, vax_modifier, r_wind, beta_wind, beta_animal
                )

        # vaccinate properties around culled (reported) properties
        for premise in properties:
            if not premise.culled_status and not premise.infection_status:
                premise.vaccination(
                    prob_vaccinate, properties, time, culled_neighbours_only=True
                )

        # check if any properties now want to report
        for premise in properties:
            if not premise.culled_status:
                report += premise.reporting(
                    clinical_reporting_threshold, prob_report, time
                )

        # run infection model for each property
        for i, premise in enumerate(properties):
            premise.infection_model(
                latent_period, infectious_period, preclinical_period, FOI[i], time
            )

        # movement of animals
        animal_movement_code.animal_movement(
            properties,
            {
                "n": n,
                "movement_frequency": movement_frequency,
                "movement_probability": movement_probability,
                "movement_prop_animals": movement_prop_animals,
            },
            time,
        )

        # update counts
        # simulation ends when infected_sum = 0
        infected_sum = 0
        for i, premise in enumerate(properties):
            premise.update_counts()
            # TODO something like premise.update_status() # in the case all infected animals recover or are moved off the property, it may be considered no longer infected? or, to state "contaminated"
            # though in that case, the fomites should still be there -- noted under cumulative infections...?
            if not premise.culled_status:
                cumulative_infection_proportions[i] = (
                    premise.cumulative_infections / len(premise.animals)
                )
                infected_sum += premise.number_infected

        if plotting:
            output.plot_map(
                properties,
                property_coordinates,
                time,
                xlims=xlims,
                ylims=ylims,
                folder_path=folder_path,
                real_situation=True,
                controlzone=controlzone,
                infectionpoly=False,
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
                infectionpoly=False,
            )
            output.save_data(
                properties, property_coordinates, time, controlzone, folder_path
            )

    if plotting:
        output.make_video(folder_path, "map_underlying")
        output.make_video(folder_path, "map_apparent")

    # statistics from end of simulation
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

    # output "reports" report
    with open(os.path.join(folder_path, "report.txt"), "w") as file:
        file.write(report)

    return total_culled, total_vaccinated
