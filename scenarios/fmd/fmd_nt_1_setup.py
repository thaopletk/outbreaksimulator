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
