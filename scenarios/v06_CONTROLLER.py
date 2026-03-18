import v06_functions
import os

# v06_functions.setup_to_outbreak_detection(state="NSW", testing=False, create_download_folder=False)

# shared_folder = "C:\\Users\\thaophuongl\\OneDrive - The University of Melbourne\\01_ARDC-HASTE\\Work Package 5\\WP5_TRIAL"

# action_name = "actions_1"
# v06_functions.run_actions_excel(
#     state="NSW",
#     previous_unique_output="03_outbreak_detection",
#     actions_filename_excel=os.path.join(shared_folder, f"{action_name}.xlsx"),
#     days_to_run_for=1,
#     unique_output=f"HASTE_{action_name}",
#     output_suffix="_02",
#     create_download_folder=True,
#     download_parent_folder=shared_folder,
#     download_folder_name=f"{action_name}_outputs",
# )

# action_name = "actions_2"
# v06_functions.run_actions_excel(
#     state="NSW",
#     previous_unique_output="HASTE_actions_1",
#     actions_filename_excel=os.path.join(shared_folder, f"{action_name}.xlsx"),
#     days_to_run_for=1,
#     unique_output=f"HASTE_{action_name}",
#     output_suffix="_03",
#     create_download_folder=True,
#     download_parent_folder=shared_folder,
#     download_folder_name=f"{action_name}_outputs",
# )

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


# v06_functions.run_auto_actions(
#     state="NSW",
#     previous_unique_output="04_actions_1",
#     previous_output_suffix_int=2,
#     total_days_to_run_for=7,
#     start_action_number_int=2,
#     unique_output_starting_int=5,
#     create_download_folder=False,
#     max_resource_units=100,
# )


# v06_functions.setup_to_outbreak_detection(state="QLD", burn_in_movement = 1, testing=False, create_download_folder=False)

v06_functions.run_auto_actions(
    state="QLD",
    previous_unique_output="03_outbreak_detection",
    previous_output_suffix_int=1,
    total_days_to_run_for=7,
    start_action_number_int=1,
    unique_output_starting_int=4,
    create_download_folder=False,
    max_resource_units=100,
)
