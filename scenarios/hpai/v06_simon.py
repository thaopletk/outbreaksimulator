"""

This code was developed for Simon F.'s use case of the HPAi code to run branching decision outbreak trajectories with different seeds

Usage: call on the cluster with

python3 v06_simon.py [SEED] [RUN_COMPONENT]

where [SEED] is an int
and [RUN_COMPONENT] is one of:
    - "setup"
    - "highDDD_7_21"
    - "lowDDD_7_21"
    - "highDDD_vac"
    - "highDDD_novac"
    - "lowDDD_vac"
    - "lowDDD_novac"

"""

import os
import sys
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import simulator.v06_functions as v06_functions

# property_seed = 10
if sys.argv[1] == "None":
    property_seed = None
else:
    property_seed = int(sys.argv[1])

run_component = sys.argv[2]

if property_seed is None:
    download_folder = os.path.join(os.path.dirname(__file__), f"v06_NSW")
else:
    download_folder = os.path.join(os.path.dirname(__file__), f"v06_NSW_{property_seed}")

#####################################################################
# setup

if run_component == "setup":
    v06_functions.setup_to_outbreak_detection(state="NSW", testing=False, create_download_folder=False, seed=property_seed)

    #####################################################################
    # run first 7 days post detection
    # note: no actually DDD in the first seven days due to DDD delay
    v06_functions.run_auto_strategies(
        state="NSW",
        previous_unique_output="03_outbreak_detection",
        previous_output_suffix_int=3,  # matches the '03' in '03_outbreak_detection'
        total_days_to_run_for=7,
        create_download_folder=True,
        download_folder_name=os.path.join(download_folder, "day_7_high_DDD"),
        strategy="high DDD",
        seed=property_seed,
    )

    # low DDD doesn't do anything in the first 7 days as there aren't many jobs...

# # #####################################################################

# # run from day 7 to 28

# start with running 7-21 : the following two in parallel
if run_component == "highDDD_7_21":
    # # part 1: run days 7 to 21 (14 days) - no vaccination yet
    v06_functions.run_auto_strategies(
        state="NSW",
        previous_unique_output="04_high DDD",
        previous_output_suffix_int=4,
        total_days_to_run_for=14,
        create_download_folder=False,
        strategy="high DDD",
        seed=property_seed,
    )

if run_component == "lowDDD_7_21":
    v06_functions.run_auto_strategies(
        state="NSW",
        previous_unique_output="04_high DDD",
        previous_output_suffix_int=4,
        total_days_to_run_for=14,
        create_download_folder=False,
        strategy="low DDD",
        seed=property_seed,
    )

#### each of these can be run in parallel:
# # HIGH DDD + vaccination
if run_component == "highDDD_vac":
    # part 2: now put in vaccination from day 21 - 28
    v06_functions.run_auto_strategies(
        state="NSW",
        previous_unique_output="05_high DDD",
        previous_output_suffix_int=5,
        total_days_to_run_for=7,
        create_download_folder=True,
        download_folder_name=os.path.join(download_folder, "day_28_high_DDD_vaccination"),
        strategy="high DDD vaccination",
        seed=property_seed,
    )

    # ### Then running to time point 3, day 56  (another 28 days)
    # HIGH DDD + vaccination
    v06_functions.run_auto_strategies(
        state="NSW",
        previous_unique_output="06_high DDD vaccination",
        previous_output_suffix_int=6,
        total_days_to_run_for=28,
        create_download_folder=True,
        download_folder_name=os.path.join(download_folder, "day_56_high_DDD_vaccination"),
        strategy="high DDD vaccination",
        seed=property_seed,
    )

# # HIGH DDD + no vaccination
if run_component == "highDDD_novac":
    v06_functions.run_auto_strategies(
        state="NSW",
        previous_unique_output="05_high DDD",
        previous_output_suffix_int=5,
        total_days_to_run_for=7,
        create_download_folder=True,
        download_folder_name=os.path.join(download_folder, "day_28_high_DDD"),
        strategy="high DDD",
        seed=property_seed,
    )
    # Then running to time point 3, day 56  (another 28 days)
    # # HIGH DDD + no vaccination
    v06_functions.run_auto_strategies(
        state="NSW",
        previous_unique_output="06_high DDD",
        previous_output_suffix_int=6,
        total_days_to_run_for=28,
        create_download_folder=True,
        download_folder_name=os.path.join(download_folder, "day_56_high_DDD"),
        strategy="high DDD",
        seed=property_seed,
    )


if run_component == "lowDDD_vac":
    # # LOW DDD + vaccination
    v06_functions.run_auto_strategies(
        state="NSW",
        previous_unique_output="05_low DDD",
        previous_output_suffix_int=5,
        total_days_to_run_for=7,
        create_download_folder=True,
        download_folder_name=os.path.join(download_folder, "day_28_low_DDD_vaccination"),
        strategy="low DDD vaccination",
        seed=property_seed,
    )
    # Then running to time point 3, day 56  (another 28 days)
    v06_functions.run_auto_strategies(
        state="NSW",
        previous_unique_output="06_low DDD vaccination",
        previous_output_suffix_int=6,
        total_days_to_run_for=28,
        create_download_folder=True,
        download_folder_name=os.path.join(download_folder, "day_56_low_DDD_vaccination"),
        strategy="low DDD vaccination",
        seed=property_seed,
    )

# # LOW DDD + no vaccination
if run_component == "lowDDD_novac":
    v06_functions.run_auto_strategies(
        state="NSW",
        previous_unique_output="05_low DDD",
        previous_output_suffix_int=5,
        total_days_to_run_for=7,
        create_download_folder=True,
        download_folder_name=os.path.join(download_folder, "day_28_low_DDD"),
        strategy="low DDD",
        seed=property_seed,
    )
    # Then running to time point 3, day 56  (another 28 days)
    v06_functions.run_auto_strategies(
        state="NSW",
        previous_unique_output="06_low DDD",
        previous_output_suffix_int=6,
        total_days_to_run_for=28,
        create_download_folder=True,
        download_folder_name=os.path.join(download_folder, "day_56_low_DDD"),
        strategy="low DDD",
        seed=property_seed,
    )
