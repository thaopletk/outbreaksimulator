import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),".."))

import datetime
import json
import pickle


import simulator.simulator as simulator


# FMD SEI parameters taken from Bradhurst et al., 2015 for "intensive beef" parameters
# beta, latent_period, size

xrange = [148,152]
yrange = [-31.9, -29]

set_up_params = {'n': 1600, # total number of properties to include
    'r': 20, # note that this should be in KILOMETERS, the distance in which properties are 'neighbours'
    'prob_report': 0.5,
    'prob_vaccinate':0.5,
    'size': 280, # size of properties
    'clinical_reporting_threshold': 0.05,
    'policy_start': 8,
    'policy_r': 25,
    'xrange':xrange,
    'yrange':yrange,
    'initial_vaccination' : 0.1,
}

params_FMD_like = { # parameters provided by Isobel based on FMD
    'latent_period': 2,
    'vax_modifier': 0.4,
    'infectious_period': 1,
    'pre-clinical_period': 1,
    'beta_background': 0.05*2,
    'beta_animal-animal': 2,
}

params_LSD_like = {
    'latent_period': 7.3, # EFSA 2020 table C2
    'vax_modifier': 0.6, # https://link.springer.com/article/10.1007/s11259-022-10037-2#Abs1 but kind of unclear; multiple vaccines on the market
    'infectious_period': 23.1, # EFSA 2020 table C2
    'pre-clinical_period': 16, # 6-26 days according to AUSVET, 28 days according to WOAH 
    'beta_background': 0.5, # NOT PRECISE VALUE - value to be calibrated to achieve a certain spread? (1 km per day?)
    # https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10458895/: "In the presence of an infected cow, the basic reproduction number (R0) of indirect transmission was estimated at 15.7, compared to 0.36 for direct transmission."
    'beta_animal-animal': 0, # technically it's transmitted by vectors, or rather, direct contact doesn't seem to be the main form?
}
# AUSVET: https://animalhealthaustralia.com.au//wp-content/uploads/dlm_uploads/2024/06/AUSVETPLAN-Response-Stategy-Lumpy-skin-disease-Version-5.2.pdf 
# spread 1 km per day - to adjust beta parameters such that this occurs? 
# EFSA 2020 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7448019/ table C2

params_equine_influenza_like = {
    'latent_period': 1.25, # Spence et al 2018, Table 1
    'vax_modifier': None, # Spence et al 2018 has waning immunity... 
    'infectious_period': 5.5, # Spence et al 2018, Table 1
    'pre-clinical_period': None,
    'beta_background': None,  # calibrate to have a 38% attack rate?  - Spence et al 2018
    'beta_animal-animal': None,
}
# Spence et al 2018 https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5914078/ 

params_avian_influenza_like = {
    'latent_period': None,
    'vax_modifier': None,
    'infectious_period': None,
    'pre-clinical_period': None,
    'beta_background': None,
    'beta_animal-animal': None,
}

# first, fix the spatial set up

folder_path_main = os.path.join(os.path.dirname(__file__),"outputs","spatial_v1")
if not os.path.exists(folder_path_main ):
    os.makedirs(folder_path_main )

property_setup_info = simulator.property_setup(set_up_params,folder_path_main, xrange,yrange)

file = os.path.join(folder_path_main,"set_up_params.json")
with open(file, 'w') as f: 
    json.dump(set_up_params, f)


# then, run for the different parameter sets (for now, FMD and LSD, as examples)

for disease,disease_params in [["FMD_like",params_FMD_like], ["LSD_like",params_LSD_like]]:

    # read in the property set up information (cleanly)
    with open(os.path.join(folder_path_main,"properties_initialised"), 'rb') as file:
        property_setup_info = pickle.load(file)
    

    params = {**set_up_params, **disease_params }

    plotting = 1
    # unique_output = datetime.datetime.now().strftime("%Y-%m-%d %H.%M.%S")
    unique_output = f'{disease}_{datetime.datetime.now().strftime("%Y-%m-%d %H.%M.%S")}'
    # make a new folder
    folder_path = os.path.join(folder_path_main, unique_output)
    if not os.path.exists(folder_path ):
        os.makedirs(folder_path )

    file = os.path.join(folder_path,"params.json")
    with open(file, 'w') as f: 
        json.dump(params, f)

    total_culled, total_vaccinated = simulator.modified_FMD_ABM(params, plotting,folder_path,property_setup_info, xrange,yrange,unique_output)
    print(total_culled, total_vaccinated)
