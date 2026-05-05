# Disease and decision simulator

*Simulates disease outbreaks given management decisions, and outputs synthetic data for simulation workshops*

This is the infectious animal disease outbreak and decision-making simulator for the [Enhancing Models for Rapid Decision-Support in Emergency Animal Disease Outbreaks (HASTE)](https://ardc.edu.au/project/enhancing-models-for-rapid-decision-support-in-emergency-animal-disease-outbreaks/) project. This simulator simulates a realistic disease outbreak scenario and synthetic data that could be recorded during an emergency animal disease outbreak. Users can input in different management options at differenet time points; the code supports branching decision-making.

**Key features**:
- Disease spread via close contact, movements and wind-aided fomite dispersal
- Animal and animal material movements between different types of premises
- Multiple management options including movement restrictions, vaccination, depopulation, surveillance and laboratory testing
- Version v0.5+ can accept CSV or Excel spreadsheets and shapefiles to specific the exact management actions over a customisable amount of days
- Data outputs at end of simulation periods allows return to previous time points and branching decision-making.

**Code requirements**:
- Python (3.12.10)
- Some kind of GIS installation for mapping outputs
- Live internet connection for address finding

**Code written by**:
- Thao (TK) P. Le: lead programmer
- Isobel Abell: programmer of infectious disease components 
- Martin Cyster: plotting assistance

For assistance, contact TK at tk.le (at) unimelb.edu.au

**Report**:
Thao P Le, Isobel Abell, Simon Firestone, Sarita Rosenstock, Chris Baker (2026). HASTE Simulation exercise workshops for EAD preparedness - Joint WP4 and WP5 final report. The University of Melbourne. Report. [doi:10.26188/32129971.v2](https://doi.org/10.26188/32129971.v2)

## Quick start - Highly pathogenic avian influenza (v0.5)

1. Download the HPAI-version of the repository [v0.5.3](https://github.com/thaopletk/outbreaksimulator/releases/tag/v0.5.3)  

`git clone https://github.com/thaopletk/outbreaksimulator.git`

2. Install virtual environment and requirements. For Windows:

```
python -m venv venv
. venv/Scripts/activate
pip install -r requirements.txt
```

3. Download required data files

- ABS: region information
- Wildlife information
- Wind data (has already been included in the repo - downloaded from the Climate Data Store)

4. Run an outbreak of HPAI in NSW:

Run `scenarios/v06_CONTROLLER.py`, making sure to uncomment or comment out appropriate sections.


## Repository Structure

📂**FMD_modelling**: folder containing infectious disease spread code written by Isobel Abell, forms basis of disease spread and tracking

📂**data**: stores geographic data (Australian states, LGAs, postal areas etc), property distribution data (e.g. different types of animal industry premises by LGA) and movement network information (directed movements from different types of premises)

📂**figure_gen**: plotting code written by Martin Cyster

📂**images**: images for plotting, readmes

📂**scenarios**: contains the code that calls the simulation code and runs specific scenarios

📂**simulator**: simulation code, including spatial system setup, any modified infectious disease components, management actions etc.

📂**tests** folder: contains some tests. Note: incomplete.


## v0.2 simulator workflow - Lumpy Skin Disease

**The main steps**:
1. Initiate map
2. Seed infection
3. Undetected spread: Run time forward until first report
4. Management stage: including default management (contract tracing local movement restrictions, clinical examination, lab testing and culling) and additional management options (large-scale movement restrictions, testing, vaccination, ring culling, and their combinations)
5. Final outputs (total number of cases etc.)

The main file that produced the outputs for the December 2024 Trial simulation exercise (v0.2) is [**maincontrol_trial.py**](scenarios/maincontrol_trial.py).

![Diagram of the steps of the outbreak simulator: initiate map, seed infection, run time forward until first report, default management (contract tracing local movement restrictions, clinical examination, lab testing and culling) and additional management options (large-scale movement restrictions, testing, vaccination, ring culling, and their combinations), and final outputs (total number of cases etc.) ](images/outbreaksimulator_workflow.png)

<!--# Planned outbreak simulator

 
![Diagram of the planned outbreak simulator, including disease dynamics, spread, simulation code, spatial arrangement, management](images/outbreak_simulator_model_diagram.png) -->

<!-- # Current state

![Diagram of the current state of the outbreak simulator, including disease dynamics, spread, simulation code, spatial arrangement, management](images/outbreak_simulator_model_current_status.png)


(note that this management process png is no longer up to date...)
![Diagram of the current state of management](images/management_process.png)

# Example outputs

![Example of a generated base map](images/base_map.png)

![Example (snapshot) of an outbreak](images/simulation_snapshot.png)
 -->
