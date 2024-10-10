import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),".."))
sys.path.append(os.path.join(os.path.dirname(__file__),"..","FMD_modelling"))
from ipynb.fs.defs.fmd_modelling import calculate_FOI # https://github.com/ipython/ipynb

# def calculate_FOI(properties, premise_index, params) 
def calculate_force_of_infection(properties, premise_index, params):
    return calculate_FOI(properties, premise_index, params) 

# does not use or require property area / radius
def calculate_FOI_point_properties(premise, params, infected_props):
    # FOI = beta * [(vax - 1)*vax_status + 1] * x
    x = 0

    vax_status = (params['vax_modifier'] - 1)*premise.vaccination_status + 1

    # farm = [index, dist]
    for farm in premise.neighbourhood:
        index = farm[0]
        dist = farm[1]
        x += (1 - (dist/params['r']))*infected_props[index]

    FOI = (params['beta_between'] * x + params['beta_within']*premise.prop_infectious)*vax_status

    return FOI 