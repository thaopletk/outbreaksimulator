import sys
import os
import json
import pickle

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import numpy as np

# from shapely.geometry import Point
# import csv
# import math
import matplotlib.pyplot as plt
import simulator.spatial_setup as spatial_setup
import simulator.management as management
import simulator.premises as premises
import simulator.SEIR as SEIR
import simulator.output as output
import simulator.animal_movement as animal_movement
import simulator.spatial_functions as spatial_functions
from shapely.ops import transform, unary_union
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, MultiPoint
import geopandas as gpd
import contextily as ctx
from matplotlib_scalebar.scalebar import ScaleBar
import pandas as pd
import csv


def save_special_data_file(folder_path, filename, properties, culled, confirmed_infected, DCP, TPs_undergoing_testing):

    # print output: all
    header = [
        "id",
        "status",
        "ip",
        "clinical_date",
        "notification_date",
        "removal_date",
        "recovery_date",
        "vacc_date",
        "address",
        "long",
        "lat",
        "area_h",
        "type",
        "total_animals",
    ]
    file = os.path.join(folder_path, f"data_sitrep_{filename}.csv")
    with open(file, "w", newline="") as f:

        # create the csv writer
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

        for index, premise in enumerate(properties):
            if index in culled or index in confirmed_infected:
                row = [
                    premise.id,
                    "RP" if index in culled else "IP",  # status
                    premise.ip,
                    premise.clinical_date,
                    premise.notification_date,
                    premise.removal_date,
                    premise.recovery_date,
                    premise.vacc_date,
                    premise.location,
                    premise.coordinates[0],
                    premise.coordinates[1],
                    premise.area,
                    premise.type,
                    premise.size,
                ]
            elif index in DCP or index in TPs_undergoing_testing:
                if premise.notification_date != "NA":
                    raise ValueError("Notification date should be NA")
                row = [
                    premise.id,
                    "DCP/SP" if index in DCP else "TP",  # status
                    premise.ip,
                    "NA",  # self.clinical_date,
                    premise.notification_date,
                    premise.removal_date,
                    premise.recovery_date,
                    premise.vacc_date,
                    premise.location,
                    premise.coordinates[0],
                    premise.coordinates[1],
                    premise.area,
                    premise.type,
                    premise.size,
                ]
            else:
                row = [
                    premise.id,
                    "NA",  # status
                    premise.ip,
                    "NA",  # self.clinical_date,
                    premise.notification_date,
                    premise.removal_date,
                    premise.recovery_date,
                    premise.vacc_date,
                    premise.location,
                    premise.coordinates[0],
                    premise.coordinates[1],
                    premise.area,
                    premise.type,
                    premise.size,
                ]

            writer.writerow(row)


def calculate_new_statuses(folder_path, properties, diseaseoutbreak):

    narrative = pd.read_csv(os.path.join(folder_path, "combinated_narrative.csv"))

    reported = narrative[narrative["type"] == "report"]

    reported_narrative = reported[reported["report"].str.contains("has been reported possible infection")]

    self_reported_list = reported_narrative["property"].values.tolist()
    self_reported_list = [int(x) for x in self_reported_list]

    # print(self_reported_list)

    culled = []
    confirmed_infected = []
    DCP = []

    TPs = []

    for index, premise in enumerate(properties):
        if premise.culled_status == True:
            culled.append(index)

            contact_tracing_report, traced_property_indices = management.contact_tracing(
                properties, index, diseaseoutbreak.movement_records, time
            )
            TPs.extend(traced_property_indices)

        elif premise.reported_status == True:
            confirmed_infected.append(index)

            contact_tracing_report, traced_property_indices = management.contact_tracing(
                properties, index, diseaseoutbreak.movement_records, time
            )
            TPs.extend(traced_property_indices)

        elif premise.clinical_report_outcome == True or premise.status == "DCP" or index in self_reported_list:
            DCP.append(index)

            contact_tracing_report, traced_property_indices = management.contact_tracing(
                properties, index, diseaseoutbreak.movement_records, time
            )
            TPs.extend(traced_property_indices)

    TPs = list(set(TPs))

    # final_TPs = []
    TPs_undergoing_testing = []
    TPs_false_result = []
    for index in TPs:
        if index in culled or index in confirmed_infected or index in DCP:
            pass
        else:
            # final_TPs.append(index)
            if properties[index].clinical_report_outcome == False:
                if properties[index].undergoing_testing == True:
                    TPs_undergoing_testing.append(index)  # aka, it's still waiting for a lab test...
                else:
                    TPs_false_result.append(index)
            elif (
                properties[index].undergoing_testing == True
            ):  # clinical_report_outcome == None; means that it's waiting for a clinical team AND a lab test
                TPs_undergoing_testing.append(index)
    return culled, confirmed_infected, DCP, TPs_undergoing_testing


folder_path_main = os.path.join(os.path.dirname(__file__), "outputs", "v03_trial")

undetected_spread_version = 49
detected_spread_version = 12


unique_output = f"{undetected_spread_version}_04_two_weeks_{detected_spread_version}"
folder_path = os.path.join(folder_path_main, unique_output)

#############################################
# read in relevant data--
day = 82

plotting_data_name = os.path.join(folder_path, f"plotting_data{day}")
with open(plotting_data_name, "rb") as file:
    properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

diseaseoutbreak_filename = os.path.join(folder_path, f"outbreakobject_{unique_output}")
with open(diseaseoutbreak_filename, "rb") as file:
    diseaseoutbreak = pickle.load(file)


culled, confirmed_infected, DCP, TPs_undergoing_testing = calculate_new_statuses(
    folder_path, properties, diseaseoutbreak
)

save_special_data_file(folder_path, "1", properties, culled, confirmed_infected, DCP, TPs_undergoing_testing)


#############################################
two_weeks_version = 8

day = 96

for resource_setting in ["high", "low"]:

    unique_output = (
        f"{undetected_spread_version}_{detected_spread_version}_05_two_weeks_{two_weeks_version}_{resource_setting}"
    )
    folder_path = os.path.join(folder_path_main, unique_output)

    #############################################
    # read in relevant data--

    plotting_data_name = os.path.join(folder_path, f"plotting_data{day}")
    with open(plotting_data_name, "rb") as file:
        properties, time, xlims, ylims, controlzone, contacts_for_plotting = pickle.load(file)

    diseaseoutbreak_filename = os.path.join(folder_path, f"outbreakobject_{unique_output}")
    with open(diseaseoutbreak_filename, "rb") as file:
        diseaseoutbreak = pickle.load(file)

    culled, confirmed_infected, DCP, TPs_undergoing_testing = calculate_new_statuses(
        folder_path, properties, diseaseoutbreak
    )

    save_special_data_file(
        folder_path, "2_" + resource_setting, properties, culled, confirmed_infected, DCP, TPs_undergoing_testing
    )
