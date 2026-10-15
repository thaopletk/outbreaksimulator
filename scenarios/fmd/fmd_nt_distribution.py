# looking to compare and run multiple runs and compare distributions
import FMD_functions
import datetime
import pandas as pd
import os

state = "NT"
main_folder_name = "NT_test"
start_year = 2026
start_month = 7
start_day = 1
wind_radius = 20
start_date = datetime.datetime(year=start_year, month=start_month, day=start_day)

num_runs = 2

header = ["run_id", "strategy", "total_IPs", "confirmed_IPs"]

data_rows = []

for strategy in ["large_CA", "small_CA"]:
    for run_i in range(num_runs):

        total_infected_properties_with_infected_animals, total_confirmed_IPs = FMD_functions.run_auto_strategies(
            main_folder_name=main_folder_name,
            state=state,
            previous_unique_output="05_national_standstill",
            previous_output_suffix_int=5,
            total_days_to_run_for=4,
            create_download_folder=False,
            download_parent_folder=None,
            download_folder_name=None,
            strategy=strategy,
            shapefile_path=None,
            start_date=start_date,
            random_seed=run_i,
            np_random_seed=run_i,
            EPS_factor=10,
            save_output_data=False,
        )

        row = [run_i, strategy, total_infected_properties_with_infected_animals, total_confirmed_IPs]

        data_rows.append(row)

data_df = pd.DataFrame(data_rows, columns=header)

data_df.to_csv(os.path.join(os.path.dirname(__file__), main_folder_name, "06_large_vs_small_CAs.csv"), index=False)
