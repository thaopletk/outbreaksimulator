"""Aim: script that automatically generates job files (csvs), but on a more short-term one-day-at-a-time basis"""

import pandas as pd
import os
import numpy as np


def generate_jobs(folder_path, approx_data_csv, scheduled_date, max_resource_units=100):
    approx_data = pd.read_csv(os.path.join(folder_path, approx_data_csv))

    resource_cost = {
        "ClinicalObservation": 2,
        "ContactTracing": 1,
        "LabTesting": 2,
        "Cull": 4,
        "Phone Surveillance": 1,
        "Field Surveillance": 2,
        "Self-reporting Surveillance": 1,
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
        "Self-reporting Surveillance": 0,
        "Population-level Surveillance": 0,
        "Wild Animal Surveillance": 0,
        "Environmental Surveillance": 0,
        "Missing Properties Survey": 0,
    }

    resources_used = 0

    # jobs
    jobs_rows = [["ID", "date_scheduled", "action", "specific_action", "detection_prob", "num", "Free text notes"]]
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

    SPs = approx_data[approx_data["status"] == "SP"]
    SPs = SPs.sort_values("case_id")
    for i, row in SPs.iterrows():
        if row["last_surveillance_date"] == "NA" and row["self_report_date"] + min_delays["ClinicalObservation"] <= scheduled_date:
            job_row = [row["sim_id"], scheduled_date, "ClinicalObservation", "", "", "", "SP"]
            if resources_used < max_resource_units:
                jobs_rows.append(job_row)
                resources_used += resource_cost["ClinicalObservation"]
        else:
            if row["last_PCR_date"] == "NA":
                pass

    # zone jobs

    # zones
