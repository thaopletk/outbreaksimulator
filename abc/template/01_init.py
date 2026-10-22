from pathlib import Path
import argparse
import sys
import numpy as np
import pandas as pd
import yaml
import joblib
import pickle
import copy
import ast
import itertools

from pyproj import Transformer
from scipy.spatial.distance import pdist, squareform
from scipy.stats import gamma
from shapely.geometry import Point
from datetime import datetime

# 0. user defined functions and record start time
time = datetime.now().astimezone().isoformat(timespec="seconds")

def epi_gammabuster(mode, max_val, qmax=0.99, max_shape1=10, step=0.01):
    # candidate shape and scale parameters
    shape1 = np.arange(1 + step, max_shape1 + step / 2, step)
    shape2 = mode / (shape1 - 1)

    # gamma cumulative probability at max_val
    p_vec = gamma.cdf(max_val, a=shape1, scale=shape2)

    # find shape parameter closest to qmax
    index = np.argmin(np.abs(p_vec - qmax))

    shape1 = shape1[index]
    shape2 = shape2[index]

    # distribution statistics
    mode_est = (shape1 - 1) * shape2
    median = gamma.ppf(0.50, a=shape1, scale=shape2)
    mean = shape1 * shape2
    variance = shape1 * shape2**2
    skew = 2 / np.sqrt(mean**2 / variance)
    
    return {
        "shape": float(shape1),
        "scale": float(shape2),
        "rate": float(1 / shape2),
        "mode": float(mode_est),
        "median": float(median),
        "mean": float(mean),
        "variance": float(variance),
        "skew": float(skew)
    }

def approx_dat_to_properties(dat, approx_known_dat, seed=123):
    
    rng = np.random.default_rng(seed)
    
    dat = dat.copy().reset_index(drop=True)
    approx_known_dat = approx_known_dat.copy()

    if approx_known_dat["sim_id"].duplicated().any():
        raise ValueError("Duplicate sim_id in approx_known_dat")

    # avoid overwriting dat columns
    known = approx_known_dat.set_index("sim_id")

    # helper functions
    def valid(v):
        if v is None:
            return False
        if isinstance(v, str):
            return v.strip() not in ("", "NA", "nan", "None")
        return bool(pd.notna(v))

    def get_value(row, col, default=None):
        if col in row.index and valid(row[col]):
            return row[col]
        return default

    def weighted_sample(series, default=None):
        values = series.dropna()
        values = values[
            ~values.astype(str).isin(["", "NA", "nan", "None"])
        ]

        if len(values) == 0:
            return default

        probabilities = values.value_counts(normalize=True)

        return rng.choice(
            probabilities.index.to_numpy(),
            p=probabilities.to_numpy()
        )

    def get_known(sim_id, col, default=None):
        if sim_id in known.index and col in known.columns:
            value = known.at[sim_id, col]
            if valid(value):
                return value
        return default

    def get_date(row, col):
        value = get_value(row, col)
        if value is None:
            return "NA"

        if isinstance(value, (int, float, np.integer, np.floating)):
            return str(value)

        date = pd.to_datetime(value, dayfirst=True, errors="coerce")

        if pd.notna(date):
            return date.strftime("%d/%m/%Y")

        return str(value)

    # 3. prepare imputed values
    # region: nearest available LGA by row order
    region = pd.Series(
        [
            get_known(sim_id, "LGA")
            for sim_id in dat["id"]
        ]
    )

    region = region.ffill().bfill()

    # 4. create Premises objects
    properties = []
    Premises.id_iter = itertools.count()
    for i, row in dat.iterrows():

        sim_id = int(row["id"])

        # basic premises information
        x = float(row["longitude"])
        y = float(row["latitude"])

        area_ha = float(
            get_known(sim_id, "area", get_value(row, "area_h", 0))
        )

        num_animals = int(get_value(row, "n_total", get_value(row, "total_chickens", 0)))

        # polygon (requires projected coordinates in metres)
        radius = np.sqrt(max(area_ha, 0) * 10000 / np.pi)
        polygon = Point(x, y).buffer(max(radius, 0.001))

        # enterprise
        property_type = get_known(sim_id, "enterprise")

        if property_type is None:
            property_type = weighted_sample(
                approx_known_dat["enterprise"],
                default="NA"
            )

        # create object
        p = Premises(
            num_animals=num_animals,
            coordinates=np.array([x, y], dtype=np.float64),
            area_ha=area_ha,
            neighbourhood=[],
            property_polygon=polygon,
            property_polygon_puffed=polygon,
            property_type=str(property_type),
            animal_type="chicken",
            allowed_movement={}
        )

        # identifiers
        p.id = sim_id
        p.sim_id = sim_id
        p.case_id = get_known(sim_id, "case_id", "")

        # premises information
        p.x = np.float64(x)
        p.y = np.float64(y)
        p.type = str(property_type)
        p.region = (
            str(region.iloc[i])
            if valid(region.iloc[i]) else "NA"
        )
        p.state = None
        p.data_source = get_known(sim_id, "data_source")
        if p.data_source is None:
            p.data_source = weighted_sample(
                approx_known_dat["data_source"],
                default="NA"
            )
        p.housing_type = get_known(sim_id, "housing")
        if p.housing_type is None:
            p.housing_type = weighted_sample(
                approx_known_dat["housing"],
                default=""
            )

        # infection information from dat
        p.status = get_value(row, "status", "NIL")
        p.ip = get_known(sim_id, "ip", "")
        p.exposure_date = get_date(row, "exposure_date")
        p.clinical_date = get_date(row, "clinical_date")
        p.notification_date = get_date(row, "notification_date")
        p.recovery_date = get_date(row, "recovery_date")
        p.removal_date = get_date(row, "removal_date")
        p.vacc_date = get_date(row, "vacc_date")

        # Known premises information
        p.known_birds = int(
            get_known(sim_id, "total_chickens", get_value(row, "total_chickens", num_animals))
        )

        p.known_area = float(
            get_known(sim_id, "area", get_value(row, "area_h", area_ha))
        )

        known_sheds = get_known(sim_id, "sheds")

        if known_sheds is None:
            known_sheds = weighted_sample(approx_known_dat["sheds"], default="")

        p.known_sheds = known_sheds

        # chicken-related information
        p.sheds = {
            1: {
                "chickens": [],
                "cleaning": False,
                "cleaning_completion": None
                }
            }
        p.num_sheds = 0

        p.approx_chickens_per_shed = (
            int(round(num_animals * 1.1))
            if num_animals > 0 else 100
        )

        p.eggs = 0

        # movement and neighbourhood
        p.neighbourhood = []
        p.total_neighbours = 0
        movement_types = [
            "layers free-range",
            "layers caged",
            "layers barn",
            "broiler farm",
            "pullet farm",
            "egg processing",
            "abbatoir",
            "hatchery",
            "breeder",
            "backyard"
            ]
        p.movement_neighbours = {
            movement_type: []
            for movement_type in movement_types
            }
        p.allowed_movement = {}
        p.allowed_movement_details = {}

        # additional information
        p.day_of_last_lab_test = get_known(sim_id, "last_PCR_date")
        p.case_created_date = get_known(sim_id, "case_created_date")
        p.address = ""
        p.location = ""
        self_report_date = get_known(sim_id, "self_report_date")
        p.clinical_report_outcome = (
            True
            if p.status == "IP" and self_report_date is not None
            else None
        )
        p.reported_status = (
            p.status == "IP" and self_report_date is not None
        )

        # custom information
        extra_columns = [
            "self_report_date",
            "last_surveillance_date",
            "animals_clinical",
            "last_PCR_date",
            "PCR_result",
            "last_cull_date",
            "culled_birds",
            "destroyed_eggs",
            "last_conducted_contact_tracing",
            "vaccinated_birds"
        ]

        for col in extra_columns:
            p.custom_info[col] = get_known(sim_id, col, "NA")

        properties.append(p)

    return properties


# 1. working directory and arguments
parser = argparse.ArgumentParser(description="ABC initialisation")

parser.add_argument(
    "config_file",
    nargs="?",
    default="config_HPAI",
    help="Configuration filename without .yaml"
)

if "ipykernel" in sys.modules:
    args = parser.parse_args([])
else:
    args = parser.parse_args()

config_file = args.config_file

print(f"Arg input: {config_file}")


# 2. load configuration and priors
config_path = (Path("../../config") / f"{config_file}.yaml").resolve()
with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

priors_file = config["general"]["priors_file"]
priors_path = (Path("../../config") / priors_file).resolve()
priors = pd.read_csv(priors_path)

out_dir = Path("Out")
out_dir.mkdir(parents=True, exist_ok=True)

setup_file = config["general"]["setup_file"] # Setup filename (to be changed to pickle later)

dat_file = config["general"]["data_file"] # fake_data_apparent_RTM_05_high DDD.csv (current outbreak data)
dat_path = (Path("../../") / dat_file).resolve()
dat = pd.read_csv(dat_path)

approx_dat_file = config["general"]["approx_known_data_file"] # approx_known_data_03_outbreak_detection.csv (premises and first IP info)
approx_dat_path = (Path("../../") / approx_dat_file).resolve()
approx_dat = pd.read_csv(approx_dat_path)

# change NIL to IP if notification_date is available
check_status = (
    (dat["status"] == "NIL") &
    (dat["notification_date"].notna())
)
dat.loc[check_status, "status"] = "IP"

date_format = config["general"]["date_format"]

# TK simulator configuration
previous_t_point = config["TK"]["t_point"]
previous_DDD = config["TK"]["DDD"]
previous_vaccine = config["TK"]["vaccine"]
xrange = config["TK"]["xrange"]
yrange = config["TK"]["yrange"]
epsg = config["TK"]["epsg"]
t_max = config["run_parameters"]["t_max"]
forecast_policy = config["TK"]["forecast_policy"]

# validate lengths
if not (
    len(previous_t_point) ==
    len(previous_DDD) ==
    len(previous_vaccine)
):
    raise ValueError(
        "previous_t_point, previous_DDD, and "
        "previous_vaccine must have the same length."
    )

# calculate simulation intervals
previous_t_point = list(previous_t_point) + [t_max]
previous_t_diff = np.diff([0] + previous_t_point).tolist()

policy_map = {
    ("high", False): "fast DDD",
    ("high", True): "fast DDD vaccination",
    ("low", False): "slow DDD",
    ("low", True): "slow DDD vaccination"
}

previous_policy = [
    policy_map.get((ddd, vaccine), None)
    for ddd, vaccine in zip(previous_DDD, previous_vaccine)
]
previous_policy.append(forecast_policy) # Policy to be applied from t_today onwards

# 3. setup simulation parameters
scenario = config["run_parameters"]["scenario"]
N_particles = config["run_parameters"]["n_particles"]
n_cpus = config["run_parameters"]["n_cpus"]
G = config["run_parameters"]["n_generations"]

temporal_tolerance_daily = config["tolerance"]["temporal_tolerance_daily"]
if temporal_tolerance_daily is not None and temporal_tolerance_daily != "NA":
    temporal_tolerance_daily = np.asarray(
        temporal_tolerance_daily, dtype=float
    ) # NA

epsilon_spatial = config["tolerance"]["spatial_tolerance"]
if epsilon_spatial is not None and epsilon_spatial != "NA":
    epsilon_spatial = np.asarray(epsilon_spatial, dtype=float)
else:
    default_spatial = [
        0.3, 0.4, 0.5, 0.6, 0.65,
        0.675, 0.7, 0.725, 0.75, 0.775
    ]
    epsilon_spatial = np.asarray(default_spatial[:G])
# check spatial tolerance schedule
if len(epsilon_spatial) != G:
    raise ValueError(
        "Spatial tolerance schedule and no. generations do not match"
    )

cell_reso = config["tolerance"]["cell_resolution"]


# 4. priors
para_names = priors["param_name"].to_numpy()
paras_index = np.where(priors["estimated_param"] == True)[0]
lm_low = priors.loc[paras_index, "lower_bound"].to_numpy()
lm_upp = priors.loc[paras_index, "upper_bound"].to_numpy()
paras_index_ratio = np.where(priors["prior_type"] == 2)[0] # Parameters on ratio scale; none for HPAI
paras_index_unif = paras_index[~np.isin(paras_index, paras_index_ratio)] # Parameters on uniform distribution
paras_fixed = np.where(priors["fixed_param"] == True)[0] # Fixed parameters
fixed_vals = priors.loc[paras_fixed, "value"].to_numpy()


# 5. outbreak data
incubation_mode = config["disease_assumptions"]["incubation_period"]["mode"]
incubation_max = config["disease_assumptions"]["incubation_period"]["max"]
latent_mode = config["disease_assumptions"]["latent_period"]["mode"]
latent_max = config["disease_assumptions"]["latent_period"]["max"]

incubation_stats = epi_gammabuster(mode=incubation_mode, max_val=incubation_max)
latent_stats = epi_gammabuster(mode=latent_mode, max_val=latent_max)

incubation_params = np.array([
    incubation_stats["shape"],
    incubation_stats["rate"],
    incubation_stats["scale"]
])

latent_params = np.array([
    latent_stats["shape"],
    latent_stats["rate"],
    latent_stats["scale"]
])

del incubation_stats, latent_stats

transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
dat["changed_lon"], dat["changed_lat"] = transformer.transform(
    dat["longitude"].to_numpy(),
    dat["latitude"].to_numpy()
)

# convert date columns
date_columns = ["clinical_date", "notification_date", "recovery_date", "removal_date", "vacc_date", "report_date"]
for col in date_columns:
    if col in dat.columns:
        dat[col] = pd.to_datetime(
            dat[col],
            format=date_format,
            errors="coerce"
        )

# coordinates in kilometres
dat["x_km"] = (dat["changed_lon"] / 1000).round(3)
dat["y_km"] = (dat["changed_lat"] / 1000).round(3)
coords = dat[["x_km", "y_km"]].to_numpy(dtype=float)
distmat = squareform(pdist(coords, metric="euclidean")).round(3)

# generate exposure dates from the gamma distribution
ip_mask = dat["status"] == "IP"
incubation_periods = np.round(gamma.rvs(a=incubation_params[0], scale=incubation_params[2], size=ip_mask.sum()), 0)
dat["exposure_date"] = pd.NaT
dat.loc[ip_mask, "exposure_date"] = (dat.loc[ip_mask, "clinical_date"] - pd.to_timedelta(incubation_periods, unit="D"))

# day 1 is set to an arbitrary number of days before the first exposure
if config["run_parameters"]["date0"] != "NA":
    date0 = pd.to_datetime(config["run_parameters"]["date0"], format=date_format)
else:
    date0 = (dat["exposure_date"].min() - pd.Timedelta(days=config["run_parameters"]["date0_offset"]))

# simulation time settings
t_start = 1
t_end = t_max

# calculate dates relative to date0
dat["t_c"] = (dat["clinical_date"] - date0).dt.days
dat["t_n"] = (dat["notification_date"] - date0).dt.days
dat["t_e"] = (dat["exposure_date"] - date0).dt.days
dat["t_r"] = (dat["recovery_date"] - date0).dt.days
dat["t_d"] = (dat["removal_date"] - date0).dt.days
dat["t_v"] = (dat["vacc_date"] - date0).dt.days

# generate latent periods for IPs only
latent_periods = np.round(gamma.rvs(a=latent_params[0], scale=latent_params[2], size=ip_mask.sum()), 0)
dat["t_i"] = np.nan
dat.loc[ip_mask, "t_i"] = (dat.loc[ip_mask, "t_e"] + latent_periods)
# ensure infectious start time does not exceed clinical onset
dat["t_i"] = np.minimum(dat["t_i"], dat["t_c"])

dat = dat[["id", "status", 
           "clinical_date", "notification_date", "exposure_date", "recovery_date", "removal_date", "vacc_date",
           "t_e", "t_i", "t_c", "t_n", "t_r", "t_d", "t_v",
           "longitude", "latitude", "changed_lon", "changed_lat", "x_km", "y_km",
           "area_h", "n_total"
        ]]

# simulation time settings
t_detect = int(dat["t_n"].min())
t_today_config = config["run_parameters"]["t_today"]
if t_today_config is None or str(t_today_config).upper() == "NA":
    t_today = int(dat["t_n"].max()) + 1 # t_today is the day after the last notification
else:
    t_today = int(t_today_config) + t_detect # we put t_today (t_detect based; e.g., 3 weeks after t_detect)
    if t_today > t_max:
        raise ValueError("t_max must be bigger than (t_detect + t_today).") 
    
dat_today = dat.copy()


# 6. outbreak data reconstrucion
mask = dat["t_e"] < t_detect
n_exposed = mask.sum()
print("Number of exposed premises:", n_exposed)

# recode IP and status
dat["ip"] = np.nan
dat.loc[mask, "ip"] = np.arange(1, n_exposed + 1)
dat["status"] = "NIL"
dat.loc[mask, "status"] = "IP"

# remove infection-related dates for non-IPs
cols = ["t_c", "t_n", "t_e", "t_i", "t_r", "t_d"]
dat.loc[~mask, cols] = np.nan


# 7. outbreak data reconstrucion
# a. temporal target
# observation window (inclusive)
t_range = np.arange(t_detect, t_today + 1)
target_temporal = pd.DataFrame({"t": t_range})

for col, event in [("t_e", "E"), ("t_i", "I"), ("t_c", "C"), ("t_n", "N"), ("t_r", "R"), ("t_d", "D")]:
    counts = dat_today[col].value_counts()
    target_temporal[event] = (
        counts.reindex(t_range, fill_value=0)
        .to_numpy(dtype=int)
    )

# temporal tolerance
if (temporal_tolerance_daily is None or (isinstance(temporal_tolerance_daily, str) and temporal_tolerance_daily.upper() == "NA")):
    n_steps = 8 if G <= 8 else G
    decay = np.round(np.exp(np.linspace(np.log(1), np.log(0.12), n_steps)), 4)[:G]
    temporal_tolerance_daily = (target_temporal["E"].mean() * 3 * decay)

# temporal tolerance for the entire fitted period
epsilon_temporal = np.ceil(np.asarray(temporal_tolerance_daily, dtype=float) * len(t_range)).astype(int)

if len(np.atleast_1d(epsilon_temporal)) != G:
    raise ValueError("Temporal tolerance schedule and no. generations do not match")

# b. spatial target
x_min = np.round(dat_today["x_km"].min() - 1, 0)
x_max = np.round(dat_today["x_km"].max() + 1, 0)
y_min = np.round(dat_today["y_km"].min() - 1, 0)
y_max = np.round(dat_today["y_km"].max() + 1, 0)

# grid boundaries
x_breaks = np.linspace(x_min, x_max, int(cell_reso) + 1)
y_breaks = np.linspace(y_min, y_max, int(cell_reso) + 1)

# assign every premises to a grid cell
dat_today["cut_x"] = pd.cut(
    dat_today["x_km"],
    bins=x_breaks,
    include_lowest=True,
    right=True
)

dat_today["cut_y"] = pd.cut(
    dat_today["y_km"],
    bins=y_breaks,
    include_lowest=True,
    right=True
)

# exposures during the observation window
dat_ip = dat_today.loc[dat_today["t_e"].isin(t_range)].copy()

# all possible grid cells
all_cells = pd.MultiIndex.from_product(
    [dat_today["cut_x"].cat.categories, dat_today["cut_y"].cat.categories],
    names=["cut_x", "cut_y"]
)

# number of infected premises per cell
spatial_counts = (
    dat_ip.groupby(["cut_x", "cut_y"], observed=True)
    .size()
    .reindex(all_cells, fill_value=0)
)

target_spatial = pd.DataFrame({
    "cell": np.arange(1, len(all_cells) + 1),
    "n": spatial_counts.to_numpy(dtype=int)
})

n_premises_cell = (
    dat_today.groupby(["cut_x", "cut_y"], observed=True)
    .size()
    .reindex(all_cells, fill_value=0)
    .reset_index(name="n")
)
cell_index = np.where(n_premises_cell["n"].to_numpy() > 0)[0]


# 8. outbreak data at the first detection
# create simulation directories
detection_dir = Path("03_outbreak_detection")
detection_dir.mkdir(parents=True, exist_ok=True)

# import user defined functions
sys.path.insert(0, str(Path("../..").resolve())) # add simulator_path
from simulator.premises import Premises

# create Premises objects
properties = approx_dat_to_properties(dat, approx_dat, seed=123)

# save as pickle
output_file = detection_dir / "properties_03_outbreak_detection"

with open(output_file, "wb") as f:
    pickle.dump(properties, f, protocol=pickle.HIGHEST_PROTOCOL)


# 9. save setup file
setup = {
    # configuration and data
    "config": config,
    "priors": priors,
    "dat": dat,
    "dat_today": dat_today,
    "approx_dat": approx_dat,
    "date_format": date_format,
    "time": time,

    # simulation settings
    "scenario": scenario,
    "N_particles": N_particles,
    "n_cpus": n_cpus,
    "G": G,
    "t_max": t_max,
    "t_start": t_start,
    "t_end": t_end,
    "t_detect": t_detect,
    "t_today": t_today,
    "date0": date0,

    # previous simulation settings
    "previous_t_point": previous_t_point,
    "previous_t_diff": previous_t_diff,
    "previous_DDD": previous_DDD,
    "previous_vaccine": previous_vaccine,
    "previous_policy": previous_policy,
    "xrange": xrange,
    "yrange": yrange,
    "epsg": epsg,
    "forecast_policy": forecast_policy,

    # disease assumptions
    "incubation_mode": incubation_mode,
    "incubation_max": incubation_max,
    "latent_mode": latent_mode,
    "latent_max": latent_max,
    "incubation_params": incubation_params,
    "latent_params": latent_params,

    # tolerance
    "temporal_tolerance_daily": temporal_tolerance_daily,
    "epsilon_temporal": epsilon_temporal,
    "epsilon_spatial": epsilon_spatial,
    "cell_reso": cell_reso,

    # parameters
    "para_names": para_names,
    "paras_index": paras_index,
    "paras_index_ratio": paras_index_ratio,
    "paras_index_unif": paras_index_unif,
    "paras_fixed": paras_fixed,
    "lm_low": lm_low,
    "lm_upp": lm_upp,
    "fixed_vals": fixed_vals,

    # temporal targets
    "t_range": t_range,
    "target_temporal": target_temporal,

    # spatial targets
    "x_min": x_min,
    "x_max": x_max,
    "y_min": y_min,
    "y_max": y_max,
    "x_breaks": x_breaks,
    "y_breaks": y_breaks,
    "all_cells": all_cells,
    "target_spatial": target_spatial,
    "n_premises_cell": n_premises_cell,
    "cell_index": cell_index,

    # Distance matrix
    "distmat": distmat
}

# save setup
setup_path = (out_dir / "abc.setup.joblib").resolve()
joblib.dump(setup, setup_path, compress=0)

# save setup path
(out_dir / "abc.setup.file.txt").write_text(str(setup_path))

# initialise generation
(out_dir / "g.txt").write_text("1")


### require top make diseaseoutbreak pickle obj.
### but for now, I'm going to copy and paste pickle objs for simulation
import shutil
source_dir = Path("../../scenarios/hpai/v06_NSW_123/03_outbreak_detection")

files_to_copy = [
    "properties_03_outbreak_detection",
    "outbreakobject_03_outbreak_detection"
]

detection_dir.mkdir(parents=True, exist_ok=True)

for filename in files_to_copy:
    shutil.copy2(
        source_dir / filename,
        detection_dir / filename
    )

### copy approx_known_data and paste to template folder
shutil.copy2(
    approx_dat_path,
    detection_dir / "approx_known_data_03_outbreak_detection.csv"
)

print("done")