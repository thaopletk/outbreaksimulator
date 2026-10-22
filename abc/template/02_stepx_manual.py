#%%
from pathlib import Path
import os
import sys
import shutil
import random
import re
import importlib

import joblib
import numpy as np
import pandas as pd
import pickle

from shapely.geometry import Polygon
from scipy.stats import gamma
from pyproj import Transformer

# 0. user defined functions
def temporal_counts(df, t_start, t_end, column="t_e"):
    days = np.arange(t_start, t_end + 1)

    counts = (
        pd.to_numeric(df[column], errors="coerce")
        .dropna()
        .value_counts()
        .reindex(days, fill_value=0)
        .sort_index()
    )

    return counts.to_numpy()

def make_sim_temporal(res, t_start, t_end):
    days = np.arange(t_start, t_end + 1)

    columns = {
        "E": "t_e",
        "I": "t_i",
        "C": "t_c",
        "N": "t_n",
        "R": "t_r",
        "D": "t_d"
    }

    sim_temporal = pd.DataFrame({"t": days})

    for name, col in columns.items():
        if col in res.columns:
            sim_temporal[name] = (
                pd.to_numeric(res[col], errors="coerce")
                .value_counts()
                .reindex(days, fill_value=0)
                .to_numpy(dtype=int)
            )
        else:
            raise ValueError(f"Missing column: {col}")

    return sim_temporal

# 1. Load data and parameters
workdir = Path("C:/TK/outbreaksimulator/abc/template") # not needed in HPC
os.chdir(workdir)
out_dir = Path("Out")

# Load setup file
setup_file = Path((out_dir / "abc.setup.file.txt").read_text(encoding="utf-8").strip())
print("Setup file:", setup_file)
setup = joblib.load(setup_file)
globals().update(setup)

# Load generation
g = int((out_dir / "g.txt").read_text(encoding="utf-8").strip())
print("Generation:", g)

if g > 1:
    previous_file = out_dir / f"abc.g{g-1}.postclust.joblib"
    previous_results = joblib.load(previous_file)
    globals().update(previous_results)
    g += 1
print("Generation:", g)

task_id = int(os.environ.get("SLURM_ARRAY_TASK_ID", "2")) # if it run on PC, task_id will set as 1

# 2. Create simulation directories and copy, paste generated pickle obj to task folders
sim_dir = Path(f"task{task_id}")
sim_dir.mkdir(parents=True, exist_ok=True)
detection_dir = sim_dir / "03_outbreak_detection"
detection_dir.mkdir(parents=True, exist_ok=True)
source_dir = Path("03_outbreak_detection")
files_to_copy = [
    "properties_03_outbreak_detection",
    "outbreakobject_03_outbreak_detection",
    "approx_known_data_03_outbreak_detection.csv"
]
for filename in files_to_copy:
    shutil.copy2(source_dir / filename, detection_dir / filename)

# 3. import user defined functions
sys.path.insert(0, str(Path("../../scenarios").resolve())) # add scenarios_path
sys.path.insert(0, str(Path("../..").resolve())) # add simulator_path
v06_functions = importlib.import_module("simulator.v06_functions")
from simulator.premises import Premises
from simulator.disease_simulation import DiseaseSimulation

seed = 100000 + task_id
random.seed(seed)
np.random.seed(seed)

i = 1  # Number of accepted particles
k = 1  # Acceptance-rate counter
# Count accepted particles for the current generation
pattern = re.compile(rf"^gen_{g}_task_")
N_particles_g = sum(
    bool(pattern.match(p.name))
    for p in out_dir.iterdir()
    if p.is_file()
)

# 4. empty parameter
base_params = [
        "beta_intra", "sigma_intra", "gamma_intra",
        "alpha", "beta0", "kernel_type", "psi", "rho0",
        "zeta", "zeta_1", "zeta_2", "zeta_3",
        "chi", "xi", "xi_1", "xi_2", "xi_3", "theta"
    ]

lsd_params = [
        "add_c", "add_v", "mu_c", "mu_v",
        "a1", "a2", "a3", "a4",
        "v_vc", "v_cv", "d_v",
        "omega", "mu_lsd", "trans",
        "scaling_c", "scaling_v"
    ]

hpai_params = [
        "beta_wind", "beta_animal",
        "latent_period", "infectious_period",
        "preclinical_period",
        "lab_test_sensitivity", "clinical_test_sensitivity",
        "cull_delay", "contact_tracing_delay",
        "lab_test_delay", "clinical_delay",
        "vaccination_delay",
        "clinical_reporting_threshold",
        "prob_report", "prob_report_commercial",
        "prob_report_backyard", "r_wind"
    ]
    
if scenario in (10, 20):
        param_names = base_params
elif scenario == 30:
        param_names = base_params + lsd_params
elif scenario == 40:
        param_names = hpai_params

paras = dict.fromkeys(param_names, np.nan)

for idx, val in zip(paras_fixed, fixed_vals):
        paras[para_names[idx]] = val

if g == 1:
            for j, idx in enumerate(paras_index):
                value = np.random.uniform(lm_low[j], lm_upp[j])
                if idx in paras_index_ratio:
                    value = 10 ** value # Ratio parameters sampled on log10 scale
                paras[para_names[idx]] = value

else:  # g > 1
            # Select a particle from the previous generation
            p = np.random.choice(N_particles, p=w_old)
            # Perturb estimated parameters
            for j, idx in enumerate(paras_index):

                lower = lm_low[j]
                upper = lm_upp[j]
                sd = np.sqrt(2 * tau_var_old[j])

                if idx in paras_index_ratio:
                    mean = np.log10(theta_old[p, j])
                else:
                    mean = theta_old[p, j]

                # Rejection sampling within prior bounds
                while True:
                    value = np.random.normal(mean, sd)
                    if lower <= value <= upper:
                        break

                # Convert log10-scale parameters back
                if idx in paras_index_ratio:
                    value = 10 ** value

                paras[para_names[idx]] = value

disease_parameters = {
            "chicken": {
                key: float(paras[key])
                for key in [
                    "beta_wind",
                    "beta_animal",
                    "latent_period",
                    "infectious_period",
                    "preclinical_period"
                ]
            }
        }

job_parameters = {
            key: float(paras[key])
            for key in [
                "lab_test_sensitivity", # not included in properties or outbreakobject
                "clinical_test_sensitivity", # not included in properties or outbreakobject
                "cull_delay",
                "contact_tracing_delay", # not included in properties or outbreakobject
                "lab_test_delay", # not included in properties or outbreakobject
                "clinical_delay", # not included in properties or outbreakobject
                "vaccination_delay"
            ]
        }

scenario_parameters = {
            key: float(paras[key])
            for key in [
                "clinical_reporting_threshold",
                "prob_report",
                "prob_report_commercial",
                "prob_report_backyard"
            ]
        }

spatial_only_parameters = {
        "r_wind": float(paras["r_wind"]),
        "xrange": xrange,
        "yrange": yrange
        }

    # update pickle objects
with open(detection_dir / "properties_03_outbreak_detection", "rb") as f:
        properties = pickle.load(f)    
with open(detection_dir / "outbreakobject_03_outbreak_detection", "rb") as f:
        diseaseoutbreak = pickle.load(f)

    # update disease parameters
diseaseoutbreak.disease_parameters = disease_parameters
for key, value in disease_parameters["chicken"].items():
        getattr(diseaseoutbreak, key)["chicken"] = value

    # update scenario parameters
for key, value in scenario_parameters.items():
        setattr(diseaseoutbreak, key, value)

    # update spatial parameters
diseaseoutbreak.r_wind = spatial_only_parameters["r_wind"]

    # update property-level parameters
for prop in properties:
        prop.cull_delay = job_parameters["cull_delay"]
        prop.vaccinate_delay = job_parameters["vaccination_delay"]

    # save updated pickle objects
with open(detection_dir / "properties_03_outbreak_detection", "wb") as f:
        pickle.dump(properties, f)
with open(detection_dir / "outbreakobject_03_outbreak_detection", "wb") as f:
        pickle.dump(diseaseoutbreak, f)
print("done")

#%%
# 4. run simulations across configured timepoints
previous_unique_output = "03_outbreak_detection"
previous_output_suffix_int = 3

for t_diff, policy in zip(previous_t_diff[:-1], previous_policy[:-1]):

        if policy is None:
            raise ValueError("Invalid DDD/vaccination policy")

        print(f"Running {t_diff} days with {policy}")

        v06_functions.run_auto_strategies(
            state="NSW",
            previous_unique_output=previous_unique_output,
            previous_output_suffix_int=previous_output_suffix_int,
            total_days_to_run_for=int(t_diff),
            create_download_folder=False,
            strategy=policy,
            seed=None,
            base_folder=sim_dir.resolve(),
        )

        previous_output_suffix_int += 1
        previous_unique_output = f"{previous_output_suffix_int:02d}_{policy}"
print("done")

#%%
# comparison of simulation and observation
folder_name = f"{previous_output_suffix_int:02d}_{policy}"
sim_file = sim_dir / folder_name / f"fake_data_apparent_RTM_{folder_name}.csv"
res = pd.read_csv(sim_file)

res["clinical_date"] = pd.to_datetime(
    res["clinical_date"], format=date_format, errors="coerce"
)
ip_mask = res["status"] == "IP"
incubation_periods = np.round(gamma.rvs(a=incubation_params[0], scale=incubation_params[2], size=ip_mask.sum()), 0)
res["t_e"] = np.nan
res.loc[ip_mask, "t_e"] = (
    res.loc[ip_mask, "clinical_date"] - pd.to_timedelta(incubation_periods, unit="D") - date0
).dt.days

# convert coordinates
transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
res["changed_lon"], res["changed_lat"] = transformer.transform(
    res["longitude"].to_numpy(),
    res["latitude"].to_numpy()
)
res["x_km"] = (res["changed_lon"] / 1000).round(3)
res["y_km"] = (res["changed_lat"] / 1000).round(3)

# temporal discrepancy
target_E = temporal_counts(dat_today, t_detect, t_today)
sim_E = temporal_counts(res, t_detect, t_today)
distance_temporal = np.abs(target_E - sim_E).sum()

# spatial discrepancy
res["cut_x"] = pd.cut(res["x_km"], bins=x_breaks, include_lowest=True, right=True)
res["cut_y"] = pd.cut(res["y_km"], bins=y_breaks, include_lowest=True, right=True)
sim_ip = res.loc[res["t_e"].isin(t_range)]
sim_counts = (
    sim_ip.groupby(["cut_x", "cut_y"], observed=True)
    .size()
    .reindex(all_cells, fill_value=0)
)
target_n = target_spatial["n"].to_numpy()[cell_index]
sim_n = sim_counts.to_numpy()[cell_index]
if len(target_n) < 2 or np.std(target_n) == 0 or np.std(sim_n) == 0:
    distance_spatial = 0.0
else:
    distance_spatial = float(np.corrcoef(target_n, sim_n)[0, 1])

# check the criteria
accepted = (
    distance_temporal <= epsilon_temporal[g-1]
    and distance_spatial >= epsilon_spatial[g-1]
    and res["t_e"].between(t_detect + 1, t_today).sum() > 0
)

if accepted:
    # simulate from t_today
    v06_functions.run_auto_strategies(
        state="NSW",
        previous_unique_output=previous_unique_output,
        previous_output_suffix_int=previous_output_suffix_int,
        total_days_to_run_for=int(previous_t_diff[-1]),
        create_download_folder=False,
        strategy=previous_policy[-1],
        seed=None,
        base_folder=sim_dir.resolve()
    )
    final_suffix_int = previous_output_suffix_int + 1
    final_folder = f"{final_suffix_int:02d}_{previous_policy[-1]}"

    # Load final simulation results
    final_file = (sim_dir / final_folder / f"fake_data_apparent_RTM_{final_folder}.csv")
    res_final = pd.read_csv(final_file)
    
    date_columns = ["clinical_date", "notification_date", "recovery_date", "removal_date", "vacc_date"]
    for col in date_columns:
        res_final[col] = pd.to_datetime(res_final[col], format=date_format, errors="coerce")
    
    res_final["t_c"] = (res_final["clinical_date"] - date0).dt.days
    res_final["t_n"] = (res_final["notification_date"] - date0).dt.days
    res_final["t_r"] = (res_final["recovery_date"] - date0).dt.days
    res_final["t_d"] = (res_final["removal_date"] - date0).dt.days
    res_final["t_v"] = (res_final["vacc_date"] - date0).dt.days
    
    ip_mask_final = res_final["status"] == "IP"
    
    incubation_periods = np.round(
        gamma.rvs(a=incubation_params[0], scale=incubation_params[2], size=ip_mask_final.sum()), 0
    )
    res_final["t_e"] = np.nan
    res_final.loc[ip_mask_final, "t_e"] = (res_final.loc[ip_mask_final, "clinical_date"]
        - pd.to_timedelta(incubation_periods, unit="D") - date0).dt.days

    latent_periods = np.round(
        gamma.rvs(a=latent_params[0], scale=latent_params[2], size=ip_mask_final.sum()), 0
    )
    res_final["t_i"] = np.nan
    res_final.loc[ip_mask_final, "t_i"] = (res_final.loc[ip_mask_final, "t_e"] + latent_periods)
    res_final["t_i"] = np.minimum(res_final["t_i"], res_final["t_c"])
    
    # Generate temporal counts up to t_max
    sim_temporal = make_sim_temporal(res_final, t_start, t_max)
    
    # output directory and save file
    output_dir = Path("Out")
    output_file = (output_dir / f"gen_{g}_task_{task_id}_particle_{i}_iter_{k}.joblib")
    # store accepted particle
    result = {
        "seed": seed,
        "paras": paras,
        "distance_temporal": distance_temporal,
        "distance_spatial": distance_spatial,
        "sim_temporal": sim_temporal,
        "sim_t_e": res_final[["id", "t_e"]].copy(),
        "k": k
    }
    joblib.dump(result, output_file)
    # update counters
    i += 1


N_particles_g = len(list(Path("Out").glob(f"gen_{g}_task_*.joblib")))
acc_rate = (i - 1) / k

print(
    f"current acceptance rate = {acc_rate:.6f}; "
    f"N.particles = {N_particles_g}",
    end="\r",
    flush=True
)

    
# remove simulation output folders, keeping 03_outbreak_detection
for folder in sim_dir.iterdir():
    if folder.is_dir() and folder.name != "03_outbreak_detection":
        shutil.rmtree(folder)

# %%
# Remove simulation directory
if sim_dir.exists():
    shutil.rmtree(sim_dir)
# %%
from pathlib import Path
import shutil
import random

out_dir = Path("Out")
source = out_dir / "gen_1_task_2_particle_1_iter_1.joblib"

# Generate 1,000 unique random numbers
particle_ids = random.sample(range(2, 100000), 1000)
iter_ids = random.sample(range(2, 100000), 1000)

for particle, k in zip(particle_ids, iter_ids):
    destination = out_dir / (
        f"gen_1_task_1_particle_{particle}_iter_{k}.joblib"
    )

    shutil.copy2(source, destination)

print("Created 1,000 copies.")
# %%
