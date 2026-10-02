import os
import sys
import pandas as pd
import json
import FMD_functions

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

state = "VIC"
folder_path_main = os.path.join(os.path.dirname(__file__), f"{state}_test")

with open(os.path.join(folder_path_main, "disease_parameters_9.json"), "r") as file:
    disease_parameters = json.load(file)

total_infected, undetected_spread_properties_filename, undetected_spread_diseaseoutbreak_filename, undetected_spread_trucks_filename = (
    FMD_functions.run_seeding_undetected_spread(
        main_folder_name=f"{state}_test",
        state="VIC",
        burn_in_time=0,
        create_download_folder=False,
        download_parent_folder=None,
        wind_radius=20,
        disease_parameters=disease_parameters,
    )
)

FMD_functions.trigger_first_report(
    undetected_spread_properties_filename,
    undetected_spread_diseaseoutbreak_filename,
    undetected_spread_trucks_filename,
    main_folder_name="VIC_test",
    state="VIC",
    create_download_folder=False,
    download_parent_folder=None,
)


FMD_functions.run_auto_strategies(
    main_folder_name="VIC_test",
    state="VIC",
    previous_unique_output="03_outbreak_detection",
    previous_output_suffix_int=3,
    total_days_to_run_for=1,
    create_download_folder=False,
    download_parent_folder=None,
    download_folder_name=None,
    strategy="initial_investigation",
    shapefile_path=None,
)

FMD_functions.run_auto_strategies(
    main_folder_name="VIC_test",
    state="VIC",
    previous_unique_output="04_initial_investigation",
    previous_output_suffix_int=4,
    total_days_to_run_for=3,
    create_download_folder=False,
    download_parent_folder=None,
    download_folder_name=None,
    strategy="national_standstill",
    shapefile_path=None,
)


# FMD_vic_functions.run_auto_strategies(
#     main_folder_name="VIC_test",
#     state="VIC",
#     previous_unique_output="05_national_standstill",
#     previous_output_suffix_int=5,
#     total_days_to_run_for=4,
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
#     strategy="large_CA",
#     shapefile_path=None,
# )

# FMD_vic_functions.run_auto_strategies(
#     main_folder_name="VIC_test",
#     state="VIC",
#     previous_unique_output="05_national_standstill",
#     previous_output_suffix_int=5,
#     total_days_to_run_for=4,
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
#     strategy="small_CA",
#     shapefile_path=None,
# )


# FMD_vic_functions.run_auto_strategies(
#     main_folder_name="VIC_test",
#     state="VIC",
#     previous_unique_output="06_large_CA",
#     previous_output_suffix_int=6,
#     total_days_to_run_for=28 - 7,  # 7 to 28
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
#     strategy="large_CA_cull_focus",
#     shapefile_path=None,
# )

# FMD_vic_functions.run_auto_strategies(
#     main_folder_name="VIC_test",
#     state="VIC",
#     previous_unique_output="06_small_CA",
#     previous_output_suffix_int=6,
#     total_days_to_run_for=28 - 7,  # 7 to 28
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
#     strategy="small_CA_cull_focus",
#     shapefile_path=None,
# )

# FMD_vic_functions.run_auto_strategies(
#     main_folder_name="VIC_test",
#     state="VIC",
#     previous_unique_output="06_large_CA",
#     previous_output_suffix_int=6,
#     total_days_to_run_for=28 - 7,  # 7 to 28
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
#     strategy="large_CA_surveillance_focus",
#     shapefile_path=None,
# )


# FMD_vic_functions.run_auto_strategies(
#     main_folder_name="VIC_test",
#     state="VIC",
#     previous_unique_output="06_small_CA",
#     previous_output_suffix_int=6,
#     total_days_to_run_for=28 - 7,  # 7 to 28
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
#     strategy="small_CA_surveillance_focus",
#     shapefile_path=None,
# )

# FMD_vic_functions.run_auto_strategies(
#     main_folder_name="VIC_test",
#     state="VIC",
#     previous_unique_output="07_large_CA_cull_focus",
#     previous_output_suffix_int=7,
#     total_days_to_run_for=56,  # 8 weeks
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
#     strategy="large_CA_cull_focus_vaccination",
#     shapefile_path=None,
# )

# effectively no vaccination
# FMD_vic_functions.run_auto_strategies(
#     main_folder_name="VIC_test",
#     state="VIC",
#     previous_unique_output="07_large_CA_cull_focus",
#     previous_output_suffix_int=7,
#     total_days_to_run_for=56,
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
#     strategy="large_CA_cull_focus",
#     shapefile_path=None,
# )
