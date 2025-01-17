import sys
import os
import json
import pickle

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.output as output
from simulator.premises import convert_time_to_date, convert_date_to_time

folder_path_main = os.path.join(os.path.dirname(__file__), "trial_simex")

properties_filename = os.path.join(folder_path_main, "properties_init")

with open(properties_filename, "rb") as file:
    properties = pickle.load(file)


xlims = [144.5, 151.5]
ylims = [-34.5, -28.5]

output.plot_animal_density(
    properties,
    xlims,
    ylims,
    folder_path_main,
)
