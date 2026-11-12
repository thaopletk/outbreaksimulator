# looking to compare and run multiple runs and compare distributions
import FMD_functions
import datetime
import pandas as pd
import os
import sys

state = "NT"
main_folder_name = "NT_test"
start_year = 2026
start_month = 7
start_day = 1
wind_radius = 20
start_date = datetime.datetime(year=start_year, month=start_month, day=start_day)

num_runs = 100

header = [
    "run_id",
    "strategy",
    "infected_properties_with_infected_animals",
    "confirmed_IPs",
    "undetected_properties_with_infected_animals",
    "infected_properties_with_infected_animals_or_depop",
    "labtests",
]

data_rows = []

previous_strategy_folder = sys.argv[1]  # e.g. "06_large_CA"
strategy = sys.argv[2]  # e.g. "large_CA_cull_focus"
for run_i in range(num_runs):
    (
        total_infected_properties_with_infected_animals,
        total_confirmed_IPs,
        total_undetected_properties_with_infected_animals,
        total_infected_properties_with_infected_animals_or_depop,
        total_lab_tests_over_interval,
    ) = FMD_functions.run_auto_strategies(
        main_folder_name=main_folder_name,
        state=state,
        previous_unique_output=previous_strategy_folder,
        previous_output_suffix_int=6,
        total_days_to_run_for=28 - 7,
        create_download_folder=False,
        download_parent_folder=None,
        download_folder_name=None,
        strategy=strategy,
        shapefile_path=None,
        start_date=start_date,
        random_seed=run_i,
        np_random_seed=run_i,
        EPS_factor=20,
        save_output_data=False,
    )

    row = [
        run_i,
        strategy,
        total_infected_properties_with_infected_animals,
        total_confirmed_IPs,
        total_undetected_properties_with_infected_animals,
        total_infected_properties_with_infected_animals_or_depop,
        total_lab_tests_over_interval,
    ]

    data_rows.append(row)

data_df = pd.DataFrame(data_rows, columns=header)

data_df.to_csv(os.path.join(os.path.dirname(__file__), main_folder_name, f"07_{strategy}.csv"), index=False)
