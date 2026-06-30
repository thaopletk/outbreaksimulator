import os
import csv
import pandas as pd
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.premises as premises
import simulator.output as output
import simulator.fixed_spatial_setup as fixed_spatial_setup
import numpy as np
import random
from FMD_modelling.class_definitions import Animal
import betapert

movement_record_header = [
    "day",
    "date",
    "from",
    "to",
    "entity",
    "quantity",
    "facility_type_1",
    "facility_type_2",
    "truck_id",
    "report",
    "from_herd_id",
    "to_herd_id",
]


def create_movement_records_df():

    return pd.DataFrame(columns=movement_record_header)


def little_date_converter(input_date_string):
    """converts dd/mm/yyyy date into yyyy-mm-dd"""

    if input_date_string == "NA":
        return "NA"
    day_string, month_string, year_string = input_date_string.split("/")
    new_date = f"{year_string}-{month_string}-{day_string}"
    return new_date


def save_approx_known_data(properties, folder_path, unique_output="", output_suffix=""):
    """Outputs a csv with the approximately known data on properties and premises

    Returns
    -------
    list

    """

    header = [
        "herd_id",
        "farm_id",
        "sim_id",
        "case_id",
        "status",
        "ip",
        "clinical_date",
        "self_report_date",
        "confirmation_date",  # aka notification date
        "removal_date",
        "recovery_date",
        "vacc_date",
        "LGA",
        "xcoord",
        "ycoord",
        "area",
        "enterprise",
        "animal_type",
        "total_animals",
        "data_source",
        "last_surveillance_date",
        "animals_clinical",
        "last_PCR_date",
        "PCR_result",
        "last_cull_date",
        "culled_animals",
        "last_conducted_contact_tracing",
        "vaccinated_animals",
        "case_created_date",
        "disposal_date",
        "decontamination_date",
    ]

    data_rows_for_Biosecurity_Commons = []

    if output_suffix == "":
        file = os.path.join(folder_path, f"approx_known_data_{unique_output}.csv")
    else:
        file = os.path.join(folder_path, f"approx_known_data{output_suffix}.csv")
    with open(file, "w", newline="") as f:

        # create the csv writer
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

        for facility in properties:

            if "herd_id" in facility.FMD_extra_info:
                herd_id = facility.FMD_extra_info["herd_id"]
            else:
                herd_id = "NA"

            if "farm_id" in facility.FMD_extra_info:
                farm_id = facility.FMD_extra_info["farm_id"]
            else:
                farm_id = "NA"

            try:
                self_report_date = facility.custom_info["self_report_date"]
            except:
                self_report_date = "NA"

            try:
                infection_data_known = facility.custom_info["infection_data_known"]
            except:
                infection_data_known = False

            try:
                last_surveillance_date = facility.custom_info["last_surveillance_date"]
            except:
                last_surveillance_date = "NA"

            try:
                animals_clinical = facility.custom_info["animals_clinical"]
            except:
                animals_clinical = "NA"

            try:
                last_PCR_date = facility.custom_info["last_PCR_date"]
            except:
                last_PCR_date = "NA"

            try:
                PCR_result = facility.custom_info["PCR_result"]
            except:
                PCR_result = "NA"

            try:
                last_cull_date = facility.custom_info["last_cull_date"]
            except:
                last_cull_date = "NA"

            try:
                culled_animals = facility.custom_info["culled_animals"]
            except:
                culled_animals = "NA"

            try:
                last_conducted_contact_tracing_date = facility.custom_info["last_conducted_contact_tracing"]
            except:
                last_conducted_contact_tracing_date = "NA"

            if "vaccinated_animals" in facility.custom_info:
                vaccinated_animals = facility.custom_info["vaccinated_animals"]
            else:
                vaccinated_animals = "NA"

            try:
                case_created_date = facility.case_created_date
            except:
                case_created_date = "NA"

            if facility.data_source != "":  # if something is actually known!
                row = [
                    herd_id,
                    farm_id,
                    facility.id,  # facility.sim_id, sim_id is too complicated ya...
                    facility.case_id,
                    facility.status,
                    facility.ip,
                    facility.clinical_date if infection_data_known else "NA",
                    self_report_date,
                    facility.notification_date,
                    facility.removal_date,
                    facility.recovery_date if infection_data_known else "NA",
                    facility.vacc_date,
                    facility.region,
                    facility.coordinates[0],
                    facility.coordinates[1],
                    facility.area,
                    facility.type,
                    facility.animal_type,
                    facility.get_num_animals(),
                    facility.data_source,
                    last_surveillance_date,
                    animals_clinical,
                    last_PCR_date,
                    PCR_result,
                    last_cull_date,
                    culled_animals,
                    last_conducted_contact_tracing_date,
                    vaccinated_animals,
                    case_created_date,
                    facility.disposal_date,
                    facility.decontamination_date,
                ]

                writer.writerow(row)

                if facility.status == "NA":
                    BC_status = "NIL"
                elif facility.status == "RP":
                    BC_status = "IP"
                else:
                    BC_status = facility.status

                row = [
                    facility.id,
                    BC_status,
                    little_date_converter(facility.clinical_date) if infection_data_known else "NA",
                    little_date_converter(facility.notification_date),
                    little_date_converter(facility.removal_date),
                    little_date_converter(facility.recovery_date) if infection_data_known else "NA",
                    facility.coordinates[0],
                    facility.coordinates[1],
                ]

                data_rows_for_Biosecurity_Commons.append(row)

    BC_header = [
        "id",
        "status",
        "clinical_date",
        "notification_date",
        "removal_date",
        "recovery_date",
        "lon",
        "lat",
    ]

    if output_suffix == "":
        file = os.path.join(folder_path, f"approx_known_data_{unique_output}_Biosecurity_Commons.csv")
    else:
        file = os.path.join(folder_path, f"approx_known_data{output_suffix}_Biosecurity_Commons.csv")
    with open(file, "w", newline="") as f:
        # create the csv writer
        writer = csv.writer(f)

        # write the header
        writer.writerow(BC_header)
        for row in data_rows_for_Biosecurity_Commons:
            writer.writerow(row)


def seed_FMD_infection(
    seed_herd_id,
    properties,
    int_time=0,
    xlims=[],
    ylims=[],
    folder_path="",
    unique_output="",
    latent_period=7,
    disease_parameters=None,
    ABC_mode=False,
):
    """Seeds an infection at a property within the bounds specified"""
    seed_property = 0  # default

    for i, property in enumerate(properties):
        if "herd_id" in property.FMD_extra_info:
            if seed_herd_id == property.FMD_extra_info["herd_id"]:
                seed_property = i
                break

    # seed this property
    p = properties[seed_property]
    num_infected = 4  # min(10, p.animals[p.animal_type]["n"])
    p.init_animals(None)

    # TODO technically, to encapsulate this better, there should a function that allows you to infect a specific animal(s), and that will then update infection_status, prop_infections, cumulative_infections, and exposure_date, and anything else that may need to be updated
    p.infection_status = 1
    # if latent_period != None:
    #     p.exposure_date = premises.convert_time_to_date(int_time - latent_period)
    # else:  # the version with multiple animals
    #     latent_period = disease_parameters[p.animal_type]["latent_period"]
    #     p.exposure_date = premises.convert_time_to_date(int_time - latent_period)

    p.exposure_date = premises.convert_time_to_date(int_time)

    for seed_animal in range(num_infected):
        p.animals[p.animal_type]["objs"][seed_animal].infection_status = "exposed"
        p.animals[p.animal_type]["objs"][seed_animal].clinical_status = "pre-clinical"
        # p.animals[p.animal_type]["objs"][seed_animal].check_transition(disease_parameters[p.animal_type])
        # p.animals[p.animal_type]["objs"][seed_animal].update_clock()

        # p.animals[p.animal_type]["objs"][seed_animal].infection_status = "infectious"
        # p.animals[p.animal_type]["objs"][seed_animal].infection_clock = latent_period
        # p.animals[p.animal_type]["objs"][seed_animal].clinical_clock = latent_period

    # p.prop_infectious = num_infected / p.get_num_animals()
    p.cumulative_infections = num_infected
    p.cumulative_infections_by_animal_type[p.animal_type] = num_infected

    if ABC_mode == False:
        output.plot_map(
            properties,
            int_time,
            xlims=xlims,
            ylims=ylims,
            folder_path=folder_path,
            real_situation=True,
            controlzone=None,
            infectionpoly=None,
            contacts_for_plotting={},  # contacts_for_plotting,  # hiding the contacts for plotting, to make things look clearer,,,, TODO in the real situation, these should be the actual movements, or something
        )

        fixed_spatial_setup.save_FMD_property_csv(properties, int_time, folder_path, unique_output)

    return properties, seed_property


def construct_trucks(properties):
    # set up trucks (e.g. 10) at each processing facility, saleyard, export facility and maybe at large premises with a lot of animals
    trucks_list = []
    truck_id = 0
    for premise_index, facility in enumerate(properties):
        if facility.type in [
            "beef extensive",
            "beef intensive",
            "mixed beef",
            "mixed sheep",
            "pigs small",
            "pigs large",
            "sheep",
            "smallholder",
            "feedlot",
        ]:
            cargo = 0
            contamination_level = 0
            home_location = premise_index
            if facility.animal_type == "cattle":
                cargo_limit = 30
            elif facility.animal_type == "pigs":
                cargo_limit = 60
            elif facility.animal_type == "sheep":
                cargo_limit = 90
            else:
                raise ValueError(f"unexpected animal type for facility/ truck, {facility.animal_type}")

            num_trucks = 0
            if facility.get_num_animals() > 100:  # a bigger property
                num_trucks = max(1, int(np.ceil(facility.get_num_animals() / 100)))
            for _ in range(num_trucks):
                trucks_list.append([truck_id, home_location, facility.animal_type, cargo_limit, cargo, contamination_level, False])
                truck_id += 1

        elif facility.type == "milk_processing":
            cargo = 0
            contamination_level = 0
            home_location = premise_index
            properties_serviced = [premise_index]
            cargo_limit = 40000
            for _ in range(10):
                trucks_list.append([truck_id, home_location, "milk", cargo_limit, cargo, contamination_level, False])
                truck_id += 1
        elif facility.type == "dairy":
            num_trucks = 0
            # 20 litres of milk per day
            if facility.get_num_animals() * 20 > 15000:  # a bigger property
                num_trucks = max(1, int(np.ceil(facility.get_num_animals() * 20 / 15000)))
                cargo = 0
                contamination_level = 0
                home_location = premise_index
                properties_serviced = [premise_index]
                cargo_limit = 15000

                for _ in range(num_trucks):
                    trucks_list.append([truck_id, home_location, "milk", cargo_limit, cargo, contamination_level, False])
                    truck_id += 1

        elif facility.type in ["abattoir", "saleyard", "export_facility"]:
            cargo = 0
            contamination_level = 0
            home_location = premise_index
            properties_serviced = [premise_index]
            if "cattle" in facility.animal_type:
                cargo_limit = 30
                trucks_list.append([truck_id, home_location, "cattle", cargo_limit, cargo, contamination_level, False])
                truck_id += 1

            if "pigs" in facility.animal_type:
                cargo_limit = 60
                trucks_list.append([truck_id, home_location, "pigs", cargo_limit, cargo, contamination_level, False])
                truck_id += 1

            if "sheep" in facility.animal_type:
                cargo_limit = 90
                trucks_list.append([truck_id, home_location, "sheep", cargo_limit, cargo, contamination_level, False])
                truck_id += 1

    # NOTE: assuming for now that trucks automatically return to their "home" at the end of the day.
    trucks_df = pd.DataFrame(trucks_list, columns=["truck_id", "home_property", "cargo_type", "cargo_cap", "cargo", "contamination", "busy"])

    return trucks_df


def in_zones(facility_polygon, controlzone, reduced_movement_zone):
    in_control_zone = False
    if controlzone != None and facility_polygon.intersects(controlzone):
        in_control_zone = True
        # TODO: if True, use this to raise movement permit request

    in_reduced_movement_zone = False
    if reduced_movement_zone != None and facility_polygon.intersects(reduced_movement_zone):
        in_reduced_movement_zone = True

    return in_control_zone, in_reduced_movement_zone


def find_targets(properties, properties_to_move_to, controlzone, movement_reduction_factor, all_movement_reduction_factor, reduced_movement_zone):
    targets_unrestricted_zones = []
    targets_in_control_zones = []
    for property_index in properties_to_move_to:
        target_facility = properties[property_index]
        if target_facility == "IP" or target_facility == "RP":
            continue  # skip it

        if controlzone != None and target_facility.polygon.intersects(controlzone):
            if random.uniform(0, 1) < movement_reduction_factor * all_movement_reduction_factor:
                # ILLEGAL MOVEMENT, aka with some probability, there will be movement without movement requests!
                targets_unrestricted_zones.append(property_index)
            else:
                targets_in_control_zones.append(property_index)
        else:
            if reduced_movement_zone != None and target_facility.polygon.intersects(reduced_movement_zone):
                if random.uniform(0, 1) < all_movement_reduction_factor:  # illegal or reduced movement
                    targets_unrestricted_zones.append(property_index)
                else:
                    targets_in_control_zones.append(property_index)
            else:
                targets_unrestricted_zones.append(property_index)
    return targets_unrestricted_zones, targets_in_control_zones


def pick_single_movement_target(
    facility,
    targets_unrestricted_zones,
    targets_in_control_zones,
    in_control_zone,
    movement_reduction_factor,
    in_reduced_movement_zone,
    item_to_transport,
):
    movement_possible = False
    number_of_movement_requests = 0
    target_property_index = 0
    if targets_unrestricted_zones == [] and targets_in_control_zones == []:
        pass
    else:
        if in_control_zone and (random.uniform(0, 1) > movement_reduction_factor):
            # note permit request:  facility id[], type [], status [], requests to move [X animals] to [target facility]
            if targets_unrestricted_zones != [] or targets_in_control_zones != []:  # i.e., there is a place it could have moved stuff
                print(f"{facility.type} (sim_id {facility.id}) would like to transport {item_to_transport} but is inside restricted zone")
                number_of_movement_requests = 1
        elif in_reduced_movement_zone and (random.uniform(0, 1) > movement_reduction_factor):
            if targets_unrestricted_zones != [] or targets_in_control_zones != []:  # i.e., there is a place it could have moved stuff
                print(f"{facility.type} (sim_id {facility.id}) would like to transport {item_to_transport} but is inside control zone")
                number_of_movement_requests = 1
        else:
            movement_possible = True
            if targets_unrestricted_zones != []:
                random.shuffle(targets_unrestricted_zones)
                target_property_index = targets_unrestricted_zones[0]
            elif targets_in_control_zones != []:
                random.shuffle(targets_in_control_zones)
                target_property_index = targets_in_control_zones[0]

    return movement_possible, number_of_movement_requests, target_property_index


def get_available_trucks(trucks_df, premise_index, target_index, item_to_move, must_return_truck=False):
    # item to move can be an animal or milk

    trucks_sub_df = trucks_df[
        (trucks_df["busy"] == False) & (trucks_df["cargo_type"] == item_to_move) & (trucks_df["home_property"] == premise_index)
    ]
    trucks_sub = list(trucks_sub_df.truck_id)
    local_trucks = True
    if len(trucks_sub) == 0:
        # try the target index instead
        trucks_sub_df = trucks_df[
            (trucks_df["busy"] == False) & (trucks_df["cargo_type"] == item_to_move) & (trucks_df["home_property"] == target_index)
        ]
        trucks_sub = list(trucks_sub_df.truck_id)
        local_trucks = False

        if len(trucks_sub) == 0 and must_return_truck:
            truck_found = False
            # find nearby trucks nearby instead
            i = 0
            while truck_found == False:
                i += 1
                trucks_sub_df = trucks_df[
                    (trucks_df["busy"] == False) & (trucks_df["cargo_type"] == item_to_move) & (trucks_df["home_property"] == premise_index - i)
                ]
                trucks_sub = list(trucks_sub_df.truck_id)
                if len(trucks_sub) > 0:
                    truck_found = True

    truck_capacities = list(trucks_sub_df.cargo_cap)
    total_capacity = sum(truck_capacities)

    available_trucks = trucks_sub  # truck ids

    return available_trucks, total_capacity, local_trucks, truck_capacities


def animal_movement(
    properties,
    day,
    controlzone,
    reduced_movement_zone=None,
    movement_reduction_factor=0.2,
    all_movement_reduction_factor=1.0,
    trucks_df=None,
    disease_parameters={},
    truck_contanmination_infection_factor=0.5,
    truck_cleaning=0.2,
):

    date = premises.convert_time_to_date(day)

    movement_record = []
    number_of_movement_requests = 0

    # superseded by property_i.movement_probability
    # # this is the probability of movement every x days
    # x = 5
    # probability_of_movement = {
    #     "beef extensive": x / 365,  # one year movement
    #     "beef intensive": x / (7 * 30.5),  # movements every 7 months
    #     "feedlot": x / 100,  # animals stay from 50 days minimum to 400 days; so proability as expected for 100 days
    #     "mixed beef": x / (7 * 30.5),
    #     "mixed sheep": x / 365,
    #     "pigs small": x / (5 * 30),
    #     "pigs large": x / (5 * 30),
    #     "sheep": x / 365,
    #     "smallholder": x / (6 * 30),
    #     "saleyard": 1,  # daily movement allowed
    # }

    in_transit = {}  # needs to contain info about target facility, animal type, and animals (number, objs if relevant)

    # start the movement
    for premise_index, facility in enumerate(properties):
        if facility.culled_status or facility.status == "IP" or facility.status == "RP":
            continue

        # if facility.type not in ["dairy", "abattoir", "saleyard", "export_facility", "milk_processing"] and facility.id % x != day % x:
        #     continue  # check non-dairy properties every ten days

        in_control_zone, in_reduced_movement_zone = in_zones(facility.polygon, controlzone, reduced_movement_zone)

        if facility.type in [
            "beef extensive",
            "beef intensive",
            "feedlot",
            "mixed beef",
            "mixed sheep",
            "pigs small",
            "pigs large",
            "sheep",
            "smallholder",
            "saleyard",
        ]:
            # some forced movements
            forced = False

            if "herd_id" in facility.FMD_extra_info and facility.FMD_extra_info["herd_id"] == 125520:
                if day == 1:
                    print("herd id == 125520 and day == 1")
                    forced = True
                elif day == 2:
                    print("herd id == 125520 and day == 2")
                    forced = True
                else:
                    continue  # no movement on other days
            elif "herd_id" in facility.FMD_extra_info and facility.FMD_extra_info["herd_id"] == 114447:
                if day == 21:
                    print("herd id == 114447 and day == 21")  # this works
                    forced = True
                else:
                    continue  # no movements on other days
            elif "herd_id" in facility.FMD_extra_info and facility.FMD_extra_info["herd_id"] == 25435:
                continue  # no movements off the target property
            else:
                if np.random.rand() > facility.movement_probability:
                    continue  # no movement

            # else: lets move!
            for animal_avail in facility.animals:
                if facility.animals[animal_avail]["n"] == 0:
                    continue
                try:
                    properties_to_move_to = facility.allowed_movement_details[animal_avail]["properties"]
                except Exception as e:
                    print(e)
                    print(facility.animals)
                    print(facility.id)
                    print(facility.allowed_movement_details)
                    exit(1)

                target_index = None
                if "herd_id" in facility.FMD_extra_info and facility.FMD_extra_info["herd_id"] == 125520 and day == 1:
                    # source - sim id is 38769
                    movement_possible = True
                    # target herd id = 124711
                    for i, property in enumerate(properties):
                        if "herd_id" in property.FMD_extra_info:
                            if property.FMD_extra_info["herd_id"] == 124711:
                                target_index = i
                                print("forced target index found")
                elif "herd_id" in facility.FMD_extra_info and facility.FMD_extra_info["herd_id"] == 125520 and day == 2:
                    movement_possible = True
                    # target herd id = 114447 now
                    for i, property in enumerate(properties):
                        if "herd_id" in property.FMD_extra_info:
                            if property.FMD_extra_info["herd_id"] == 114447:
                                target_index = i
                                print("forced target index found")

                elif "herd_id" in facility.FMD_extra_info and facility.FMD_extra_info["herd_id"] == 114447 and day == 21:
                    movement_possible = True
                    # target herd id = 111575 now
                    for i, property in enumerate(properties):
                        if "herd_id" in property.FMD_extra_info:
                            if property.FMD_extra_info["herd_id"] == 111575:
                                target_index = i
                                print("forced target index found")
                                # sim id 24824, pig - not found for some reason?
                else:

                    targets_unrestricted_zones, targets_in_control_zones = find_targets(
                        properties,
                        properties_to_move_to,
                        controlzone,
                        movement_reduction_factor,
                        all_movement_reduction_factor,
                        reduced_movement_zone,
                    )

                    movement_possible, n_movement_request, target_index = pick_single_movement_target(
                        facility,
                        targets_unrestricted_zones,
                        targets_in_control_zones,
                        in_control_zone,
                        movement_reduction_factor,
                        in_reduced_movement_zone,
                        animal_avail,
                    )
                    number_of_movement_requests += n_movement_request
                if movement_possible and target_index == None:
                    print("unable to find specific target index")
                    targets_unrestricted_zones, targets_in_control_zones = find_targets(
                        properties,
                        properties_to_move_to,
                        controlzone,
                        movement_reduction_factor,
                        all_movement_reduction_factor,
                        reduced_movement_zone,
                    )

                    movement_possible, n_movement_request, target_index = pick_single_movement_target(
                        facility,
                        targets_unrestricted_zones,
                        targets_in_control_zones,
                        in_control_zone,
                        movement_reduction_factor,
                        in_reduced_movement_zone,
                        animal_avail,
                    )
                    number_of_movement_requests += n_movement_request

                if movement_possible:
                    # go through truck dataframe
                    # find trucks that aren't busy
                    # first try to find a truck at the facility
                    # and if not possible, find a truck at the target facility
                    available_trucks, total_capacity, local_trucks, truck_capacities = get_available_trucks(
                        trucks_df, premise_index, target_index, animal_avail, must_return_truck=forced
                    )

                    if len(available_trucks) == 0:
                        continue

                    # facility.movement_prop_animals = [1,5,20] beta PERT distribution
                    num_animals_to_move_ideally = betapert.pert.rvs(
                        mini=facility.movement_prop_animals[0], mode=facility.movement_prop_animals[1], maxi=facility.movement_prop_animals[2]
                    )
                    if facility.type == "saleyard":
                        num_animals_to_move_ideally = int(num_animals_to_move_ideally)  # this isn't a proportion
                    else:
                        num_animals_to_move_ideally = int(num_animals_to_move_ideally * facility.animals[animal_avail]["n"])  # and this is

                    if forced:
                        num_animals_to_move_ideally = 2  # moving fewer...

                    # print(num_animals_to_move_ideally)

                    if local_trucks:
                        # if local trucks on the property, just use all of them
                        num_animals_to_move = min(total_capacity, facility.animals[animal_avail]["n"], num_animals_to_move_ideally)
                    else:
                        max_trucks_to_use = int(np.random.randint(1, len(available_trucks) + 1))
                        sub_capacity = sum(truck_capacities[:max_trucks_to_use])
                        num_animals_to_move = min(sub_capacity, facility.animals[animal_avail]["n"], num_animals_to_move_ideally)

                    # based on the number of animals to move, calculate which trucks are actually used and stop when that amount is reached

                    trucks_used = []
                    for i in range(len(available_trucks)):
                        truck_id = available_trucks[i]
                        trucks_used.append(truck_id)
                        cap = truck_capacities[i]

                        # move the number of animals that is bounded by the truck capacity
                        if cap < num_animals_to_move:
                            to_move = cap
                        else:
                            to_move = num_animals_to_move

                        # move the animals into a temporary dictionary probably, rather than the dataframe
                        in_transit[truck_id] = {"cargo": animal_avail, "n": to_move, "target": target_index}
                        facility.animals[animal_avail]["n"] = facility.animals[animal_avail]["n"] - to_move
                        num_animals_to_move = num_animals_to_move - to_move

                        if forced:
                            if "objs" not in facility.animals[animal_avail]:
                                print("need a sick animal to move but there are no sick animals here!")
                            else:
                                sick_animal_moved_successfully = False
                                # todo : make sure that you move at least one infected animal
                                for i in range(len(facility.animals[animal_avail]["objs"])):
                                    animal_temp = facility.animals[animal_avail]["objs"][i]
                                    if animal_temp.infection_status in ["exposed", "infectious"]:  # move this animal, break and remove it
                                        sick_animal_moved_successfully = True
                                        in_transit[truck_id]["objs"] = [animal_temp]
                                        del facility.animals[animal_avail]["objs"][i]
                                        break
                                if sick_animal_moved_successfully:
                                    # only need to move N-1
                                    print("Moved sick animal")
                                    in_transit[truck_id]["objs"].extend(facility.animals[animal_avail]["objs"][: to_move - 1])
                                    facility.animals[animal_avail]["objs"] = facility.animals[animal_avail]["objs"][to_move - 1 :]
                                else:
                                    print("Unable to find sick animal to move")
                                    in_transit[truck_id]["objs"] = facility.animals[animal_avail]["objs"][:to_move]
                                    facility.animals[animal_avail]["objs"] = facility.animals[animal_avail]["objs"][to_move:]
                        else:
                            if "objs" in facility.animals[animal_avail]:
                                in_transit[truck_id]["objs"] = facility.animals[animal_avail]["objs"][:to_move]
                                facility.animals[animal_avail]["objs"] = facility.animals[animal_avail]["objs"][to_move:]
                                if len(facility.animals[animal_avail]["objs"]) == 0:
                                    del facility.animals[animal_avail]["objs"]

                        row = [
                            day,
                            f"{date}",
                            premise_index,
                            target_index,
                            animal_avail,
                            in_transit[truck_id]["n"],
                            facility.type,
                            properties[target_index].type,
                            truck_id,
                            f"DAY {date} - moved {in_transit[truck_id]['n']} {animal_avail} from {facility.type} (sim_id {facility.id}) ({facility.region}) to {properties[target_index].type} (sim_id {properties[target_index].id}) ( {properties[target_index].region})",
                            facility.FMD_extra_info["herd_id"] if "herd_id" in facility.FMD_extra_info else "NA",
                            properties[target_index].FMD_extra_info["herd_id"] if "herd_id" in properties[target_index].FMD_extra_info else "NA",
                        ]

                        movement_record.append(row)

                        if num_animals_to_move == 0:
                            break

                    # tag those trucks as "busy"=True
                    mask = trucks_df["truck_id"].isin(trucks_used)
                    trucks_df["busy"][mask] = True

        elif facility.type == "dairy":
            # moving milk every 24 or 48 hours. just go daily for now for simplicity
            # get places to move milk to; assume no movement of cattle for simplicity

            # do any forced movements first
            if facility.FMD_extra_info["herd_id"] == 57712 and day in [19, 25]:
                print("herd id == 57712 and day == 19 or 25")  # thtis doesn't work???
                # should be 12501... dairy

                if day == 25:
                    # target herd id = 24636 now
                    for i, property in enumerate(properties):
                        if "herd_id" in property.FMD_extra_info:
                            if property.FMD_extra_info["herd_id"] == 24636:
                                target_index = i
                                print("forced target index found")
                elif day == 19:
                    # target herd id = 217444 now
                    for i, property in enumerate(properties):
                        if "herd_id" in property.FMD_extra_info:
                            if property.FMD_extra_info["herd_id"] == 217444:
                                target_index = i
                                print("forced target index found")

                available_trucks, total_capacity, local_trucks, truck_capacities = get_available_trucks(
                    trucks_df, premise_index, target_index, "cattle", must_return_truck=True
                )

                animal_avail = "cattle"

                num_animals_to_move_ideally = betapert.pert.rvs(
                    mini=facility.movement_prop_animals[0], mode=facility.movement_prop_animals[1], maxi=facility.movement_prop_animals[2]
                )
                num_animals_to_move_ideally = int(num_animals_to_move_ideally * facility.animals[animal_avail]["n"])

                max_trucks_to_use = int(np.random.randint(1, len(available_trucks) + 1))
                sub_capacity = sum(truck_capacities[:max_trucks_to_use])
                num_animals_to_move = min(sub_capacity, facility.animals[animal_avail]["n"], num_animals_to_move_ideally)

                trucks_used = []
                for i in range(len(available_trucks)):
                    truck_id = available_trucks[i]
                    trucks_used.append(truck_id)
                    cap = truck_capacities[i]

                    # move the number of animals that is bounded by the truck capacity
                    if cap < num_animals_to_move:
                        to_move = cap
                    else:
                        to_move = num_animals_to_move

                    # move the animals into a temporary dictionary probably, rather than the dataframe
                    in_transit[truck_id] = {"cargo": animal_avail, "n": to_move, "target": target_index}
                    facility.animals[animal_avail]["n"] = facility.animals["cattle"]["n"] - to_move
                    num_animals_to_move = num_animals_to_move - to_move

                    if "objs" not in facility.animals[animal_avail]:
                        print("need a sick animal to move but there are no sick animals here!")
                    else:
                        sick_animal_moved_successfully = False
                        # todo : make sure that you move at least one infected animal
                        for i in range(len(facility.animals[animal_avail]["objs"])):
                            animal_temp = facility.animals[animal_avail]["objs"][i]
                            if animal_temp.infection_status != "susceptible":  # move this animal, break and remove it
                                sick_animal_moved_successfully = True
                                in_transit[truck_id]["objs"] = [animal_temp]
                                del facility.animals[animal_avail]["objs"][i]
                                break
                        if sick_animal_moved_successfully:
                            # only need to move N-1
                            print("Moved sick animal")
                            in_transit[truck_id]["objs"].extend(facility.animals[animal_avail]["objs"][: to_move - 1])
                            facility.animals[animal_avail]["objs"] = facility.animals[animal_avail]["objs"][to_move - 1 :]
                        else:
                            print("Unable to find sick animal to move")
                            in_transit[truck_id]["objs"] = facility.animals[animal_avail]["objs"][:to_move]
                            facility.animals[animal_avail]["objs"] = facility.animals[animal_avail]["objs"][to_move:]

                    row = [
                        day,
                        f"{date}",
                        premise_index,
                        target_index,
                        animal_avail,
                        in_transit[truck_id]["n"],
                        facility.type,
                        properties[target_index].type,
                        truck_id,
                        f"DAY {date} - moved {in_transit[truck_id]['n']} {animal_avail} from {facility.type} (sim_id {facility.id}) ({facility.region}) to {properties[target_index].type} (sim_id {properties[target_index].id}) ( {properties[target_index].region})",
                        facility.FMD_extra_info["herd_id"] if "herd_id" in facility.FMD_extra_info else "NA",
                        properties[target_index].FMD_extra_info["herd_id"] if "herd_id" in properties[target_index].FMD_extra_info else "NA",
                    ]

                    movement_record.append(row)

                    if num_animals_to_move == 0:
                        break
                # tag those trucks as "busy"=True
                mask = trucks_df["truck_id"].isin(trucks_used)
                trucks_df["busy"][mask] = True

            properties_to_move_to = facility.allowed_movement_details["milk"]["properties"]

            targets_unrestricted_zones, targets_in_control_zones = find_targets(
                properties, properties_to_move_to, controlzone, movement_reduction_factor, all_movement_reduction_factor, reduced_movement_zone
            )

            movement_possible, n_movement_request, target_index = pick_single_movement_target(
                facility,
                targets_unrestricted_zones,
                targets_in_control_zones,
                in_control_zone,
                movement_reduction_factor,
                in_reduced_movement_zone,
                facility.animal_type,
            )
            number_of_movement_requests += n_movement_request
            if movement_possible:

                # find a truck
                available_trucks, total_capacity, local_trucks, truck_capacities = get_available_trucks(
                    trucks_df, premise_index, target_index, "milk"
                )

                if len(available_trucks) == 0:
                    continue

                new_facility = properties[target_index]
                milk_litres = 20 * facility.get_num_animals()  # 20 L of milk per day

                if local_trucks:
                    # if local trucks on the property, just use all of them
                    milk_litres = min(total_capacity, milk_litres)
                else:
                    max_trucks_to_use = int(np.random.randint(1, len(available_trucks) + 1))
                    sub_capacity = sum(truck_capacities[:max_trucks_to_use])
                    milk_litres = min(sub_capacity, milk_litres)

                trucks_used = []
                for i in range(len(available_trucks)):
                    truck_id = available_trucks[i]
                    trucks_used.append(truck_id)
                    cap = truck_capacities[i]

                    in_transit[truck_id] = {"cargo": "milk", "n": cap, "target": target_index}
                    milk_litres = milk_litres - cap

                    # TODO could add in milk infection here somehow
                    row = [
                        day,
                        f"{date}",
                        premise_index,
                        target_index,
                        "milk",
                        cap,  # 20 L of milk per day
                        facility.type,
                        new_facility.type,
                        truck_id,
                        f"DAY {date} - moved {cap} L milk from {facility.type} (sim_id {facility.id}) ({facility.region}) to {new_facility.type} (sim_id {new_facility.id}) ( {new_facility.region})",
                        facility.FMD_extra_info["herd_id"] if "herd_id" in facility.FMD_extra_info else "NA",
                        properties[target_index].FMD_extra_info["herd_id"] if "herd_id" in properties[target_index].FMD_extra_info else "NA",
                    ]

                    movement_record.append(row)

                    if milk_litres <= 0:
                        break

                # tag those trucks as "busy"=True
                mask = trucks_df["truck_id"].isin(trucks_used)
                trucks_df["busy"][mask] = True

        elif facility.type == "abattoir":
            # TODO: could have separate trucks here and infection in the meat

            if facility.FMD_extra_info["export"] == 1:
                # this would be meat export rather than live export
                for ani_type in facility.animals:
                    if "n" in facility.animals[ani_type] and facility.animals[ani_type]["n"] > 0:
                        properties_to_move_to = facility.allowed_movement_details[ani_type]["properties"]
                        targets_unrestricted_zones, targets_in_control_zones = find_targets(
                            properties,
                            properties_to_move_to,
                            controlzone,
                            movement_reduction_factor,
                            all_movement_reduction_factor,
                            reduced_movement_zone,
                        )

                        movement_possible, n_movement_request, target_index = pick_single_movement_target(
                            facility,
                            targets_unrestricted_zones,
                            targets_in_control_zones,
                            in_control_zone,
                            movement_reduction_factor,
                            in_reduced_movement_zone,
                            facility.animal_type,
                        )
                        number_of_movement_requests += n_movement_request

                        if movement_possible:
                            for_slaughter = facility.animals[ani_type]["n"]
                            # clear the abattoir
                            facility.animals[ani_type]["n"] = 0
                            if "objs" in facility.animals[ani_type]:
                                del facility.animals[ani_type]["objs"]

                            cargo = "meat-" + ani_type

                            row = [
                                day,
                                f"{date}",
                                premise_index,
                                target_index,
                                cargo,
                                for_slaughter,
                                facility.type,
                                properties[target_index].type,
                                -1,
                                f"DAY {date} - slaughtered and moved {for_slaughter} {ani_type} from {facility.type} (sim_id {facility.id}) ({facility.region}) {properties[target_index].type} (sim_id {properties[target_index].id}) ( {properties[target_index].region})",
                                facility.FMD_extra_info["herd_id"] if "herd_id" in facility.FMD_extra_info else "NA",
                                properties[target_index].FMD_extra_info["herd_id"] if "herd_id" in properties[target_index].FMD_extra_info else "NA",
                            ]

                            if cargo not in properties[target_index].animals:
                                properties[target_index].animals[cargo] = {"n": for_slaughter}
                            else:
                                properties[target_index].animals[cargo]["n"] += for_slaughter

                            movement_record.append(row)

            else:  # sink
                for ani_type in facility.animals:
                    for_slaughter = facility.animals[ani_type]["n"]

                    if for_slaughter > 0:
                        # clear the abattoir
                        facility.animals[ani_type]["n"] = 0
                        if "objs" in facility.animals[ani_type]:
                            del facility.animals[ani_type]["objs"]

                        row = [
                            day,
                            f"{date}",
                            premise_index,
                            -2,
                            ani_type,
                            for_slaughter,
                            facility.type,
                            "meat distributor",
                            -1,
                            f"DAY {date} - slaughtered and moved {for_slaughter} {ani_type} from {facility.type} (sim_id {facility.id}) ({facility.region}) to meat distributor",
                            facility.FMD_extra_info["herd_id"] if "herd_id" in facility.FMD_extra_info else "NA",
                            "NA",
                        ]

                        movement_record.append(row)

        elif facility.type == "export_facility":
            # sink
            for cargo_type in facility.animals:
                if facility.animals[cargo_type]["n"] > 0:
                    if "meat" not in cargo_type:
                        if in_control_zone or in_reduced_movement_zone:
                            print(
                                f"{facility.type} (sim_id {facility.id}) would like to export {cargo_type} but is inside control/movement controlled area"
                            )
                            number_of_movement_requests = 1
                        else:
                            # flag for export of ill animals
                            num_infectious_on_board = 0
                            if "objs" in facility.animals[cargo_type]:
                                for a in facility.animals[cargo_type]["objs"]:
                                    if a.infection_status in ["exposed", "infectious"]:
                                        num_infectious_on_board += 1

                            row = [
                                day,
                                f"{date}",
                                premise_index,
                                -3,
                                cargo_type,
                                facility.animals[cargo_type]["n"],
                                facility.type,
                                "overseas",
                                -3,
                                f"DAY {date} - live export of {facility.animals[cargo_type]['n']} {cargo_type} from {facility.type} (sim_id {facility.id}) ({facility.region}) to overseas (number exposed or infectious on board: {num_infectious_on_board})",
                                facility.FMD_extra_info["herd_id"] if "herd_id" in facility.FMD_extra_info else "NA",
                                "NA",
                            ]

                            movement_record.append(row)

                            facility.animals[cargo_type]["n"] = 0
                            if "objs" in facility.animals[cargo_type]:
                                del facility.animals[cargo_type]["objs"]

                    else:  # slaughtered meat
                        if in_control_zone and (random.uniform(0, 1) > movement_reduction_factor):
                            print(f"{facility.type} (sim_id {facility.id}) would like to export {cargo_type} but is inside restricted area")
                            number_of_movement_requests = 1
                        elif in_reduced_movement_zone and (random.uniform(0, 1) > movement_reduction_factor):
                            print(f"{facility.type} (sim_id {facility.id}) would like to export {cargo_type} but is inside control area")
                            number_of_movement_requests = 1
                        else:
                            row = [
                                day,
                                f"{date}",
                                premise_index,
                                -3,
                                cargo_type,
                                facility.animals[cargo_type]["n"],
                                facility.type,
                                "overseas",
                                -3,
                                f"DAY {date} - export of {facility.animals[cargo_type]['n']} {cargo_type} from {facility.type} (sim_id {facility.id}) ({facility.region}) to overseas",
                                facility.FMD_extra_info["herd_id"] if "herd_id" in facility.FMD_extra_info else "NA",
                                "NA",
                            ]

                            movement_record.append(row)

                            facility.animals[cargo_type]["n"] = 0

        elif facility.type == "milk_processing":
            # sink
            if "milk" in facility.animals and facility.animals["milk"]["n"] > 0:

                row = [
                    day,
                    f"{date}",
                    premise_index,
                    -4,
                    "milk",
                    facility.animals["milk"]["n"],
                    facility.type,
                    "dairy foods distributor",
                    -4,
                    f"DAY {date} - milk transported from {facility.type} (sim_id {facility.id}) ({facility.region}) to dairy foods distributors",
                    facility.FMD_extra_info["herd_id"] if "herd_id" in facility.FMD_extra_info else "NA",
                    "NA",
                ]

                movement_record.append(row)

                facility.animals["milk"]["n"] = 0

        else:
            raise ValueError(f"Unexpected facility type {facility.type} ")

    # in transit - complete movements
    # at the end, move the animals from the temporary dictionary into the new properties
    for truck_id in in_transit:

        # if the animals are infectious, then the truck should get a contamination level
        num_infectious_on_board = 0
        new_infections = 0
        num_exposed = 0
        if "objs" in in_transit[truck_id]:
            for a in in_transit[truck_id]["objs"]:
                if a.infection_status == "infectious":
                    num_infectious_on_board += 1

                    # probably want some beta_wind based on the animal type, some kind of FOI here, for the contamination level
                    # alternatively, if the truck is already contaminated, then the animals could get sick...!
                    # TODO
                if a.infection_status == "exposed":
                    num_exposed += 1
        if num_exposed > 0:
            print(f"exposed animals on truck {truck_id}")
        if num_infectious_on_board > 0:  # won't be milk
            # contaminate the truck
            FOI_ish = num_infectious_on_board * disease_parameters[in_transit[truck_id]["cargo"]]["beta_wind"] * truck_contanmination_infection_factor
            trucks_df.loc[trucks_df["truck_id"] == truck_id, "contamination"] += FOI_ish
            print(f"infectious animals on truck {truck_id}")
        else:  # see if the truck is contaminated and therefore can infect the animals
            existing_contamination = list(trucks_df[trucks_df["truck_id"] == truck_id].contamination)[0]
            if existing_contamination > 0:
                if "objs" not in in_transit[truck_id]:
                    in_transit[truck_id]["objs"] = [Animal(None) for _ in range(in_transit[truck_id]["n"])]

                params = disease_parameters[in_transit[truck_id]["cargo"]]

                for anim in in_transit[truck_id]["objs"]:
                    animal_inf = anim.infection_event(params, existing_contamination)
                    # just makes some of them exposed
                    new_infections += animal_inf

                    # TODO/ to think about: if infected, should I add cumulative infections at the property level... ???
                    # if animal_inf:
                    #     self.cumulative_infections += 1
                    #     if ani_type in self.cumulative_infections_by_animal_type:
                    #         self.cumulative_infections_by_animal_type[ani_type] += 1
                    #     else:
                    #         self.cumulative_infections_by_animal_type[ani_type] = 1
                    # anim.check_transition(params)
                    # anim.update_clock()

        # now transport; may need to align animal objects
        new_facility = properties[in_transit[truck_id]["target"]]
        if in_transit[truck_id]["cargo"] not in new_facility.animals:
            new_facility.animals[in_transit[truck_id]["cargo"]] = {"n": in_transit[truck_id]["n"]}
        else:
            new_facility.animals[in_transit[truck_id]["cargo"]]["n"] += in_transit[truck_id]["n"]

        if "objs" in new_facility.animals[in_transit[truck_id]["cargo"]]:
            if "objs" not in in_transit[truck_id]:
                in_transit[truck_id]["objs"] = [Animal(None) for _ in range(in_transit[truck_id]["n"])]
            new_facility.animals[in_transit[truck_id]["cargo"]]["objs"].extend(in_transit[truck_id]["objs"])
        else:
            if (
                num_exposed == 0 and new_infections == 0 and num_infectious_on_board == 0 and "objs" in in_transit[truck_id]
            ):  # nothing actually infected
                del in_transit[truck_id]["objs"]

            if "objs" in in_transit[truck_id]:
                new_facility.init_animals(None)
                new_facility.animals[in_transit[truck_id]["cargo"]]["objs"].extend(in_transit[truck_id]["objs"])

    # discard the in_transit dictionary - should be automatic

    # and do some "truck cleaning"
    trucks_df.loc[:, "contamination"] = trucks_df["contamination"] * truck_cleaning
    # and convert all trucks to not being busy again.
    trucks_df.loc[:, "busy"] = False

    print(f"movements for day {day} / {date} completed")

    movement_record = pd.DataFrame(movement_record, columns=movement_record_header)

    return movement_record, number_of_movement_requests, trucks_df
