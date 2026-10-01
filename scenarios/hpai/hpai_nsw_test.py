"""
Test

"""

import os
import sys
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import simulator.auto_job_mode as auto_job_mode
import simulator.v06_functions as v06_functions

v06_functions.setup_to_outbreak_detection(
    state="NSW",
    testing=False,
    create_download_folder=False,
    seed=None,
    main_folder_name="NSW_test",
    base_folder_path=os.path.join(os.path.dirname(__file__)),
)
