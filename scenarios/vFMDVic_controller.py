import vFMDVic
import os
import sys
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


# vFMDVic.setup(state="VIC", wind_radius=20)

total_infected, undetected_spread_properties_filename, undetected_spread_diseaseoutbreak_filename, undetected_spread_trucks_filename = (
    vFMDVic.run_seeding_undetected_spread(state="VIC", burn_in_time=0, create_download_folder=False, download_parent_folder=None, wind_radius=20)
)

vFMDVic.trigger_first_report(
    undetected_spread_properties_filename,
    undetected_spread_diseaseoutbreak_filename,
    undetected_spread_trucks_filename,
    state="VIC",
    create_download_folder=False,
    download_parent_folder=None,
)


# vFMDVic.run_auto_strategies(
#     state="VIC",
#     previous_unique_output = "03_outbreak_detection",
#     previous_output_suffix_int=3,
#     total_days_to_run_for=3,
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
#     strategy="national_standstill",
#     shapefile_path=None,
# )


# vFMDVic.run_auto_strategies(
#     state="VIC",
#     previous_unique_output = "04_national_standstill",
#     previous_output_suffix_int=4,
#     total_days_to_run_for=4,
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
#     strategy="large_CA",
#     shapefile_path=None,
# )

# vFMDVic.run_auto_strategies(
#     state="VIC",
#     previous_unique_output = "04_national_standstill",
#     previous_output_suffix_int=4,
#     total_days_to_run_for=4,
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
#     strategy="small_CA",
#     shapefile_path=None,
# )


# vFMDVic.run_auto_strategies(
#     state="VIC",
#     previous_unique_output="05_large_CA",
#     previous_output_suffix_int=5,
#     total_days_to_run_for=28 - 7,  # 7 to 28
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
#     strategy="large_CA_cull_focus",
#     shapefile_path=None,
# )

# vFMDVic.run_auto_strategies(
#     state="VIC",
#     previous_unique_output="05_large_CA",
#     previous_output_suffix_int=5,
#     total_days_to_run_for=28 - 7,  # 7 to 28
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
#     strategy="large_CA_surveillance_focus",
#     shapefile_path=None,
# )


# vFMDVic.run_auto_strategies(
#     state="VIC",
#     previous_unique_output="06_large_CA_cull_focus",
#     previous_output_suffix_int=6,
#     total_days_to_run_for=7,
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
#     strategy="large_CA_cull_focus_vaccination",
#     shapefile_path=None,
# )

# effectively no vaccination
# vFMDVic.run_auto_strategies(
#     state="VIC",
#     previous_unique_output="06_large_CA_cull_focus",
#     previous_output_suffix_int=6,
#     total_days_to_run_for=7,
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
#     strategy="large_CA_cull_focus",
#     shapefile_path=None,
# )

# action_name = "actions_1"
# vFMDVic.run_actions_excel(
#     state="VIC",
#     previous_unique_output="03_outbreak_detection",
#     actions_filename_excel=f"{action_name}.xlsx",
#     days_to_run_for=1,
#     unique_output=f"FMD_{action_name}",
#     output_suffix="_02",
# )

# action_name = "actions_2"
# vFMDVic.run_actions_excel(
#     state="VIC",
#     previous_unique_output="FMD_actions_1",
#     actions_filename_excel=f"{action_name}.xlsx",
#     days_to_run_for=1,
#     unique_output=f"FMD_{action_name}",
#     output_suffix="_03",
# )


# vFMDVic.run_auto_actions(
#     state="VIC",
#     previous_unique_output="FMD_actions_2",
#     previous_output_suffix_int=3,
#     total_days_to_run_for=2,
#     start_action_number_int=3,
#     unique_output_starting_int=4,
#     create_download_folder=False,
#     strategy = "national_standstill",
# )


# notes: I could split the undetected spread part out -- so I can conduct ABC on that part to adjust the parameters to spread more like what I want
# notes for next steps:continue following the v0.6 and continue set up of properties.
# then take a closer look at (1) the original FMD parameters to try and match them; and (2) the initial outbreak data to try and fit it; and (3) ABC method to more roughly fit it.


# vFMDVic.ABC(state="VIC", grid_size=3)
