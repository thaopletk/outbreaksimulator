import v06_functions
import os

# v06_functions.setup_to_outbreak_detection(state="QLD-provided", burn_in_movement=7, testing=False, create_download_folder=False)

# v06_functions.run_auto_actions(
#     state="QLD-provided",
#     previous_unique_output="03_outbreak_detection",
#     previous_output_suffix_int=1,
#     total_days_to_run_for=10,
#     start_action_number_int=1,
#     unique_output_starting_int=4,
#     create_download_folder=False,
#     max_resource_units=100,
# )


# action_name = "actions_1"
# v06_functions.run_actions_excel(
#     state="QLD-provided",
#     previous_unique_output="03_outbreak_detection",
#     actions_filename_excel= f"{action_name}.xlsx",
#     days_to_run_for=1,
#     unique_output=f"HASTE_QLD_{action_name}",
#     output_suffix="_02",
#     create_download_folder=True,
#     download_folder_name=f"{action_name}_outputs",
# )

# action_name = "actions_2"
# v06_functions.run_actions_excel(
#     state="QLD-provided",
#     previous_unique_output="HASTE_QLD_actions_1",
#     actions_filename_excel= f"{action_name}.xlsx",
#     days_to_run_for=1,
#     unique_output=f"HASTE_QLD_{action_name}",
#     output_suffix="_03",
#     create_download_folder=True,
#     download_folder_name=f"{action_name}_outputs",
# )

# action_name = "actions_3"
# v06_functions.run_actions_excel(
#     state="QLD-provided",
#     previous_unique_output="HASTE_QLD_actions_2",
#     actions_filename_excel= f"{action_name}.xlsx",
#     days_to_run_for=1,
#     unique_output=f"HASTE_QLD_{action_name}",
#     output_suffix="_04",
#     create_download_folder=True,
#     download_folder_name=f"{action_name}_outputs",
# )

# action_name = "actions_4"
# v06_functions.run_actions_excel(
#     state="QLD-provided",
#     previous_unique_output="HASTE_QLD_actions_3",
#     actions_filename_excel= f"{action_name}.xlsx",
#     days_to_run_for=1,
#     unique_output=f"HASTE_QLD_{action_name}",
#     output_suffix="_05",
#     create_download_folder=True,
#     download_folder_name=f"{action_name}_outputs",
# )


# v06_functions.run_status_update_only_excel_shapefile(
#     state="QLD-provided",
#     previous_unique_output="HASTE_QLD_actions_4",
#     actions_filename_excel=None,
#     shapefile_path=os.path.join("QLD_CA_RA", "Layer 1", "Layer 1-polygons.shp"),
#     unique_output="HASTE_QLD_actions_4_updated",
#     output_suffix="_05_updated",
#     create_download_folder=False,
#     download_parent_folder=None,
#     download_folder_name=None,
# )


# action_name = "actions_5"
# v06_functions.run_actions_excel_shapefile(
#     state="QLD-provided",
#     previous_unique_output="HASTE_QLD_actions_4_updated",
#     actions_filename_excel=f"{action_name}.xlsx",
#     shapefile_path=os.path.join("QLD_CA_RA", "Layer 1", "Layer 1-polygons.shp"),
#     days_to_run_for=7,
#     unique_output=f"HASTE_QLD_{action_name}",
#     output_suffix="_06",
#     create_download_folder=True,
#     download_folder_name=f"{action_name}_outputs",
# )


# v06_functions.run_auto_actions(
#     state="QLD-provided",
#     previous_unique_output="HASTE_QLD_actions_5",
#     previous_output_suffix_int=6,
#     total_days_to_run_for=28,
#     start_action_number_int=6,
#     unique_output_starting_int=4,
#     create_download_folder=False,
#     strategy = "normal_zones",
#     shapefile_path=os.path.join("QLD_CA_RA", "Layer 1", "Layer 1-polygons.shp"),
# )

# v06_functions.run_auto_actions(
#     state="QLD-provided",
#     previous_unique_output="HASTE_QLD_actions_5",
#     previous_output_suffix_int=6,
#     total_days_to_run_for=28,
#     start_action_number_int=6,
#     unique_output_starting_int=4,
#     create_download_folder=False,
#     strategy = "small_zones"
# )


# action_name = "actions_6"
# v06_functions.run_actions_excel_shapefile(
#     state="QLD-provided",
#     previous_unique_output="HASTE_QLD_actions_5",
#     actions_filename_excel=f"{action_name}.xlsx",
#     shapefile_path=os.path.join("Day11", "Layer 14", "Layer 14-polygons.shp"),
#     days_to_run_for=7,
#     unique_output=f"HASTE_QLD_{action_name}",
#     output_suffix="_07",
#     create_download_folder=True,
#     download_folder_name=f"{action_name}_outputs",
# )

action_name = "actions_6_all_depop"
v06_functions.run_actions_excel_shapefile(
    state="QLD-provided",
    previous_unique_output="HASTE_QLD_actions_5",
    actions_filename_excel=f"{action_name}.xlsx",
    shapefile_path=os.path.join("Day11", "Layer 14", "Layer 14-polygons.shp"),
    days_to_run_for=7,
    unique_output=f"HASTE_QLD_{action_name}",
    output_suffix="_07",
    create_download_folder=True,
    download_folder_name=f"{action_name}_outputs",
)
