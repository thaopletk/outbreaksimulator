import vFMDVic
import os
import sys
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


vFMDVic.setup_to_outbreak_detection(state="VIC", burn_in_time=1, create_download_folder=False, download_parent_folder=None, wind_radius=20)

# notes: I could split the undetected spread part out -- so I can conduct ABC on that part
# and I probably really should remove the burn in movement phase
