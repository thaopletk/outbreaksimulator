import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),".."))

import datetime
import json
import pickle


import simulator.simulator as simulator


# FMD SEI parameters taken from Bradhurst et al., 2015 for "intensive beef" parameters
# beta, latent_period, size

xrange = [150,152]
yrange = [-30.9, -29]

set_up_params = {'n': 100, # total number of properties to include
    'r': 25, # note that this should be in KILOMETERS, the maximum wind dispersal distance
    'prob_report': 0.5,
    'prob_vaccinate':0.5,
    'size': 280, # number of animals on each property
    'clinical_reporting_threshold': 0.05,
    'policy_start': 8,
    'policy_r': 25,
    'xrange':xrange,
    'yrange':yrange,
    'initial_vaccination' : 0.1, # allow the possibility of having some initial vaccination
    'movement_frequency': 3, # days
    'movement_probability': 0,
    'movement_prop_animals': 0.2

}

params_FMD_like = { # parameters provided by Isobel based on FMD
    'latent_period': 2,
    'vax_modifier': 0.4,
    'infectious_period': 1,
    'pre-clinical_period': 1,
    'beta_wind': 0.05*2, # force of infection for wind dispersal
    'beta_animal': 2, # force of infection for animal-animal contact
}



# first, fix the spatial set up

folder_path_main = os.path.join(os.path.dirname(__file__),"outputs","spatial_small")
if not os.path.exists(folder_path_main ):
    os.makedirs(folder_path_main )

property_setup_info = simulator.property_setup(set_up_params,folder_path_main, xrange,yrange)

file = os.path.join(folder_path_main,"set_up_params.json")
with open(file, 'w') as f: 
    json.dump(set_up_params, f)


# # then, run for the different parameter sets (for now, FMD and LSD, as examples)

# for disease,disease_params in [["FMD_like",params_FMD_like]]:

#     # read in the property set up information (cleanly)
#     with open(os.path.join(folder_path_main,"properties_initialised"), 'rb') as file:
#         property_setup_info = pickle.load(file)
    

#     params = {**set_up_params, **disease_params }

#     plotting = 1
#     # unique_output = datetime.datetime.now().strftime("%Y-%m-%d %H.%M.%S")
#     unique_output = f'{disease}_{datetime.datetime.now().strftime("%Y-%m-%d %H.%M.%S")}'
#     # make a new folder
#     folder_path = os.path.join(folder_path_main, unique_output)
#     if not os.path.exists(folder_path ):
#         os.makedirs(folder_path )

#     file = os.path.join(folder_path,"params.json")
#     with open(file, 'w') as f: 
#         json.dump(params, f)

#     total_culled, total_vaccinated = simulator.modified_FMD_ABM(params, plotting,folder_path,property_setup_info, xrange,yrange,unique_output)
#     print(total_culled, total_vaccinated)
