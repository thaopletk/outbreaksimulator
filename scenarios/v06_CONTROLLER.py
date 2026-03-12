import v06_functions
import os

# v06_functions.setup_to_outbreak_detection(state="NSW", testing=False, create_download_folder=False)


v06_functions.run_actions_excel(
    state="NSW",
    previous_unique_output="03_outbreak_detection",
    actions_filename_excel="new_actions_1.xlsx",
    days_to_run_for=1,
    unique_output="04_actions_1",
    output_suffix="_02",
    create_download_folder=False,
)

v06_functions.run_actions_excel_shapefile(
    state="NSW",
    previous_unique_output="03_outbreak_detection",
    actions_filename_excel="new_actions_1.xlsx",
    shapefile_path=os.path.join("HPAIExerciseZones", "HPAIExerciseZone.shp"),
    days_to_run_for=1,
    unique_output="04_actions_1_with_shapefile",
    output_suffix="_02",
    create_download_folder=False,
)
