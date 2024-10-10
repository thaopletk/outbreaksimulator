import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),".."))

import datetime
import json


import simulator.simulator as simulator


# SEI parameters taken from Bradhurst et al., 2015 for "intensive beef" parameters
# beta, latent_period, size

xrange = [148,152]
yrange = [-31.9, -29]

params = {
    'n': 20, #1600, # total number of properties to include
    'r': 20, # note that this should be in KILOMETERS, the distance in which properties are 'neighbours'
    'prob_report': 0.5,
    'prob_vaccinate':0.5,
    'size': 280,
    # size of properties
    'latent_period': 2,
    'vax_modifier': 0.4,
    'infectious_period': 1,
    'pre-clinical_period': 1,
    'beta_background': 0.05*2,
    'beta_animal-animal': 2,
    'clinical_reporting_threshold': 0.05,
    # 'beta_between': 0.25*2,
    # 'beta_within': 2,
    'policy_start': 8,
    'policy_r': 25,
    'xrange':xrange,
    'yrange':yrange,
    'initial_vaccination' : 0.1
}

# create video of single simulation 
plotting = 1
unique_output = datetime.datetime.now().strftime("%Y-%m-%d %H.%M.%S")
# make a new folder
folder_path = os.path.join(os.path.dirname(__file__),"outputs",unique_output)
if not os.path.exists(folder_path ):
  os.makedirs(folder_path )

file = os.path.join(folder_path,"params.json")
with open(file, 'w') as f: 
    json.dump(params, f)

total_culled, total_vaccinated = simulator.modified_FMD_ABM(params, plotting,folder_path,xrange,yrange,unique_output)
print(total_culled, total_vaccinated)
