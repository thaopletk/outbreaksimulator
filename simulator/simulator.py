"""Simulator

    Runs parts of the simulation. Adapted from FMD_modelling, abm_fn.py
    Adjusted to have explicit parameter requirements rather than a dictionary with params

    Typical workflow involves calling:
    * property_setup
    * simulate_outbreak

"""

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
import simulator.animal_movement as animal_movement


#
#


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
        Number of properties to generate
    r_wind : int, double
        Distance in kilometers, to define wind neighbours
    average_property_ha : int, double
        Not actually the average property hectares generated at the moment... but as a rough guide (TODO - adjust generation to make this value the actual average?)
    average_animals_per_ha : double
        Average number of animals per hectare, to initialise properties
        The default value comes from https://www.farmstyle.com.au/forum/raising-cattle-meat-how-many-acre where a cow needs ~10 hectares of land to raise
    movement_frequency : int
        Properties might move animals every x days
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
    """Send infection in the middle third of the map if possible (we don't want the outbreak spreading to edges and stop simply because of the unnatural map boundaries)"""
    seed_property = 0  # default
    seed_animal = 0

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


def initialise_infection_vaccination(
    properties, n, xrange, yrange, init_vax_probability, time=0
):
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

    return properties, seed_property, cumulative_infection_proportions


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
    test_sensitivity=0.9,
    movement_standstill=False,  # should only trigger after a notification occurs
    movement_restrictions=False,
    movement_restriction_radius_km=None,
    movement_restriction_convex=None,
    ring_vaccination=False,
    ring_vaccination_radius_km=None,
    ring_vaccination_convex=None,
    ring_culling=False,
    ring_culling_radius_km=None,
    ring_culling_convex=None,
    ring_testing=False,
    ring_testing_radius_km=None,
    ring_testing_convex=None,
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
    total_culled_animals = 0
    time = 0

    controlzone = {}  # dictionary, of different types control zones, if necessary

    report = ""
    movement_records = []
    contact_tracing_reports = ""
    testing_reports = ""
    combined_narrative = ""

    # limits for the figures
    xlims = [round(xrange[0], 2) - 0.005, round(xrange[1], 2) + 0.005]
    ylims = [round(yrange[0], 1) - 0.05, round(yrange[1], 1) + 0.05]

    properties, seed_property, cumulative_infection_proportions = (
        initialise_infection_vaccination(
            properties, n, xrange, yrange, init_vax_probability
        )
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

    # spread begins here:

    FOI = list(np.zeros(n))
    # plt.figure()
    # start time loop
    infected_sum = 1  # so the while loop begins
    properties_to_contact_trace = []
    traced_contacts = []
    while time < stop_time:  # infected_sum > 0 and
        time += 1

        properties_to_contact_trace_tomorrow = (
            []
        )  # properties collected today, to be traced tomorrow

        # calculate FOI for each property

        for i, premise in enumerate(properties):
            if not premise.culled_status:
                FOI[i] = SEIR.calculate_force_of_infection(
                    properties, i, vax_modifier, r_wind, beta_wind, beta_animal
                )

        # Do something about the contact tracing reported yesterday
        # TODO 1. plot out a "network" of the contact traced properties
        # 2. Conduct testing of traced properties
        # TODO 3. Apply movement standstill to traced properties
        if traced_contacts != []:
            testing_report, positive_indices = management.testing(
                properties, traced_contacts, time, test_sensitivity
            )
            testing_reports += testing_report
            combined_narrative += testing_report
            # for any positive indices (properties found), we will need to enact "reporting" procedures
            # given that I mostly copied this from the code below, this suggests that it could be encapsulated better...
            for index in positive_indices:
                premise = properties[index]
                premise_report, culled_animals = premise.reporting(
                    0, 0, time=time, force_report=True
                )
                total_culled_animals += culled_animals
                premise_report = "REPORTED AFTER POSTIVE TEST: " + premise_report
                report += premise_report
                combined_narrative += premise_report
                if premise.reported_status == True:  # well, this should be true...
                    properties_to_contact_trace_tomorrow.append(index)

        traced_contacts = []  # reset this
        contacts_for_plotting = {}  # from property, to properties

        # conduct contact tracing of properties that reported yesterday

        for property_index in properties_to_contact_trace:
            contact_tracing_report, traced_property_indices = (
                management.contact_tracing(
                    properties, property_index, movement_records, time
                )
            )
            contact_tracing_reports += contact_tracing_report
            combined_narrative += contact_tracing_report
            traced_contacts.extend(traced_property_indices)
            contacts_for_plotting[property_index] = traced_property_indices

        source_indices = []
        for i, premise in enumerate(properties):
            if premise.reported_status == True:
                source_indices.append(i)

        # implement ring culling
        if ring_culling:
            if source_indices != []:
                controlzone_ring_culling = management.define_control_zone_polygons(
                    properties,
                    source_indices,
                    ring_culling_radius_km,
                    convex=ring_culling_convex,
                )

                controlzone["ring culling"] = controlzone_ring_culling

                for premise in properties:
                    if not premise.culled_status and premise.polygon.intersects(
                        controlzone_ring_culling
                    ):
                        premise_report, culled_animals = premise.cull_without_reporting(
                            time
                        )
                        total_culled_animals += culled_animals
                        report += premise_report
                        combined_narrative += premise_report

        # implementing ring vaccination
        if ring_vaccination:
            if source_indices != []:
                controlzone_ring_vaccination = management.define_control_zone_polygons(
                    properties,
                    source_indices,
                    ring_vaccination_radius_km,
                    convex=ring_vaccination_convex,
                )

                controlzone["ring vaccination"] = controlzone_ring_vaccination

                for premise in properties:
                    if not premise.culled_status and premise.polygon.intersects(
                        controlzone_ring_vaccination
                    ):
                        premise.vaccinate(time)

        # implementing ring testing
        if ring_testing:
            if source_indices != []:
                controlzone_ring_testing = management.define_control_zone_polygons(
                    properties,
                    source_indices,
                    ring_testing_radius_km,
                    convex=ring_testing_convex,
                )

                controlzone["ring testing"] = controlzone_ring_testing

                properties_to_test = []
                for i, premise in enumerate(properties):
                    if not premise.culled_status and premise.polygon.intersects(
                        controlzone_ring_testing
                    ):
                        properties_to_test.append(i)

                testing_report, positive_indices = management.testing(
                    properties, properties_to_test, time, test_sensitivity
                )

                testing_reports += testing_report
                combined_narrative += testing_report

                # for any positive indices (properties found), we will need to enact "reporting" procedures
                # given that I mostly copied this from the code above, this suggests that it could be encapsulated better...
                for index in positive_indices:
                    premise = properties[index]
                    premise_report, culled_animals = premise.reporting(
                        0, 0, time=time, force_report=True
                    )
                    total_culled_animals += culled_animals
                    premise_report = "REPORTED AFTER POSTIVE TEST: " + premise_report
                    report += premise_report
                    combined_narrative += premise_report
                    if premise.reported_status == True:  # well, this should be true...
                        properties_to_contact_trace_tomorrow.append(index)

        # vaccinate properties around culled (reported) properties
        for premise in properties:
            if not premise.culled_status and not premise.infection_status:
                premise.vaccination(
                    prob_vaccinate, properties, time, culled_neighbours_only=True
                )

        # check if any properties now want to report
        for i, premise in enumerate(properties):
            if not premise.culled_status:
                premise_report, culled_animals = premise.reporting(
                    clinical_reporting_threshold, prob_report, time
                )
                total_culled_animals += culled_animals
                report += premise_report
                combined_narrative += premise_report
                if premise.reported_status == True:
                    properties_to_contact_trace_tomorrow.append(i)

        #
        properties_to_contact_trace = list(set(properties_to_contact_trace_tomorrow))

        # run infection model for each property
        for i, premise in enumerate(properties):
            premise.infection_model(
                latent_period, infectious_period, preclinical_period, FOI[i], time
            )

        # calculate movement restriction zones before animal movement
        # TODO: can implement some kind of policy_start variable
        controlzone_movement_restrictions = None
        if movement_standstill:
            source_indices = []
            for i, premise in enumerate(properties):
                if premise.reported_status == True:
                    source_indices.append(i)

            if source_indices != []:
                map_polygon = {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [xlims[0], ylims[0]],
                            [xlims[1], ylims[0]],
                            [xlims[1], ylims[1]],
                            [xlims[0], ylims[1]],
                            [xlims[0], ylims[0]],
                        ]
                    ],
                }
                controlzone_movement_restrictions = (
                    spatial_setup.convert_dict_poly_to_Polygon(map_polygon)
                )
                controlzone["movement restrictions"] = controlzone_movement_restrictions

        elif movement_restrictions:
            source_indices = []
            for i, premise in enumerate(properties):
                if premise.reported_status == True:
                    source_indices.append(i)

            if source_indices != []:
                controlzone_movement_restrictions = (
                    management.define_control_zone_polygons(
                        properties,
                        source_indices,
                        movement_restriction_radius_km,
                        convex=movement_restriction_convex,
                    )
                )
                controlzone["movement restrictions"] = controlzone_movement_restrictions

        # movement of animals
        movement_record = animal_movement.animal_movement(
            properties,
            n=n,
            movement_frequency=movement_frequency,
            movement_probability=movement_probability,
            movement_prop_animals=movement_prop_animals,
            day=time,
            controlzone=controlzone_movement_restrictions,
        )
        if movement_record != []:
            movement_records.extend(movement_record)

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
                contacts_for_plotting={},  # TODO in the real situation, these should be the actual movements, or something
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
                contacts_for_plotting=contacts_for_plotting,
            )
            # should also save contacts_for_plotting
            output.save_data(
                properties, property_coordinates, time, controlzone, folder_path
            )

        combined_narrative += "\n"

    if plotting:
        output.make_video(folder_path, "map_underlying")
        output.make_video(folder_path, "map_apparent")

    # statistics from end of simulation
    for premise in properties:
        if premise.culled_status:
            total_culled += 1
        if premise.vaccination_status:
            total_vaccinated += 1

    # should add in a total culled animals
    combined_narrative += f"\n==============\nTotal culled properties: {total_culled}; total vaccinated properties: {total_vaccinated}; total culled animals: {total_culled_animals}"

    # print output: all
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
    file = os.path.join(folder_path, f"fake_data_underlying_{unique_output}.csv")
    with open(file, "w", newline="") as f:

        # create the csv writer
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

        for premise in properties:
            row = premise.return_output_row()
            writer.writerow(row)

    # print output: known
    file = os.path.join(folder_path, f"fake_data_apparent_{unique_output}.csv")
    with open(file, "w", newline="") as f:

        # create the csv writer
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

        for premise in properties:
            row = premise.return_known_output_row()
            writer.writerow(row)

    # output "reports" report
    with open(os.path.join(folder_path, "report.txt"), "w") as file:
        file.write(report)

    # output contact tracing reports
    with open(os.path.join(folder_path, "report_contact_tracing.txt"), "w") as file:
        file.write(contact_tracing_reports)

    # output testing reports
    with open(os.path.join(folder_path, "report_testing.txt"), "w") as file:
        file.write(testing_reports)

    # output the inter-twined narrative (of known occurences)
    with open(os.path.join(folder_path, "report_combined_narrative.txt"), "w") as file:
        file.write(combined_narrative)

    # write movement records

    header = [
        "time",
        "moving from index",
        "moving to index",
        "report",
    ]
    file = os.path.join(folder_path, f"movement_records.csv")
    with open(file, "w", newline="") as f:

        # create the csv writer
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

        for row in movement_records:
            writer.writerow(row)

    return total_culled, total_vaccinated, properties
