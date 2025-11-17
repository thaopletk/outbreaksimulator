import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.fixed_spatial_setup as fixed_spatial_setup

xrange = [136, 155]
yrange = [-40, -25]

folder_path_main = os.path.join(os.path.dirname(__file__), "v06")
# make main folder if it doesn't exist
if not os.path.exists(folder_path_main):
    os.makedirs(folder_path_main)

fixed_spatial_setup.fixed_spatial_setup(xrange, yrange, folder_path_main, disease="HPAI", AADIS=False)
