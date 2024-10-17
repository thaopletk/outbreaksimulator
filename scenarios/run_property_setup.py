
# to be possibly converted into a test

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),".."))

import datetime
import json
import pickle

import simulator.simulator as simulator


xrange = [150,151]
yrange = [-30, -29]

set_up_params = {'n': 10, # total number of properties to include
    'r': 25, # note that this should be in KILOMETERS, the maximum wind dispersal distance
    'xrange':xrange,
    'yrange':yrange,
    'average_property_ha': 500

}


folder_path_main = os.path.join(os.path.dirname(__file__),"outputs","temp")
if not os.path.exists(folder_path_main ):
    os.makedirs(folder_path_main )

simulator.property_setup(folder_path_main,set_up_params['n'], set_up_params['r'], set_up_params['average_property_ha'], set_up_params['xrange'],set_up_params['yrange'])




