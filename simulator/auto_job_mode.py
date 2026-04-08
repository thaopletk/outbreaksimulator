"""Aim: script that automatically generates job files (csvs), but on a more short-term one-day-at-a-time basis"""

import pandas as pd
import os
import numpy as np
from datetime import datetime as dt
from datetime import timedelta
import simulator.spatial_functions as spatial_functions


def generate_jobs(folder_path, approx_data_csv, scheduled_date, action_number, max_resource_units=100, strategy="default"):
    """
    Available strategies: 'default', 'surveillance', and 'faster depop'"""
    approx_data = pd.read_csv(os.path.join(folder_path, approx_data_csv))

    resource_cost = {
        "ClinicalObservation": 1,
        "ContactTracing": 1,
        "LabTesting": 2,
        "Cull": 4,
        "Phone Surveillance": 0.5,
        "Field Surveillance": 2,
        "Self-reporting Surveillance": 0.5,
        "Population-level Surveillance": 3,
        "Wild Animal Surveillance": 3,
        "Environmental Surveillance": 3,
        "Missing Properties Survey": 3,
    }

    min_delays = {
        "ClinicalObservation": 0,
        "ContactTracing": 0,
        "LabTesting": 0,
        "Cull": 1,
        "Phone Surveillance": 0,
        "Field Surveillance": 0,
        "Self-reporting Surveillance": 1,
        "Population-level Surveillance": 0,
        "Wild Animal Surveillance": 0,
        "Environmental Surveillance": 0,
        "Missing Properties Survey": 0,
    }

    resource_cost_culling_per_16k = 4
    cull_capacity = 16000
    if strategy == "faster depop":
        cull_capacity = 100000
        min_delays["Cull"] = 0

    min_delays = {key: timedelta(days=item) for key, item in min_delays.items()}

    resources_used = 0
    scheduled_date_object = dt.strptime(scheduled_date, "%d/%m/%Y")

    # jobs
    jobs_header = ["ID", "date_scheduled", "action", "specific_action", "detection_prob", "num", "Free text notes"]
    jobs_rows = []
    # top priority: IPs
    IPs = approx_data[approx_data["status"] == "IP"]
    IPs = IPs.sort_values("ip")
    for i, row in IPs.iterrows():
        if dt.strptime(row["last_PCR_date"], "%d/%m/%Y") + min_delays["Cull"] <= scheduled_date_object and row["total_chickens"] > 0:
            sheds = int(row["sheds"])
            if pd.isna(row["culled_birds"]):
                total_birds = int(row["total_chickens"])
            else:
                total_birds = int(row["culled_birds"] + row["total_chickens"])
            approx_chicken_per_shed = np.ceil(total_birds / sheds)

            max_to_cull = max(cull_capacity, approx_chicken_per_shed)

            actual_chickens_left_to_cull = int(row["total_chickens"])

            actual_cull = min(actual_chickens_left_to_cull, max_to_cull)

            job_row = [row["sim_id"], scheduled_date, "Cull", "", "", actual_cull, "IP"]
            jobs_rows.append(job_row)
            resources_used += int(
                np.ceil((actual_cull / 16000)) * resource_cost_culling_per_16k
            )  # reduce resource cost if there are less chickens to actually cull

        # contact tracing if not yet done
        if pd.isna(row["last_conducted_contact_tracing"]):
            if dt.strptime(row["last_surveillance_date"], "%d/%m/%Y") + min_delays["ContactTracing"] <= scheduled_date_object:
                job_row = [row["sim_id"], scheduled_date, "ContactTracing", "", "", "", "IP"]
                jobs_rows.append(job_row)
                resources_used += resource_cost["ContactTracing"]

    SPs = approx_data[approx_data["status"] == "SP"]  # suspect properties; all self-reported
    SPs = SPs.sort_values("case_id")
    for i, row in SPs.iterrows():
        try:
            self_report_date = dt.strptime(row["self_report_date"], "%d/%m/%Y")
        except:
            # for non-self-reported
            self_report_date = dt.strptime(row["last_surveillance_date"], "%d/%m/%Y")
        if pd.isna(row["last_surveillance_date"]) and self_report_date + min_delays["ClinicalObservation"] <= scheduled_date_object:
            job_row = [row["sim_id"], scheduled_date, "ClinicalObservation", "", "", "", "SP"]
            if resources_used < max_resource_units:
                jobs_rows.append(job_row)
                resources_used += resource_cost["ClinicalObservation"]
        if pd.isna(row["last_PCR_date"]) and self_report_date + min_delays["LabTesting"] <= scheduled_date_object:
            job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "SP"]
            if resources_used < max_resource_units:
                jobs_rows.append(job_row)
                resources_used += resource_cost["LabTesting"]

        if pd.isna(row["last_conducted_contact_tracing"]) and self_report_date + min_delays["ContactTracing"] <= scheduled_date_object:
            if resources_used < max_resource_units:
                job_row = [row["sim_id"], scheduled_date, "ContactTracing", "", "", "", "SP"]
                jobs_rows.append(job_row)
                resources_used += resource_cost["ContactTracing"]

    TPs = approx_data[approx_data["status"] == "TP"]  # trace properties
    TPs = TPs.sort_values("case_id")

    count_row = TPs.shape[0]
    if count_row * resource_cost["Phone Surveillance"] > (max_resource_units - resources_used):
        # if there are too many TPs and not enough resources
        # then: either go with phone surveillence if there are REALLY too much, or otherwise go with some clinial observations/site visits
        TPaction = "Phone Surveillance"
    elif count_row * resource_cost["ClinicalObservation"] > (max_resource_units - resources_used):
        TPaction = "ClinicalObservation"
    else:
        TPaction = "ClinicalObservation"

    for i, row in TPs.iterrows():
        if strategy == "surveillance":
            if pd.isna(row["last_surveillance_date"]):
                if resources_used < max_resource_units:
                    job_row = [row["sim_id"], scheduled_date, "ClinicalObservation", "", "", "", "TP"]
                    jobs_rows.append(job_row)
                    resources_used += resource_cost[TPaction]
            if pd.isna(row["last_PCR_date"]):
                if resources_used < max_resource_units:
                    job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "TP"]
                    jobs_rows.append(job_row)
                    resources_used += resource_cost["LabTesting"]
        else:
            if pd.isna(row["last_surveillance_date"]):
                if resources_used < max_resource_units:
                    job_row = [row["sim_id"], scheduled_date, TPaction, "", "", "", "TP"]
                    jobs_rows.append(job_row)
                    resources_used += resource_cost[TPaction]
            else:
                if row["data_source"] == "Phone Surveillance":
                    if TPaction != "Phone Surveillance":
                        if resources_used < max_resource_units:
                            job_row = [row["sim_id"], scheduled_date, "Surveillance", "Field Surveillance", "", "", "TP"]
                            jobs_rows.append(job_row)
                            resources_used += resource_cost["Field Surveillance"]
                else:
                    if TPaction != "Phone Surveillance":
                        if (
                            pd.isna(row["last_PCR_date"])
                            and dt.strptime(row["last_surveillance_date"], "%d/%m/%Y") + min_delays["LabTesting"] <= scheduled_date_object
                        ):
                            if resources_used < max_resource_units:
                                job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "TP"]
                                jobs_rows.append(job_row)
                                resources_used += resource_cost["LabTesting"]

    DCPs = approx_data[approx_data["status"] == "DCP"]
    DCPs = DCPs.sort_values("case_id")
    # probably just schedule a lab test with an extra delay (less important)
    for i, row in DCPs.iterrows():
        if strategy == "surveillance":
            if pd.isna(row["last_surveillance_date"]):
                if resources_used < max_resource_units:
                    job_row = [row["sim_id"], scheduled_date, TPaction, "", "", "", "DCP"]
                    jobs_rows.append(job_row)
                    resources_used += resource_cost[TPaction]
            if pd.isna(row["last_PCR_date"]):
                if resources_used < max_resource_units:
                    job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "DCP"]
                    jobs_rows.append(job_row)
                    resources_used += resource_cost["LabTesting"]
        else:
            if pd.isna(row["last_surveillance_date"]):
                if resources_used < max_resource_units:
                    job_row = [row["sim_id"], scheduled_date, TPaction, "", "", "", "DCP"]
                    jobs_rows.append(job_row)
                    resources_used += resource_cost[TPaction]
            else:
                if (
                    pd.isna(row["last_PCR_date"])
                    and dt.strptime(row["last_surveillance_date"], "%d/%m/%Y") + min_delays["LabTesting"] + timedelta(days=2) <= scheduled_date_object
                ):
                    if resources_used < max_resource_units:
                        job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "DCP"]
                        jobs_rows.append(job_row)
                        resources_used += resource_cost["LabTesting"]

    ARPs = approx_data[approx_data["status"] == "ARP"]
    ARPs = ARPs.sort_values("case_id")
    for i, row in ARPs.iterrows():
        if pd.isna(row["last_surveillance_date"]):
            if resources_used < max_resource_units:
                job_row = [row["sim_id"], scheduled_date, "Surveillance", "Field Surveillance", "", "", "ARP"]
                jobs_rows.append(job_row)
                resources_used += resource_cost["Field Surveillance"]
            if resources_used < max_resource_units:
                job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "ARP"]
                jobs_rows.append(job_row)
                resources_used += resource_cost["LabTesting"]
        else:
            if pd.isna(row["last_PCR_date"]):
                if dt.strptime(row["last_surveillance_date"], "%d/%m/%Y") + min_delays["LabTesting"] <= scheduled_date_object:
                    if resources_used < max_resource_units:
                        job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "ARP"]
                        jobs_rows.append(job_row)
                        resources_used += resource_cost["LabTesting"]
            else:
                if dt.strptime(row["last_PCR_date"], "%d/%m/%Y") + timedelta(days=7) <= scheduled_date_object:
                    if resources_used < max_resource_units:
                        job_row = [row["sim_id"], scheduled_date, "Surveillance", "Field Surveillance", "", "", "ARP"]
                        jobs_rows.append(job_row)
                        resources_used += resource_cost["Field Surveillance"]

                        job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "ARP"]
                        jobs_rows.append(job_row)
                        resources_used += resource_cost["LabTesting"]

    PORs = approx_data[approx_data["status"] == "POR"]
    PORs = PORs.sort_values("case_id")
    for i, row in PORs.iterrows():
        if pd.isna(row["last_surveillance_date"]):
            if resources_used < max_resource_units:
                job_row = [row["sim_id"], scheduled_date, "Surveillance", "Field Surveillance", "", "", "POR"]
                jobs_rows.append(job_row)
                resources_used += resource_cost["Field Surveillance"]
            if resources_used < max_resource_units:
                job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "POR"]
                jobs_rows.append(job_row)
                resources_used += resource_cost["LabTesting"]

        else:
            if pd.isna(row["last_PCR_date"]):
                if dt.strptime(row["last_surveillance_date"], "%d/%m/%Y") + min_delays["LabTesting"] <= scheduled_date_object:
                    if resources_used < max_resource_units:
                        job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "POR"]
                        jobs_rows.append(job_row)
                        resources_used += resource_cost["LabTesting"]
            else:
                if dt.strptime(row["last_PCR_date"], "%d/%m/%Y") + timedelta(days=7) <= scheduled_date_object:
                    if resources_used < max_resource_units:
                        job_row = [row["sim_id"], scheduled_date, "Surveillance", "Field Surveillance", "", "", "POR"]
                        jobs_rows.append(job_row)
                        resources_used += resource_cost["Field Surveillance"]

                        job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "POR"]
                        jobs_rows.append(job_row)
                        resources_used += resource_cost["LabTesting"]

    UPs = approx_data[approx_data["status"] == "UP"]
    UPs = UPs.sort_values("case_id")
    # phone surveillance to determine info about it
    for i, row in UPs.iterrows():
        if pd.isna(row["last_surveillance_date"]):
            if resources_used < max_resource_units:
                job_row = [row["sim_id"], scheduled_date, "Phone Surveillance", "", "", "", "UP"]
                jobs_rows.append(job_row)
                resources_used += resource_cost[TPaction]

    ZPs = approx_data[approx_data["status"] == "ZP"]
    ZPs = ZPs.sort_values("case_id")
    # do nothing

    RPs = approx_data[approx_data["status"] == "RP"]
    RPs = RPs.sort_values("case_id")
    # do nothing

    # zone jobs
    zone_jobs_header = ["ID", "date_scheduled", "radius_km", "action", "zone_name", "zone_parameter", "Free text notes"]
    zone_jobs_rows = []
    if strategy == "surveillance":
        for i, row in IPs.iterrows():
            if dt.strptime(row["last_PCR_date"], "%d/%m/%Y") + timedelta(days=1) == scheduled_date_object:
                if resources_used < max_resource_units:
                    job_row = [row["sim_id"], scheduled_date, 5, "Population-level Surveillance", row["sim_id"], "", "surveillance around IP"]
                    zone_jobs_rows.append(job_row)
                    resources_used += resource_cost["Population-level Surveillance"]

                if resources_used < max_resource_units:
                    job_row = [row["sim_id"], scheduled_date, 5, "Wild Animal Surveillance", row["sim_id"], "", "surveillance around IP"]
                    zone_jobs_rows.append(job_row)
                    resources_used += resource_cost["Wild Animal Surveillance"]

                if resources_used < max_resource_units:
                    job_row = [row["sim_id"], scheduled_date, 5, "Missing Properties Survey", row["sim_id"], "", "surveillance around IP"]
                    zone_jobs_rows.append(job_row)
                    resources_used += resource_cost["Missing Properties Survey"]

    # zones
    zones_header = ["ID", "radius_km", "zone_type", "zone_parameter", "Free text notes"]
    zone_rows = []
    for i, row in IPs.iterrows():
        zone_row = [row["sim_id"], 5, "RA", "", ""]
        zone_rows.append(zone_row)
        if strategy == "surveillance":
            zone_row = [row["sim_id"], 20, "CA", "", ""]  # exapnd to get more PORs or ARPs
        else:
            zone_row = [row["sim_id"], 10, "CA", "", ""]
        zone_rows.append(zone_row)

    for i, row in RPs.iterrows():
        zone_row = [row["sim_id"], 5, "RA", "", ""]
        zone_rows.append(zone_row)

        if strategy == "surveillance":
            zone_row = [row["sim_id"], 20, "CA", "", ""]
        else:
            zone_row = [row["sim_id"], 10, "CA", "", ""]
        zone_rows.append(zone_row)

    for i, row in SPs.iterrows():
        zone_row = [row["sim_id"], 0.2, "RA", "", ""]
        zone_rows.append(zone_row)

        if strategy == "surveillance":
            zone_row = [row["sim_id"], 20, "CA", "", ""]
        else:
            zone_row = [row["sim_id"], 0.2, "CA", "", ""]
        zone_rows.append(zone_row)

    for i, row in TPs.iterrows():
        zone_row = [row["sim_id"], 0.2, "RA", "", ""]
        zone_rows.append(zone_row)

        zone_row = [row["sim_id"], 0.2, "CA", "", ""]
        zone_rows.append(zone_row)

    for i, row in DCPs.iterrows():
        zone_row = [row["sim_id"], 0.2, "RA", "", ""]
        zone_rows.append(zone_row)

        zone_row = [row["sim_id"], 0.2, "CA", "", ""]
        zone_rows.append(zone_row)

    # general super enhanced passive surveillance across NSW
    zone_row = [3, 1200, "Enhanced Passive Surveillance", "", "NSW-wide enhanced passive surveillance"]
    zone_rows.append(zone_row)

    # and then if there are extra resources, then ---
    print(f"Resources left: {max_resource_units-resources_used}")

    # and then save
    jobs_df = pd.DataFrame(jobs_rows, columns=jobs_header)
    jobs_df.to_csv(os.path.join(folder_path, f"jobs_{action_number}.csv"), index=False)

    zone_jobs_df = pd.DataFrame(zone_jobs_rows, columns=zone_jobs_header)
    zone_jobs_df.to_csv(os.path.join(folder_path, f"zone_jobs_{action_number}.csv"), index=False)

    zones_df = pd.DataFrame(zone_rows, columns=zones_header)
    zones_df.to_csv(os.path.join(folder_path, f"zones_{action_number}.csv"), index=False)


def generate_ARP_POR_jobs_only(folder_path, approx_data_csv, scheduled_date, output_file_name):
    approx_data = pd.read_csv(os.path.join(folder_path, approx_data_csv))

    # jobs
    jobs_header = ["ID", "date_scheduled", "action", "specific_action", "detection_prob", "num", "Free text notes"]
    jobs_rows = []

    scheduled_date_object = dt.strptime(scheduled_date, "%d/%m/%Y")

    ARPs = approx_data[approx_data["status"] == "ARP"]
    ARPs = ARPs.sort_values("case_id")
    for i, row in ARPs.iterrows():
        if pd.isna(row["last_surveillance_date"]):
            job_row = [row["sim_id"], scheduled_date, "Surveillance", "Field Surveillance", "", "", "ARP"]
            jobs_rows.append(job_row)
            job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "ARP"]
            jobs_rows.append(job_row)
        else:
            if pd.isna(row["last_PCR_date"]):
                job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "ARP"]
                jobs_rows.append(job_row)
            else:
                if dt.strptime(row["last_PCR_date"], "%d/%m/%Y") + timedelta(days=7) <= scheduled_date_object:
                    job_row = [row["sim_id"], scheduled_date, "Surveillance", "Field Surveillance", "", "", "ARP"]
                    jobs_rows.append(job_row)

                    job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "ARP"]
                    jobs_rows.append(job_row)

    PORs = approx_data[approx_data["status"] == "POR"]
    PORs = PORs.sort_values("case_id")
    for i, row in PORs.iterrows():
        if pd.isna(row["last_surveillance_date"]):
            job_row = [row["sim_id"], scheduled_date, "Surveillance", "Field Surveillance", "", "", "POR"]
            jobs_rows.append(job_row)
            job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "POR"]
            jobs_rows.append(job_row)

        else:
            if pd.isna(row["last_PCR_date"]):
                job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "POR"]
                jobs_rows.append(job_row)
            else:
                if dt.strptime(row["last_PCR_date"], "%d/%m/%Y") + timedelta(days=7) <= scheduled_date_object:
                    job_row = [row["sim_id"], scheduled_date, "Surveillance", "Field Surveillance", "", "", "POR"]
                    jobs_rows.append(job_row)

                    job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "POR"]
                    jobs_rows.append(job_row)
    jobs_df = pd.DataFrame(jobs_rows, columns=jobs_header)
    jobs_df.to_csv(os.path.join(folder_path, f"{output_file_name}.csv"), index=False)


def generate_jobs_teams(folder_path, approx_data_csv, scheduled_date, action_number, strategy="fast DDD"):
    """
    Available strategies:  "fast DDD" and "slow DDD"
    """

    approx_data = pd.read_csv(os.path.join(folder_path, approx_data_csv))

    # "teams" is actually the number of jobs that can be done a day
    teams = {
        "DDD": 6,
        "ContactTracing": 2,
        "Surveillance": 100,
    }

    delays = {"ContactTracing": timedelta(days=2)}

    if strategy == "fast DDD":
        delays["DDD"] = timedelta(days=7)
    elif strategy == "slow DDD":
        delays["DDD"] = timedelta(days=21)
    else:
        raise ValueError(f"strategy '{strategy}' not expected")

    scheduled_date_object = dt.strptime(scheduled_date, "%d/%m/%Y")

    # jobs
    jobs_header = ["ID", "date_scheduled", "action", "specific_action", "detection_prob", "num", "Free text notes"]
    jobs_rows = []

    # top priority: IPs
    IPs = approx_data[approx_data["status"] == "IP"]
    IPs = IPs.sort_values("ip")

    for i, row in IPs.iterrows():
        if row["enterprise"] == "backyard":
            if int(row["sim_id"]) % 2 == 0:
                pass  # we'll only depop the even sim_id's ((technically the animals should die anyway...))
            else:
                continue  # go to the next row

        if teams["DDD"] > 0 and dt.strptime(row["last_PCR_date"], "%d/%m/%Y") + delays["DDD"] <= scheduled_date_object:
            job_row = [row["sim_id"], scheduled_date, "Cull", "", "", row["total_chickens"], "IP"]
            jobs_rows.append(job_row)
            teams["DDD"] -= 1

        # contact tracing if not yet done
        if teams["ContactTracing"] > 0 and pd.isna(row["last_conducted_contact_tracing"]):
            if dt.strptime(row["last_surveillance_date"], "%d/%m/%Y") + delays["ContactTracing"] <= scheduled_date_object:
                job_row = [row["sim_id"], scheduled_date, "ContactTracing", "", "", "", "IP"]
                jobs_rows.append(job_row)
                teams["ContactTracing"] -= 1

    # SPs and DCPs and TPs are treated the same
    for status in ["SP", "DCP", "TP"]:
        SPs = approx_data[approx_data["status"] == status]  # suspect properties; all self-reported
        SPs = SPs.sort_values("case_id")
        for i, row in SPs.iterrows():
            if pd.isna(row["last_surveillance_date"]) and teams["Surveillance"] > 0:
                job_row = [row["sim_id"], scheduled_date, "ClinicalObservation", "", "", "", status]
                jobs_rows.append(job_row)
                job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", status]
                jobs_rows.append(job_row)

                teams["Surveillance"] -= 10  # in depth first investigation

            else:  # if it's still an SP, then it's not an IP....treating it like a DCP with ~2 inspections per week
                if teams["Surveillance"] > 0 and dt.strptime(row["last_surveillance_date"], "%d/%m/%Y") + timedelta(days=4) <= scheduled_date_object:
                    job_row = [row["sim_id"], scheduled_date, "Surveillance", "Field Surveillance", "", "", status]
                    jobs_rows.append(job_row)
                    job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", status]
                    jobs_rows.append(job_row)
                    teams["Surveillance"] -= 1  # a less in-depth investigation

    # ARPs and PORs are treated the same
    for status in ["ARP", "POR"]:
        properties = approx_data[approx_data["status"] == status]
        properties = properties.sort_values("case_id")
        for i, row in properties.iterrows():
            if pd.isna(row["last_surveillance_date"]) and teams["Surveillance"] > 0:
                job_row = [row["sim_id"], scheduled_date, "Surveillance", "Field Surveillance", "", "", status]
                jobs_rows.append(job_row)
                job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", status]
                jobs_rows.append(job_row)

                teams["Surveillance"] -= 1  # a less in-depth investigation
            else:  # if it's still an SP, then it's not an IP....treating it like a DCP with ~2 inspections per week
                if teams["Surveillance"] > 0 and dt.strptime(row["last_surveillance_date"], "%d/%m/%Y") + timedelta(days=7) <= scheduled_date_object:
                    job_row = [row["sim_id"], scheduled_date, "Surveillance", "Field Surveillance", "", "", status]
                    jobs_rows.append(job_row)
                    job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", status]
                    jobs_rows.append(job_row)
                    teams["Surveillance"] -= 1  # a less in-depth investigation

    UPs = approx_data[approx_data["status"] == "UP"]
    UPs = UPs.sort_values("case_id")
    # phone surveillance to determine info about it
    for i, row in UPs.iterrows():
        if pd.isna(row["last_surveillance_date"]) and teams["Surveillance"] > 0:
            job_row = [row["sim_id"], scheduled_date, "Surveillance", "Field Surveillance", "", "", status]
            jobs_rows.append(job_row)
            job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", status]
            jobs_rows.append(job_row)
            teams["Surveillance"] -= 1

    # zone jobs
    zone_jobs_header = ["ID", "date_scheduled", "radius_km", "action", "zone_name", "zone_parameter", "Free text notes"]
    zone_jobs_rows = []

    job_row = ["", scheduled_date, "", "Wild Animal Surveillance", "Enhanced Passive Surveillance", "", ""]
    zone_jobs_rows.append(job_row)

    job_row = ["", scheduled_date, "", "Population-level Surveillance", "RA", "", ""]
    zone_jobs_rows.append(job_row)

    job_row = ["", scheduled_date, "", "Wild Animal Surveillance", "RA", "", ""]
    zone_jobs_rows.append(job_row)

    job_row = ["", scheduled_date, "", "Population-level Surveillance", "CA", "", ""]
    zone_jobs_rows.append(job_row)

    job_row = ["", scheduled_date, "", "Wild Animal Surveillance", "CA", "", ""]
    zone_jobs_rows.append(job_row)

    # zones

    zones_header = ["ID", "radius_km", "zone_type", "zone_parameter", "Free text notes"]
    zone_rows = []
    for status in ["IP", "RP"]:
        properties = approx_data[approx_data["status"] == status]
        for i, row in properties.iterrows():
            zone_row = [row["sim_id"], 3, "RA", "", ""]
            zone_rows.append(zone_row)

            zone_row = [row["sim_id"], 5, "CA", "", ""]
            zone_rows.append(zone_row)

    for status in ["SP", "TP", "DCP"]:
        properties = approx_data[approx_data["status"] == status]
        for i, row in properties.iterrows():
            zone_row = [row["sim_id"], 0.2, "RA", "", "IBD"]
            zone_rows.append(zone_row)

    print(teams)

    # and then save
    jobs_df = pd.DataFrame(jobs_rows, columns=jobs_header)
    jobs_df.to_csv(os.path.join(folder_path, f"jobs_{action_number}.csv"), index=False)

    zone_jobs_df = pd.DataFrame(zone_jobs_rows, columns=zone_jobs_header)
    zone_jobs_df.to_csv(os.path.join(folder_path, f"zone_jobs_{action_number}.csv"), index=False)

    zones_df = pd.DataFrame(zone_rows, columns=zones_header)
    zones_df.to_csv(os.path.join(folder_path, f"zones_{action_number}.csv"), index=False)


def generate_jobs_QLD(folder_path, approx_data_csv, scheduled_date, action_number, properties, strategy="normal_zones"):
    approx_data = pd.read_csv(os.path.join(folder_path, approx_data_csv))

    scheduled_date_object = dt.strptime(scheduled_date, "%d/%m/%Y")

    delays = {"ContactTracing": timedelta(days=2), "DDD": timedelta(days=2), "LabTesting": timedelta(days=1)}

    # jobs
    jobs_header = ["ID", "date_scheduled", "action", "specific_action", "detection_prob", "num", "Free text notes"]
    jobs_rows = []

    # top priority: IPs
    IPs = approx_data[approx_data["status"] == "IP"]
    IPs = IPs.sort_values("ip")

    culling_team_points = 8  # two teams, up to 4 properties each if they're small
    contact_tracing_points = 2

    for i, row in IPs.iterrows():
        if culling_team_points > 0 and dt.strptime(row["last_PCR_date"], "%d/%m/%Y") + delays["DDD"] <= scheduled_date_object:
            if row["total_chickens"] < 2000:
                job_row = [row["sim_id"], scheduled_date, "Cull", "", "", row["total_chickens"], "IP"]
                jobs_rows.append(job_row)
                culling_team_points -= 1
            else:
                job_row = [row["sim_id"], scheduled_date, "Cull", "", "", 15000, "IP"]
                jobs_rows.append(job_row)
                culling_team_points -= 4

    # checking contact tracing - go from large to small
    IPs = IPs.sort_values("total_chickens", ascending=False)
    for i, row in IPs.iterrows():
        if contact_tracing_points > 0 and pd.isna(row["last_conducted_contact_tracing"]):
            if dt.strptime(row["last_surveillance_date"], "%d/%m/%Y") + delays["ContactTracing"] <= scheduled_date_object:
                job_row = [row["sim_id"], scheduled_date, "ContactTracing", "", "", "", "IP"]
                jobs_rows.append(job_row)
                contact_tracing_points -= 1

    # SPs and DCPs and TPs are treated the same. Go with the properties that are either larger OR are close to something large
    SPDCP_site_visit = 5
    SPDCP_lab_testing = 5
    SPDCPs = approx_data[approx_data["status"].isin(["SP", "DCP", "TP"])]
    SPDCPs = SPDCPs.sort_values("total_chickens", ascending=False)
    for i, row in SPDCPs.iterrows():
        if row["enterprise"] not in ["abbatoir", "egg processing"]:
            if row["total_chickens"] > 1000:
                if pd.isna(row["last_surveillance_date"]) and SPDCP_site_visit > 0:
                    job_row = [row["sim_id"], scheduled_date, "ClinicalObservation", "", "", "", row["status"]]
                    jobs_rows.append(job_row)
                    SPDCP_site_visit -= 1
                elif (
                    not pd.isna(row["last_surveillance_date"])
                    and dt.strptime(row["last_surveillance_date"], "%d/%m/%Y") + delays["LabTesting"] <= scheduled_date_object
                    and SPDCP_lab_testing > 0
                ):
                    job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", row["status"]]
                    jobs_rows.append(job_row)
                    SPDCP_lab_testing -= 1
            else:
                # check if it's near anything or not
                focus_facility = properties[int(row["sim_id"])]
                close_to_commercial = False
                for j, facility in enumerate(properties):
                    if j != int(row["sim_id"]):
                        distance = spatial_functions.quick_distance_haversine(
                            focus_facility.coordinates,
                            facility.coordinates,
                        )
                        if distance < 2:
                            close_to_commercial = True
                            break

                if close_to_commercial:
                    if pd.isna(row["last_surveillance_date"]) and SPDCP_site_visit > 0:
                        job_row = [row["sim_id"], scheduled_date, "ClinicalObservation", "", "", "", row["status"]]
                        jobs_rows.append(job_row)
                        SPDCP_site_visit -= 1
                    elif (
                        not pd.isna(row["last_surveillance_date"])
                        and dt.strptime(row["last_surveillance_date"], "%d/%m/%Y") + delays["LabTesting"] <= scheduled_date_object
                        and SPDCP_lab_testing > 0
                    ):
                        job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", row["status"]]
                        jobs_rows.append(job_row)
                        SPDCP_lab_testing -= 1

    if SPDCP_site_visit > 0 or SPDCP_lab_testing > 0:  # i.e., there is capacity left
        for i, row in SPDCPs.iterrows():
            if row["enterprise"] not in ["abbatoir", "egg processing"]:
                if row["total_chickens"] < 1000:
                    focus_facility = properties[int(row["sim_id"])]
                    close_to_commercial = False
                    for j, facility in enumerate(properties):
                        if j != int(row["sim_id"]):
                            distance = spatial_functions.quick_distance_haversine(
                                focus_facility.coordinates,
                                facility.coordinates,
                            )
                            if distance < 2:
                                close_to_commercial = True
                                break
                    if not close_to_commercial:
                        if pd.isna(row["last_surveillance_date"]) and SPDCP_site_visit > 0:
                            job_row = [row["sim_id"], scheduled_date, "ClinicalObservation", "", "", "", row["status"]]
                            jobs_rows.append(job_row)
                            SPDCP_site_visit -= 1
                        elif (
                            not pd.isna(row["last_surveillance_date"])
                            and dt.strptime(row["last_surveillance_date"], "%d/%m/%Y") + delays["LabTesting"] <= scheduled_date_object
                            and SPDCP_lab_testing > 0
                        ):
                            job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", row["status"]]
                            jobs_rows.append(job_row)
                            SPDCP_lab_testing -= 1

    # ARPs and PORs are treated the same. Go with the properties that are either larger OR are close to something large
    SPDCP_site_visit = 5
    SPDCP_lab_testing = 5
    SPDCPs = approx_data[approx_data["status"].isin(["ARP", "POR"])]
    SPDCPs = SPDCPs.sort_values("total_chickens", ascending=False)
    for i, row in SPDCPs.iterrows():
        if row["enterprise"] not in ["abbatoir", "egg processing"]:
            if row["total_chickens"] > 1000:
                if pd.isna(row["last_surveillance_date"]) and SPDCP_site_visit > 0:
                    job_row = [row["sim_id"], scheduled_date, "ClinicalObservation", "", "", "", row["status"]]
                    jobs_rows.append(job_row)
                    SPDCP_site_visit -= 1
                elif (
                    not pd.isna(row["last_surveillance_date"])
                    and dt.strptime(row["last_surveillance_date"], "%d/%m/%Y") + delays["LabTesting"] <= scheduled_date_object
                    and SPDCP_lab_testing > 0
                ):
                    job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", row["status"]]
                    jobs_rows.append(job_row)
                    SPDCP_lab_testing -= 1
            else:
                # check if it's near anything or not
                focus_facility = properties[int(row["sim_id"])]
                close_to_commercial = False
                for j, facility in enumerate(properties):
                    if j != int(row["sim_id"]):
                        distance = spatial_functions.quick_distance_haversine(
                            focus_facility.coordinates,
                            facility.coordinates,
                        )
                        if distance < 2:
                            close_to_commercial = True
                            break

                if close_to_commercial:
                    if pd.isna(row["last_surveillance_date"]) and SPDCP_site_visit > 0:
                        job_row = [row["sim_id"], scheduled_date, "ClinicalObservation", "", "", "", row["status"]]
                        jobs_rows.append(job_row)
                        SPDCP_site_visit -= 1
                    elif (
                        not pd.isna(row["last_surveillance_date"])
                        and dt.strptime(row["last_surveillance_date"], "%d/%m/%Y") + delays["LabTesting"] <= scheduled_date_object
                        and SPDCP_lab_testing > 0
                    ):
                        job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", row["status"]]
                        jobs_rows.append(job_row)
                        SPDCP_lab_testing -= 1

    if SPDCP_site_visit > 0 or SPDCP_lab_testing > 0:  # i.e., there is capacity left
        for i, row in SPDCPs.iterrows():
            if row["enterprise"] not in ["abbatoir", "egg processing"]:
                if row["total_chickens"] < 1000:
                    focus_facility = properties[int(row["sim_id"])]
                    close_to_commercial = False
                    for j, facility in enumerate(properties):
                        if j != int(row["sim_id"]):
                            distance = spatial_functions.quick_distance_haversine(
                                focus_facility.coordinates,
                                facility.coordinates,
                            )
                            if distance < 2:
                                close_to_commercial = True
                                break
                    if not close_to_commercial:
                        if pd.isna(row["last_surveillance_date"]) and SPDCP_site_visit > 0:
                            job_row = [row["sim_id"], scheduled_date, "ClinicalObservation", "", "", "", row["status"]]
                            jobs_rows.append(job_row)
                            SPDCP_site_visit -= 1
                        elif (
                            not pd.isna(row["last_surveillance_date"])
                            and dt.strptime(row["last_surveillance_date"], "%d/%m/%Y") + delays["LabTesting"] <= scheduled_date_object
                            and SPDCP_lab_testing > 0
                        ):
                            job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", row["status"]]
                            jobs_rows.append(job_row)
                            SPDCP_lab_testing -= 1

    zone_jobs_header = ["ID", "date_scheduled", "radius_km", "action", "zone_name", "zone_parameter", "Free text notes"]
    zone_jobs_rows = []
    # nothing

    zones_header = ["ID", "radius_km", "zone_type", "zone_parameter", "Free text notes"]
    zone_rows = []
    IPs = approx_data[approx_data["status"].isin(["IP", "RP"])]
    for i, row in IPs.iterrows():
        if strategy == "normal_zones":
            zone_row = [row["sim_id"], 5, "RA", "", ""]
            zone_rows.append(zone_row)

            zone_row = [row["sim_id"], 15, "CA", "", ""]
            zone_rows.append(zone_row)
        elif strategy == "small_zones":
            zone_row = [row["sim_id"], 2, "RA", "", ""]
            zone_rows.append(zone_row)

            zone_row = [row["sim_id"], 7, "CA", "", ""]
            zone_rows.append(zone_row)

    for status in ["SP", "TP", "DCP"]:
        properties = approx_data[approx_data["status"] == status]
        for i, row in properties.iterrows():
            zone_row = [row["sim_id"], 0.2, "RA", "", "quarantine"]
            zone_rows.append(zone_row)

    # and then save
    jobs_df = pd.DataFrame(jobs_rows, columns=jobs_header)
    jobs_df.to_csv(os.path.join(folder_path, f"jobs_{action_number}.csv"), index=False)

    zone_jobs_df = pd.DataFrame(zone_jobs_rows, columns=zone_jobs_header)
    zone_jobs_df.to_csv(os.path.join(folder_path, f"zone_jobs_{action_number}.csv"), index=False)

    zones_df = pd.DataFrame(zone_rows, columns=zones_header)
    zones_df.to_csv(os.path.join(folder_path, f"zones_{action_number}.csv"), index=False)
