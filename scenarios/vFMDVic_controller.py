import vFMDVic
import os
import sys
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


# vFMDVic.setup(state="VIC",wind_radius=20)

total_infected, undetected_spread_properties_filename, undetected_spread_diseaseoutbreak_filename, undetected_spread_trucks_filename = (
    vFMDVic.run_seeding_undetected_spread(state="VIC", burn_in_time=0, create_download_folder=False, download_parent_folder=None, wind_radius=20)
)

vFMDVic.trigger_first_report(
    undetected_spread_properties_filename,
    undetected_spread_diseaseoutbreak_filename,
    undetected_spread_trucks_filename,
    state="VIC",
    create_download_folder=False,
    download_parent_folder=None,
)


# notes: I could split the undetected spread part out -- so I can conduct ABC on that part to adjust the parameters to spread more like what I want
