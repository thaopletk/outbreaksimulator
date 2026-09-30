import FMD_functions

state = "NT"

FMD_functions.setup(main_folder_name="NT_test", state=state, wind_radius=20, testing=False)
# not many properties in NT AADIS data, so don't need "testing = True"
