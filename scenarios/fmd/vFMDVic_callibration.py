import vFMDVic
import os
import sys
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import shutil
import time
import json

total_infected_aim = 18
state = "VIC"
folder_path_main = os.path.join(os.path.dirname(__file__), f"vFMD{state}")

folder_path_main_ABC_params = os.path.join(folder_path_main, "ABC_params")
if not os.path.exists(folder_path_main_ABC_params):
    os.makedirs(folder_path_main_ABC_params)

# read in sim _id number
sim_id = int(sys.argv[1])

# based on the sim_id number, pick a parameter set from a pre-constructed list
grid_size = 5
# animal_grid = 3
parameters_list = []
for beta_wind in [0.00042, 0.00045, 0.0005, 0.00055]:  # np.linspace(0.00038, 0.00052, grid_size):
    # beta_animal = 3
    for beta_animal in [1.85, 1.9, 1.95, 2.00, 2.05]:  # np.linspace(1.7, 2.1, 10):
        pig_multiplier = (2.1 / 1.6 + 2.1 / 0.7) / 2
        sheep_multiplier = (0.5 / 1.6 + 0.5 / 0.7) / 2
        parameters_list.append([beta_wind, beta_animal, pig_multiplier, sheep_multiplier])

        # for pig_multiplier in np.linspace(2.1 / 1.6, 2.1 / 0.7, grid_size):
        #     for sheep_multiplier in np.linspace(0.5 / 1.6, 0.5 / 0.7, grid_size):
        #         parameters_list.append([beta_wind, beta_animal, pig_multiplier, sheep_multiplier])

beta_wind, beta_animal, pig_multiplier, sheep_multiplier = parameters_list[sim_id]

disease_parameters = {
    "cattle": {
        "beta_wind": beta_wind,
        "beta_animal": beta_animal,
        "latent_period": 2,
        "infectious_period": 10,
        "preclinical_period": 3,
        "pre-clinical_period": 3,
    },
    "pigs": {
        "beta_wind": beta_wind * pig_multiplier,
        "beta_animal": beta_animal * pig_multiplier,
        "latent_period": 1,
        "infectious_period": 10,
        "preclinical_period": 3,
        "pre-clinical_period": 3,
    },
    "sheep": {
        "beta_wind": beta_wind * sheep_multiplier,
        "beta_animal": beta_animal * sheep_multiplier,
        "latent_period": 5,
        "infectious_period": 10,
        "preclinical_period": 3,
        "pre-clinical_period": 3,
    },
}

print(disease_parameters)

# run
start_time = time.time()


(
    total_infected,
    current_time,
    total_infected_properties_with_infected_animals,
    total_infected_animals,
) = vFMDVic.run_seeding_undetected_spread(
    state="VIC",
    burn_in_time=0,
    create_download_folder=False,
    download_parent_folder=None,
    wind_radius=20,
    ABC_mode=True,
    disease_parameters=disease_parameters,
    max_infected_premises=total_infected_aim + 1,
    target_infected_properties=total_infected_aim,
)

# check if it was good. if so, save the parameter set (with sim id)
if (
    current_time == 28
    and total_infected_properties_with_infected_animals >= total_infected_aim - 1
    and total_infected_properties_with_infected_animals <= total_infected_aim + 1
):
    with open(os.path.join(folder_path_main_ABC_params, f"disease_parameters_{sim_id}.json"), "w") as f:
        json.dump(disease_parameters, f)

else:
    print(f"total infected: {total_infected}, after {current_time} days")


end_time = time.time()
execution_time = end_time - start_time
print(f"Execution time of an ABC run: {execution_time/60} minutes")
