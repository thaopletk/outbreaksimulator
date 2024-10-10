import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),".."))

import simulator.spatial_setup as spatial_setup

def test_assign_coordinates():
    num = 5
    assert len(spatial_setup.assign_coordinates(num))==num