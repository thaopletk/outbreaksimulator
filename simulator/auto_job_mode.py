"""Aim: script that automatically generates job files (csvs), but on a more short-term one-day-at-a-time basis"""

import pandas as pd
import os
import numpy as np


def generate_jobs(folder_path, approx_data_csv, scheduled_date, action_number, max_resource_units=100):
    approx_data = pd.read_csv(os.path.join(folder_path, approx_data_csv))

    resource_cost = {
        "ClinicalObservation": 2,
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
        "LabTesting": 2,
        "Cull": 2,
        "Phone Surveillance": 0,
        "Field Surveillance": 0,
        "Self-reporting Surveillance": 1,
        "Population-level Surveillance": 0,
        "Wild Animal Surveillance": 0,
        "Environmental Surveillance": 0,
        "Missing Properties Survey": 0,
    }

    resources_used = 0

    # jobs
    jobs_header = ["ID", "date_scheduled", "action", "specific_action", "detection_prob", "num", "Free text notes"]
    jobs_rows = []
    # top priority: IPs
    IPs = approx_data[approx_data["status"] == "IP"]
    IPs = IPs.sort_values("ip")
    for i, row in IPs.iterrows():
        if row["last_PCR_date"] + min_delays["Cull"] <= scheduled_date and row["total_chickens"] > 0:
            sheds = row["sheds"]
            total_birds = row["culled_birds"] + row["total_chickens"]
            approx_chicken_per_shed = np.ceil(total_birds / sheds)
            job_row = [row["sim_id"], scheduled_date, "Cull", "", "", approx_chicken_per_shed, "IP"]
            jobs_rows.append(job_row)
            resources_used += resource_cost["Cull"]

        if row["last_conducted_contact_tracing"] == "NA":
            if row["last_surveillance_date"] + min_delays["ContactTracing"] <= scheduled_date:
                job_row = [row["sim_id"], scheduled_date, "ContactTracing", "", "", "", "IP"]
                jobs_rows.append(job_row)
                resources_used += resource_cost["ContactTracing"]

        # TODO: contact tracing if not yet done

    SPs = approx_data[approx_data["status"] == "SP"]  # suspect properties; all self-reported
    SPs = SPs.sort_values("case_id")
    for i, row in SPs.iterrows():
        if row["last_surveillance_date"] == "NA":
            if row["self_report_date"] + min_delays["ClinicalObservation"] <= scheduled_date:
                job_row = [row["sim_id"], scheduled_date, "ClinicalObservation", "", "", "", "SP"]
                if resources_used < max_resource_units:
                    jobs_rows.append(job_row)
                    resources_used += resource_cost["ClinicalObservation"]
        else:
            if row["last_PCR_date"] == "NA" and row["last_surveillance_date"] + min_delays["LabTesting"] <= scheduled_date:
                job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "SP"]
                if resources_used < max_resource_units:
                    jobs_rows.append(job_row)
                    resources_used += resource_cost["LabTesting"]

        if row["last_conducted_contact_tracing"] == "NA" and row["animals_clinical"] == "TRUE":
            if row["last_surveillance_date"] + min_delays["ContactTracing"] <= scheduled_date:
                job_row = [row["sim_id"], scheduled_date, "ContactTracing", "", "", "", "IP"]
                jobs_rows.append(job_row)
                resources_used += resource_cost["ContactTracing"]

    TPs = approx_data[approx_data["status"] == "TPs"]  # trace properties
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
        pass  # go with clinical observations and/or lab testing
    for i, row in TPs.iterrows():
        if row["last_surveillance_date"] == "NA":
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
                    if row["last_PCR_date"] == "NA" and row["last_surveillance_date"] + min_delays["LabTesting"] <= scheduled_date:
                        if resources_used < max_resource_units:
                            job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "TP"]
                            jobs_rows.append(job_row)
                            resources_used += resource_cost["LabTesting"]

    DCPs = approx_data[approx_data["status"] == "DCP"]
    DCPs = DCPs.sort_values("case_id")
    # probably just schedule a lab test with an extra delay (less important)
    for i, row in DCPs.iterrows():
        if row["last_surveillance_date"] == "NA":
            if resources_used < max_resource_units:
                job_row = [row["sim_id"], scheduled_date, TPaction, "", "", "", "DCP"]
                jobs_rows.append(job_row)
                resources_used += resource_cost[TPaction]
        else:
            if row["last_PCR_date"] == "NA" and row["last_surveillance_date"] + min_delays["LabTesting"] + 2 <= scheduled_date:
                if resources_used < max_resource_units:
                    job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "DCP"]
                    jobs_rows.append(job_row)
                    resources_used += resource_cost["LabTesting"]

    ARPs = approx_data[approx_data["status"] == "ARP"]
    ARPs = ARPs.sort_values("case_id")
    for i, row in DCPs.iterrows():
        if row["last_surveillance_date"] == "NA":
            if resources_used < max_resource_units:
                job_row = [row["sim_id"], scheduled_date, TPaction, "", "", "", "TP"]
                jobs_rows.append(job_row)
                resources_used += resource_cost[TPaction]
        else:
            if row["last_PCR_date"] == "NA":
                if row["animals_clinical"] == "TRUE":
                    if row["last_surveillance_date"] + min_delays["LabTesting"] + 2 <= scheduled_date:
                        if resources_used < max_resource_units:
                            job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "ARP"]
                            jobs_rows.append(job_row)
                            resources_used += resource_cost["LabTesting"]

    PORs = approx_data[approx_data["status"] == "POR"]
    PORs = PORs.sort_values("case_id")
    for i, row in DCPs.iterrows():
        if row["last_surveillance_date"] == "NA":
            if resources_used < max_resource_units:
                job_row = [row["sim_id"], scheduled_date, TPaction, "", "", "", "TP"]
                jobs_rows.append(job_row)
                resources_used += resource_cost[TPaction]
        else:
            if row["last_PCR_date"] == "NA":
                if row["animals_clinical"] == "TRUE":
                    if row["last_surveillance_date"] + min_delays["LabTesting"] + 2 <= scheduled_date:
                        if resources_used < max_resource_units:
                            job_row = [row["sim_id"], scheduled_date, "LabTesting", "", "", "", "POR"]
                            jobs_rows.append(job_row)
                            resources_used += resource_cost["LabTesting"]

    UPs = approx_data[approx_data["status"] == "UP"]
    UPs = UPs.sort_values("case_id")
    # phone surveillance to determine info about it
    for i, row in DCPs.iterrows():
        if row["last_surveillance_date"] == "NA":
            if resources_used < max_resource_units:
                job_row = [row["sim_id"], scheduled_date, "Phone Surveillance", "", "", "", "UP"]
                jobs_rows.append(job_row)
                resources_used += resource_cost[TPaction]

    ZPs = approx_data[approx_data["status"] == "ZP"]
    ZPs = ZPs.sort_values("case_id")
    # do nothing

    RPs = approx_data[approx_data["status"] == "RP"]
    RPs = ZPs.sort_values("case_id")
    # do nothing

    # zone jobs
    zone_jobs_header = ["ID", "date_scheduled", "radius_km", "action", "zone_name", "zone_parameter", "Free text notes"]
    zone_jobs_rows = []
    # skip for now

    # zones
    zones_header = ["ID", "radius_km", "zone_type", "Free text notes"]
    zone_rows = []
    for i, row in IPs.iterrows():
        zone_row = [row["sim_id"], 5, "RA", ""]
        zone_rows.append(zone_row)

        zone_row = [row["sim_id"], 10, "CA", ""]
        zone_rows.append(zone_row)

    for i, row in RPs.iterrows():
        zone_row = [row["sim_id"], 5, "RA", ""]
        zone_rows.append(zone_row)

        zone_row = [row["sim_id"], 10, "CA", ""]
        zone_rows.append(zone_row)

    for i, row in SPs.iterrows():
        zone_row = [row["sim_id"], 1, "RA", ""]
        zone_rows.append(zone_row)

        zone_row = [row["sim_id"], 1, "CA", ""]
        zone_rows.append(zone_row)

    for i, row in TPs.iterrows():
        zone_row = [row["sim_id"], 1, "RA", ""]
        zone_rows.append(zone_row)

        zone_row = [row["sim_id"], 1, "CA", ""]
        zone_rows.append(zone_row)

    for i, row in DCPs.iterrows():
        zone_row = [row["sim_id"], 1, "RA", ""]
        zone_rows.append(zone_row)

        zone_row = [row["sim_id"], 1, "CA", ""]
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
