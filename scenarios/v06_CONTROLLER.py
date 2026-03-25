import v06_functions
import os
import sys
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.auto_job_mode as auto_job_mode

# v06_functions.setup_to_outbreak_detection(state="NSW", testing=False, create_download_folder=False)

shared_folder = "C:\\Users\\thaophuongl\\OneDrive - The University of Melbourne\\01_ARDC-HASTE\\WP5_NSW_Workshop"

# action_name = "actions_1"
# v06_functions.run_actions_excel(
#     state="NSW",
#     previous_unique_output="03_outbreak_detection",
#     actions_filename_excel=os.path.join(shared_folder, f"{action_name}.xlsx"),
#     days_to_run_for=1,
#     unique_output=f"HASTE_NSW_{action_name}",
#     output_suffix="_02",
#     create_download_folder=True,
#     download_parent_folder=shared_folder,
#     download_folder_name=f"{action_name}_outputs",
# )

# v06_functions.run_status_update_only_excel_shapefile(
#     state="NSW",
#     previous_unique_output="HASTE_NSW_actions_1",
#     actions_filename_excel=None,
#     shapefile_path=os.path.join(shared_folder, "actions_1IP_zones", "1IP_Zones.shp"),
#     unique_output="HASTE_NSW_actions_1_updated",
#     output_suffix="_02_updated",
#     create_download_folder=True,
#     download_parent_folder=shared_folder,
#     download_folder_name="actions_1_updated_outputs",
# )


# auto_job_mode.generate_ARP_POR_jobs_only(
#     os.path.join(shared_folder, "actions_1_updated_outputs"),
#     "approx_known_data_02_updated.csv",
#     "21/01/2026",
#     "post_actions_1_updated_ARP_POR_jobs",
# )

# action_name = "actions_1IP"
# v06_functions.run_actions_excel_shapefile(
#     state="NSW",
#     previous_unique_output="HASTE_NSW_actions_1",
#     actions_filename_excel=os.path.join(shared_folder, f"{action_name}.xlsx"),
#     shapefile_path=os.path.join(shared_folder, "actions_1IP_zones", "1IP_Zones.shp"),
#     days_to_run_for=2,
#     unique_output=f"HASTE_NSW_{action_name}_2days", # intention is to run something with more days
#     output_suffix="_03",
#     create_download_folder=True,
#     download_parent_folder=shared_folder,
#     download_folder_name=f"{action_name}_outputs_2days",
# )

# action_name = "action_2_new"
# v06_functions.run_actions_excel_shapefile(
#     state="NSW",
#     previous_unique_output="HASTE_NSW_actions_1IP_2days",
#     actions_filename_excel=os.path.join(shared_folder, f"{action_name}.xlsx"),
#     shapefile_path=os.path.join(shared_folder, "Day4", "Day4_1510.shp"),
#     days_to_run_for=2,
#     unique_output=f"HASTE_NSW_{action_name}", # intention is to run something with more days
#     output_suffix="_04",
#     create_download_folder=True,
#     download_parent_folder=shared_folder,
#     download_folder_name=f"{action_name}_outputs",
# )

action_name = "actions_1 Fast DDD"
v06_functions.run_actions_excel_shapefile(
    state="NSW",
    previous_unique_output="HASTE_NSW_action_2_new",
    actions_filename_excel=os.path.join(shared_folder, f"{action_name}.xlsx"),
    shapefile_path=os.path.join(shared_folder, "Day4", "Day4_1510.shp"),  # TODO -
    days_to_run_for=7,  # TODO
    unique_output=f"HASTE_NSW_{action_name}",  # intention is to run something with more days
    output_suffix="_05",
    create_download_folder=True,
    download_parent_folder=shared_folder,
    download_folder_name=f"{action_name}_outputs",
)

action_name = "actions_1 Slow DDD"
v06_functions.run_actions_excel_shapefile(
    state="NSW",
    previous_unique_output="HASTE_NSW_action_2_new",
    actions_filename_excel=os.path.join(shared_folder, f"{action_name}.xlsx"),
    shapefile_path=os.path.join(shared_folder, "Day4", "Day4_1510.shp"),  # TODO -
    days_to_run_for=7,  # TODO
    unique_output=f"HASTE_NSW_{action_name}",  # intention is to run something with more days
    output_suffix="_05",
    create_download_folder=True,
    download_parent_folder=shared_folder,
    download_folder_name=f"{action_name}_outputs",
)


# v06_functions.run_auto_actions(
#     state="NSW",
#     previous_unique_output="HASTE_NSW_actions_1IP_2days",
#     previous_output_suffix_int=3,
#     total_days_to_run_for=4,
#     start_action_number_int=3,
#     unique_output_starting_int=4,
#     create_download_folder=True,
#     download_parent_folder=shared_folder,
#     max_resource_units=100,
#     strategy = "default",
# )

# # Compare DataFrames
# df1 = pd.read_csv('C:\\Users\\thaophuongl\\Documents\\HASTE_CODE\\OutbreakSimulator\\scenarios\\v06_NSW\\VERSION_BEFORE_CASE_CREATION_DATE\\07_actions_6_default\\approx_known_data_07.csv')
# df2 = pd.read_csv('C:\\Users\\thaophuongl\\Documents\\HASTE_CODE\\OutbreakSimulator\\scenarios\\v06_NSW\\07_actions_6_default\\approx_known_data_07.csv')
# del df2['case_created_date']

# res = df1.compare(df2)
# print(res)

# df1 = pd.read_csv('C:\\Users\\thaophuongl\\Documents\\HASTE_CODE\\OutbreakSimulator\\scenarios\\v06_NSW\\VERSION_BEFORE_CASE_CREATION_DATE\\07_actions_6_default\\data_underlying_07_actions_6_default.csv')
# df2 = pd.read_csv('C:\\Users\\thaophuongl\\Documents\\HASTE_CODE\\OutbreakSimulator\\scenarios\\v06_NSW\\07_actions_6_default\\data_underlying_07_actions_6_default.csv')
# res = df1.compare(df2)
# print(res)

# v06_functions.run_auto_actions(
#     state="NSW",
#     previous_unique_output="07_actions_6_default",
#     previous_output_suffix_int=7,
#     total_days_to_run_for=4,
#     start_action_number_int=7,
#     unique_output_starting_int=8,
#     create_download_folder=False,
#     max_resource_units=120,
#     strategy = "faster depop",
# )

# v06_functions.run_auto_actions(
#     state="NSW",
#     previous_unique_output="07_actions_6_default",
#     previous_output_suffix_int=7,
#     total_days_to_run_for=4,
#     start_action_number_int=7,
#     unique_output_starting_int=8,
#     create_download_folder=False,
#     max_resource_units=100,
#     strategy="default",
# )


# df1 = pd.read_csv('C:\\Users\\thaophuongl\\Documents\\HASTE_CODE\\OutbreakSimulator\\scenarios\\v06_NSW\\VERSION_BEFORE_CASE_CREATION_DATE\\HASTE_NSW_actions_1IP_2days\\combined_narrative_03.csv')
# df2 = pd.read_csv('C:\\Users\\thaophuongl\\Documents\\HASTE_CODE\\OutbreakSimulator\\scenarios\\v06_NSW\\HASTE_NSW_actions_1IP_2days\\combined_narrative_03.csv')
# res = df1.compare(df2)
# print(res)


# action_name = "actions_3"
# v06_functions.run_actions_excel(
#     state="NSW",
#     previous_unique_output="HASTE_actions_2",
#     actions_filename_excel=os.path.join(shared_folder, f"{action_name}.xlsx"),
#     days_to_run_for=1,
#     unique_output=f"HASTE_{action_name}",
#     output_suffix="_04",
#     create_download_folder=True,
#     download_parent_folder=shared_folder,
#     download_folder_name=f"{action_name}_outputs",
# )

# action_name = "actions_4"
# v06_functions.run_actions_excel(
#     state="NSW",
#     previous_unique_output="HASTE_actions_3",
#     actions_filename_excel=os.path.join(shared_folder, "{action_name}.xlsx"),
#     days_to_run_for=1,
#     unique_output="HASTE_{action_name}",
#     output_suffix="_05",
#     create_download_folder=True,
#     download_parent_folder=shared_folder,
#     download_folder_name=f"{action_name}_outputs",
# )

# v06_functions.run_actions_excel_shapefile(
#     state="NSW",
#     previous_unique_output="03_outbreak_detection",
#     actions_filename_excel="new_actions_1.xlsx",
#     shapefile_path=os.path.join("HPAIExerciseZones", "HPAIExerciseZone.shp"),
#     days_to_run_for=1,
#     unique_output="04_actions_1_with_shapefile",
#     output_suffix="_02",
#     create_download_folder=False,
# )

# v06_functions.setup_to_outbreak_detection(state="QLD", burn_in_movement=7, testing=False, create_download_folder=False)

# v06_functions.run_auto_actions(
#     state="QLD",
#     previous_unique_output="03_outbreak_detection",
#     previous_output_suffix_int=1,
#     total_days_to_run_for=7,
#     start_action_number_int=1,
#     unique_output_starting_int=4,
#     create_download_folder=False,
#     max_resource_units=100,
# )
