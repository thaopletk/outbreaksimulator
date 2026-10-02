import FMD_functions

state = "NT"
main_folder_name = "NT_test"

FMD_functions.setup(main_folder_name=main_folder_name, state=state, wind_radius=20, testing=False, max_movement_km=500)
# not many properties in NT AADIS data, so don't need "testing = True"
# increased max movement because locations are really distant from each other

total_infected, undetected_spread_properties_filename, undetected_spread_diseaseoutbreak_filename, undetected_spread_trucks_filename = (
    FMD_functions.run_seeding_undetected_spread(
        main_folder_name=main_folder_name,
        state=state,
        burn_in_time=0,
        create_download_folder=False,
        download_parent_folder=None,
        wind_radius=20,
    )
)


FMD_functions.trigger_first_report(
    undetected_spread_properties_filename,
    undetected_spread_diseaseoutbreak_filename,
    undetected_spread_trucks_filename,
    main_folder_name=main_folder_name,
    state=state,
    create_download_folder=False,
    download_parent_folder=None,
)


FMD_functions.run_auto_strategies(
    main_folder_name=main_folder_name,
    state=state,
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
    main_folder_name=main_folder_name,
    state=state,
    previous_unique_output="04_initial_investigation",
    previous_output_suffix_int=4,
    total_days_to_run_for=3,
    create_download_folder=False,
    download_parent_folder=None,
    download_folder_name=None,
    strategy="national_standstill",
    shapefile_path=None,
)


FMD_functions.run_auto_strategies(
    main_folder_name=main_folder_name,
    state=state,
    previous_unique_output="05_national_standstill",
    previous_output_suffix_int=5,
    total_days_to_run_for=4,
    create_download_folder=False,
    download_parent_folder=None,
    download_folder_name=None,
    strategy="large_CA",
    shapefile_path=None,
)
