import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import simulator.fixed_spatial_setup as fixed_spatial_setup


fixed_spatial_setup.fixed_spatial_setup(disease="HPAI", AADIS=False)
