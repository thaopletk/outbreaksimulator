import v06_functions
import os

# v06_functions.setup_to_outbreak_detection(state="NSW", testing=False, create_download_folder=False)


# v06_functions.run_actions_excel(
#     state="NSW",
#     previous_unique_output="03_outbreak_detection",
#     actions_filename_excel="actions_1.xlsx",
#     days_to_run_for=1,
#     unique_output="04_actions_1",
#     output_suffix="_02",
#     create_download_folder=False,
# )

# v06_functions.run_actions_excel(
#     state="NSW",
#     previous_unique_output="04_actions_1",
#     actions_filename_excel="actions_2.xlsx",
#     days_to_run_for=1,
#     unique_output="04_actions_2",
#     output_suffix="_03",
#     create_download_folder=False,
# )

# v06_functions.run_actions_excel(
#     state="NSW",
#     previous_unique_output="04_actions_2",
#     actions_filename_excel="actions_3.xlsx",
#     days_to_run_for=1,
#     unique_output="04_actions_3",
#     output_suffix="_04",
#     create_download_folder=False,
# )

v06_functions.run_actions_excel(
    state="NSW",
    previous_unique_output="04_actions_3",
    actions_filename_excel="actions_4.xlsx",
    days_to_run_for=1,
    unique_output="04_actions_4",
    output_suffix="_05",
    create_download_folder=False,
)

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
