import os
import csv
import pandas as pd
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.premises as premises
import simulator.output as output
import simulator.fixed_spatial_setup as fixed_spatial_setup
import numpy as np

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

            # try:
            #     property_data_known = facility.custom_info["property_data_known"]
            # except:
            #     property_data_known = False

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
                    facility.animals,
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
    # TODO technically, to encapsulate this better, there should a function that allows you to infect a specific animal(s), and that will then update infection_status, prop_infections, cumulative_infections, and exposure_date, and anything else that may need to be updated
    p.infection_status = 1
    if latent_period != None:
        p.exposure_date = premises.convert_time_to_date(int_time - latent_period)
    else:  # the version with multiple animals
        latent_period = disease_parameters[p.animal_type]["latent_period"]
        p.exposure_date = premises.convert_time_to_date(int_time - latent_period)

    num_infected = min(10, p.animals)
    if len(p.animal_type) == 1:
        p.init_animals(None)

        for seed_animal in range(num_infected):
            p.animals[seed_animal].status = "infected"
    else:  # there could be several animal types here
        raise ValueError("Haven't yet coded up seeding a property with multiple animal types")

    p.prop_infectious = num_infected / p.get_num_animals()
    p.cumulative_infections = num_infected

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


def animal_movement(
    properties,
    day,
    controlzone,
    reduced_movement_zone=None,
    movement_reduction_factor=0.2,
    all_movement_reduction_factor=1.0,
):

    date = premises.convert_time_to_date(day)

    movement_record = []
    number_of_movement_requests = 0

    return movement_record, number_of_movement_requests
