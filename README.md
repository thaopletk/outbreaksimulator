# Disease and decision simulator

*Simulates disease outbreaks given management decisions, and outputs synthetic data for simulation workshops*

This is an infectious animal disease outbreak simulator developed as part of the [Enhancing Models for Rapid Decision-Support in Emergency Animal Disease Outbreaks (HASTE)](https://ardc.edu.au/project/enhancing-models-for-rapid-decision-support-in-emergency-animal-disease-outbreaks/) project. The aim of this simulator is to simulate a sufficiently realistic animal disease outbreak scenario and synthetic data that could be recorded during an emergency animal disease outbreak, which is then used as part of decision making and used by other mathematical modelling tools. The simulator supports branching decision-making through various save points.

This repository branch documents the version used to run simulation exercises based on a hypothetical **lumpy skin disease** outbreak in Eastern Australia.

**Key features**:
- Disease spread via close contact, movements and generalised local spatial dispersal (for lumpy skin disease, it is intended to mimic local vector dispersal)
- Animal movements between different types of premises
- Multiple management options including movement restrictions, vaccination, depopulation, surveillance and laboratory testing
- Data outputs at end of simulation periods allows return to previous time points and branching decision-making.

**Code requirements**:
- Python (3.12.10)

**Code written by Thao P. Le, Isobel Abell and Martin Cyster**
Base code and FMD_modelling module written by Isobel Abell, adapted by Thao P. Le, with column plots plotting support from Martin Cyster.

**data** folder: contains various map data

**FMD_modelling** folder: submodule containing infectious disease spread code

**simulator** folder: containing this-project-specific elements of the simulation code, including spatial system setup, any modified infectious disease components, management actions etc.

**scenarios** folder: contains the code that calls the simulation code

# Outbreak simulation workflow


**IMPORTANT**: first, you need to download various datasets that are too large to be included in this repository into the **/data** folder 
1. `data/clum_50m_2023_v2`: Catchment scale land use data - "Catchment Scale Land Use of Australia v2" https://www.agriculture.gov.au/abares/aclump/land-use/catchment-scale-land-use-and-commodities-update-2023#downloads
- direct download link: https://www.agriculture.gov.au/sites/default/files/documents/clum_50m_2023_v2.zip
2. `data/SAL_2021_AUST_GDA2020_SHP`: suburbs and localities information for Australia, 2021 version, found on https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-3-july-2021-june-2026/access-and-downloads/digital-boundary-files
- direct download link: https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs/edition-3-july-2021-june-2026/access-and-downloads/digital-boundary-files/SAL_2021_AUST_GDA2020_SHP.zip


**LSD test run (smaller run)**

Run `scenarios\LSD_test.py`

**LSD main run**

Run the `LSD_workshop_*.py` files in turn. Some slurm scripts are provided as examples, starting with
- `slurm_venv_setup.py`
- `slurm_LSD_workshop_1_initial_spread.sh`
- `slurm_LSD_workshop_2_deteciton_two_weeks.sh`


**The main steps**:
The model procedes through these setps:
1. Initiates the map, including property locations and sizes, and setting up neighbouring relationships
2. Seeds the infection
3. Undetected spread: Runs undetected spread until first report
4. Management stage: including default management (contract tracing local movement restrictions, clinical examination, lab testing and culling) and additional management options (large-scale movement restrictions, testing, vaccination, ring culling, and their combinations)
5. Final outputs (total number of cases etc.)


# Technical notes and references

### Virtual environment

Initiate virtual environment using the following if not yet created

`python -m venv venv`

Then activate (on Windows) with

`. venv/Scripts/activate`

And then you should be in the virtual environment!

You can then deactivate with:

`deactivate`

### Running in the virtual environment

```sh
. venv/Scripts/activate
pip install -r requirements.txt
python scenarios/LSD_test.py
```

### Formatting

Format using Black

https://www.freecodecamp.org/news/auto-format-your-python-code-with-black/

https://black.readthedocs.io/en/stable/getting_started.html 

`pip install black`

`black sample_code.py`

To use it as a pre-commit hook, also run:

`pip install pre-commit`

`pre-commit install`
