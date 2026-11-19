from pathlib import Path
import argparse
import sys
import numpy as np
import pandas as pd
import yaml
import joblib
import pickle
import itertools
import os

from pyproj import Transformer
from scipy.spatial.distance import pdist, squareform
from scipy.stats import gamma
from datetime import datetime
from types import SimpleNamespace
from shapely.geometry import Polygon
from scipy.spatial import cKDTree
from geopy.location import Location
import geopandas as gpd
from pyproj import Geod
from shapely.affinity import translate

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

# outbreakobject pickle
def create_outbreak_pickle(
    start_date,
    current_date,
    para_names,
    prior_values,
    folder_path="",
    unique_output="",
    movement_dat="",
    xrange="", 
    yrange="",
    job_manager="",
    vax_modifier=""
):

    def parse_date(value):
        if isinstance(value, datetime):
            return value
        return datetime.strptime(value, "%d/%m/%Y")

    start = parse_date(start_date)
    current = parse_date(current_date)
    parameters = dict(zip(para_names, prior_values))

    # disease_parameters
    chicken_keys = [
        "beta_wind",
        "beta_animal",
        "latent_period",
        "infectious_period",
        "preclinical_period",
    ]

    chicken_parameters = {
        key: float(parameters[key])
        for key in chicken_keys
    }

    outbreak = SimpleNamespace(
        time=(current.date() - start.date()).days,

        movement_records=movement_dat,

        disease_parameters={"chicken": chicken_parameters.copy()},
        beta_wind={"chicken": chicken_parameters["beta_wind"]},
        beta_animal={"chicken": chicken_parameters["beta_animal"]},
        latent_period={"chicken": chicken_parameters["latent_period"]},
        infectious_period={"chicken": chicken_parameters["infectious_period"]},
        preclinical_period={"chicken": chicken_parameters["preclinical_period"]},

        r_wind=float(parameters["r_wind"]),
        clinical_reporting_threshold=float(parameters["clinical_reporting_threshold"]),
        prob_report=float(parameters["prob_report"]),
        prob_report_commercial=float(parameters["prob_report_commercial"]),
        prob_report_backyard=float(parameters["prob_report_backyard"]),
        vax_modifier=vax_modifier,

        combined_narrative=[],
        xlims=xrange,
        ylims=yrange,
        plotting=True,
        folder_path=str(folder_path),
        unique_output=str(unique_output),
        
        job_manager=job_manager,
        total_culled_animals=0,
        controlzone={},
        contacts_for_plotting={},
        daily_statistics={},
        first_detection_day=(current.date() - start.date()).days,
        case_id_counter=1,
        notified_iter=itertools.count(1),

        start_year=start.year,
        start_month=start.month,
        start_day=start.day,
        start_date=start,
    )
    
    obj = DiseaseSimulation.__new__(DiseaseSimulation)
    obj.__dict__.update(vars(outbreak))
    return obj

# Premises pickle
def merge_dat_approx(dat, approx_known_dat, tolerance=1e-5, seed=123):
    
    dat = dat.copy().reset_index(drop=True)
    approx_known_dat = approx_known_dat.copy().reset_index(drop=True)
    rng = np.random.default_rng(seed)
    
    # known data
    approx_known_dat["known_sheds"] = approx_known_dat["sheds"].copy()
    approx_known_dat["known_area"] = approx_known_dat["area"].copy()
    approx_known_dat["known_birds"] = approx_known_dat["total_chickens"].copy()

    # Coordinate matching
    dat_coords = dat[["longitude", "latitude"]].to_numpy(dtype=float)
    approx_coords = approx_known_dat[["xcoord", "ycoord"]].to_numpy(dtype=float)
    tree = cKDTree(approx_coords)
    matches = tree.query_ball_point(dat_coords, r=tolerance, p=np.inf)

    # Avoid ambiguous matches
    if any(len(m) > 1 for m in matches):
        raise ValueError("Multiple approx_known_dat rows match the same coordinates")

    indices = [m[0] if m else -1 for m in matches]
    matched_indices = [i for i in indices if i >= 0]
    
    if len(matched_indices) != len(set(matched_indices)):
        raise ValueError("An approx_known_dat row matches multiple dat rows")

    # Keep dat columns when names overlap
    extra_cols = [
        col for col in approx_known_dat.columns
        if col not in dat.columns
        and col not in ["xcoord", "ycoord"]
    ]

    approx_aligned = (
        approx_known_dat.reindex(indices)[extra_cols]
        .reset_index(drop=True)
    )

    dat = pd.concat([dat, approx_aligned], axis=1)
    
    # Identify premises with both observed shed counts and chicken counts. - These complete records are used as sampling donors.
    sheds = pd.to_numeric(dat["sheds"], errors="coerce")
    chickens = pd.to_numeric(dat["total_chickens"], errors="coerce")
    donors = pd.DataFrame({"sheds": sheds, "total_chickens": chickens}).dropna()
    
    # Weighted sampling: similar values receive higher probabilities.
    def sample(value, column):
        if pd.isna(value):
            return donors.iloc[rng.integers(len(donors))]

        x = donors[column].to_numpy(float)
        weights = np.exp(-2 * abs(np.log1p(x) - np.log1p(value)))
        weights /= weights.sum()

        return donors.iloc[rng.choice(len(donors), p=weights)]
    
    result = []
    
    for i, row in dat.iterrows():
    
        s = sheds.iloc[i]
        n = chickens.iloc[i]

        # Four cases:
        # 1 Both known: preserve both.
        # 2 Only sheds known: sample chickens conditional on sheds.
        # 3 Only chickens known: sample sheds conditional on chickens.
        # 4 Both missing: use n_total as a proxy for farm size.
        if pd.isna(s) or pd.isna(n):
            if pd.notna(s):
                donor = sample(s, "sheds")
            elif pd.notna(n):
                donor = sample(n, "total_chickens")
            else:
                target = pd.to_numeric(row.get("n_total"), errors="coerce")
                donor = sample(target, "total_chickens")

            if pd.isna(s):
                s = donor["sheds"]
            if pd.isna(n):
                n = donor["total_chickens"]

        s, n = int(s), int(n)

        size = pd.to_numeric(row.get("n_total"), errors="coerce")
        size = max(int(size), 0) if pd.notna(size) else 0

        kind = str(row.get("enterprise", "")).strip().lower()

        # Approximate chickens per shed.
        approx_per_shed = int(round(n / s)) if n > 0 else None

        # Infer eggs using the original type-specific initialisation rules.
        # Direct egg observations take priority over simulated values.
        raw_eggs = pd.to_numeric(row.get("eggs", np.nan), errors="coerce")

        if pd.notna(raw_eggs):
            eggs = int(raw_eggs)
        elif "layers" in kind or "egg production" in kind or "mixed" in kind:
            eggs = (size // s) * int(rng.integers(0, s))
        elif kind == "breeder":
            eggs = 12000 * int(rng.integers(0, s))
        elif kind == "backyard" or "other" in kind:
            eggs = int(rng.integers(0, size)) if size > 0 else 0
        else:
            eggs = 0

        result.append((s, n, approx_per_shed, eggs))

    # Store estimates without overwriting original observations.
    dat[["num_sheds_inferred", "total_chicken_inferred", "approx_chickens_per_shed", "eggs_inferred"]] = pd.DataFrame(result, index=dat.index)
    print(f"Matched rows: {len(matched_indices)}/{len(dat)}")

    return dat

def fill_lga(dat, shp_path):
    dat = dat.copy().reset_index(drop=True)

    # Load LGA shapefile
    lga = gpd.read_file(shp_path)

    # Farm coordinates (longitude, latitude)
    farms = gpd.GeoDataFrame(
        dat[["longitude", "latitude"]].copy(),
        geometry=gpd.points_from_xy(dat["longitude"], dat["latitude"]),
        crs="EPSG:4326"
    )

    # Match coordinate systems
    farms = farms.to_crs(lga.crs)

    # Spatial join
    matched = gpd.sjoin(farms, lga[["LGA_NAME25", "geometry"]], how="left", predicate="within")

    # Ensure one LGA per farm
    if matched.index.duplicated().any():
        raise ValueError("Multiple LGAs matched to a single farm")

    # Fill missing LGA values only
    if "LGA" not in dat.columns:
        dat["LGA"] = pd.NA

    dat["LGA"] = dat["LGA"].fillna(matched["LGA_NAME25"].reindex(dat.index))

    return dat

def calculate_spatial_attributes(properties, epsg="EPSG:3577", max_distance=6, radius_km=5):
    
    # Convert longitude/latitude to projected coordinates (km)
    transformer = Transformer.from_crs("EPSG:4326", epsg, always_xy=True)
    lon = np.array([p.coordinates[0] for p in properties])
    lat = np.array([p.coordinates[1] for p in properties])
    x, y = transformer.transform(lon, lat)
    coords_km = np.column_stack([x, y]) / 1000

    # Build spatial index
    tree = cKDTree(coords_km)

    for i, p in enumerate(properties):

        # 1. Neighbourhood and total_neighbours
        indices = tree.query_ball_point(coords_km[i], r=max_distance)

        neighbours = [
            [int(j), float(np.linalg.norm(coords_km[i] - coords_km[j]))]
            for j in indices if i != j
        ]

        neighbours.sort(key=lambda item: item[0])

        p.neighbourhood = neighbours
        p.total_neighbours = len(neighbours)

        # 2. Puffed polygon and area
        # TODO: Replace the centre-distance criterion with the original polygon intersection method.
        # The original simulator also uses Haversine distances.
        polygon_coords = geodesic_point_buffer(lat[i], lon[i], radius_km)
        p.puffed_poly = Polygon(polygon_coords)
        p.puffed_poly_area = calculate_area(p.puffed_poly)

    return properties

def initialise_movement_attributes(properties, movement_dat):
    # Reconstruct movement_neighbours and allowed_movement_details
    # using observed movement records from movement_dat.
    
    MOVEMENT_TYPES = [
        "layers free-range", "layers caged", "layers barn",
        "broiler farm", "pullet farm", "egg processing",
        "abbatoir", "hatchery", "breeder", "backyard"
    ]

    # Initialise movement-related attributes.
    for p in properties:
        p.movement_neighbours = {t: [] for t in MOVEMENT_TYPES}
        p.allowed_movement_details = {}

    # Map premises IDs to list indices.
    id_to_index = {
        int(p.id): i for i, p in enumerate(properties)
    }

    # Restore observed directed movements.
    for _, row in movement_dat.iterrows():

        source_id = int(row["from"])
        target_id = int(row["to"])
        target_type = row["facility_type_2"]

        if source_id not in id_to_index or target_id not in id_to_index:
            continue

        if target_type not in MOVEMENT_TYPES:
            continue

        source_idx = id_to_index[source_id]
        target_idx = id_to_index[target_id]

        source = properties[source_idx]

        # Preserve observed movement direction.
        neighbours = source.movement_neighbours[target_type]

        if target_idx not in neighbours:
            neighbours.append(target_idx)

        # Record observed destinations by transported entity.
        entity = str(row["entity"]).strip().lower()
        entity = {"chicken": "chickens", "egg": "eggs"}.get(entity)

        if entity is None:
            continue

        if entity not in source.allowed_movement_details:
            source.allowed_movement_details[entity] = {
                "property_types": [],
                "properties": []
            }

        details = source.allowed_movement_details[entity]

        if target_type not in details["property_types"]:
            details["property_types"].append(target_type)

        if target_idx not in details["properties"]:
            details["properties"].append(target_idx)

    return properties

def create_rectangle_polygon(lon, lat, area, aspect_ratio=2.0):
    
    geod = Geod(ellps="WGS84")

    area_m2 = area * 10000 # Area (ha -> m²)
    width = np.sqrt(area_m2 / aspect_ratio)
    height = width * aspect_ratio

    corners = []

    for east, north in [
        (-width / 2, -height / 2),
        ( width / 2, -height / 2),
        ( width / 2,  height / 2),
        (-width / 2,  height / 2)
    ]:
        azimuth = np.degrees(np.arctan2(east, north))
        distance = np.hypot(east, north)

        x, y, _ = geod.fwd(lon, lat, azimuth, distance)
        corners.append((x, y))

    return Polygon(corners)

def estimate_area_polygon(dat, LGA_path, seed=123):

    dat = dat.copy()

    # Read LGA boundaries
    lga_gdf = gpd.read_file(LGA_path).to_crs("EPSG:4326")
    lga_regions = dict(zip(lga_gdf["LGA_NAME25"], lga_gdf.geometry))

    polygons = {}

    # 1. Premises with known area
    known = dat["area"].notna()

    for idx, row in dat.loc[known].iterrows():

        polygons[idx] = create_rectangle_polygon(
            lon=row["longitude"],
            lat=row["latitude"],
            area=row["area"],
            aspect_ratio=2.0
        )

    # 2. Premises with missing area
    missing = dat["area"].isna()

    np.random.seed(seed)

    for lga, group in dat.loc[missing].groupby("LGA"):

        region = lga_regions[lga]

        # Reuse original simulator function
        coords, generated_polygons, generated_areas = (
            assign_property_locations_in_region(
                n=len(group),
                region=region,
                average_property_ha=50,
                excluded_regions=[]
            )
        )

        for (idx, row), poly in zip(group.iterrows(), generated_polygons):
            
            # Move polygon to the existing premises coordinates
            polygon = translate(poly, xoff=row["longitude"] - poly.centroid.x, yoff=row["latitude"] - poly.centroid.y)
            polygons[idx] = polygon

            # Recalculate area at the destination coordinates
            dat.at[idx, "area"] = calculate_area(polygon)

    # Store polygons
    dat["polygon"] = None

    for idx, polygon in polygons.items():
        dat.at[idx, "polygon"] = polygon

    return dat


def create_property_pickle(dat, approx_known_dat, movement_dat, LGA_path=None):

    # 1. Merge datasets using farm coordinates and identify LGAs.
    dat = merge_dat_approx(dat, approx_known_dat)
    
    if LGA_path is not None:
        dat = fill_lga(dat, shp_path=LGA_path)
    
    # 2. Preserve known farm areas and use the original simulator function
    # to generate missing 'area's and rectangular polygons (re-centered)
    dat = estimate_area_polygon(dat, LGA_path=LGA_path, seed=123)
    
    properties = []
    
    rng = np.random.default_rng(123)
    cutoff = pd.to_datetime(approx_known_dat["self_report_date"], dayfirst=True, errors="coerce").min()

    for i, row in dat.iterrows():

        # 3. Create a Premises object without calling the original constructor.
        p = Premises.__new__(Premises)

        # 4. Initialise attributes that have identical values across all premises.
        p.__dict__.update({

            "radius": None,
            "animals": [],
            "vaccination_status": 0,
            "culled_status": 0,
            "vaccinate_delay": 0,
            "cull_delay": 0,
            "movement_start_day": 0,
            "animal_type": "chicken",
            "reported_status": False,
            "culled_on_suspicion": False,
            "ip": "NA",
            "notification_date": "NA",
            "removal_date": "NA",
            "recovery_date": "NA",
            "vacc_date": "NA",
            "county": "NA",
            "cluster": "NA",
            "movement_probability": 0,
            "movement_prop_animals": 0,
            "movement_frequency": 1,
            "allowed_movement": {},
            "max_daily_movements": 1,
            "undergoing_testing": False,
            "day_of_last_lab_test": None,
            "chickens": None,
            "eggs_fertilised": None,
            "QLD_property_type": None,
            "FMD_extra_info": None,
            "cumulative_infections_by_animal_type": {},
            "disposed_status": 0,
            "decontaminated_status": 0,
            "disposal_date": "NA",
            "decontamination_date": "NA",
        })
        
        # 5. known data
        p.known_birds = row["known_birds"]
        p.known_area = row["known_area"]
        p.known_sheds = row["known_sheds"]
        p.sim_id = row["sim_id"]
        p.data_source = row["data_source"]
        
        # 6. Estimated while merging
        p.num_sheds = row["num_sheds_inferred"]
        p.chicken_capacity = row["total_chicken_inferred"]
        p.approx_chickens_per_shed = row["approx_chickens_per_shed"]
        p.eggs = row["eggs_inferred"]
        
        # 7. Assign farm coordinates from the merged dataset.
        x = np.float64(row["longitude"])
        y = np.float64(row["latitude"])
        p.__dict__.update({
            "coordinates": np.array([x, y], dtype=np.float64),
            "x": x,
            "y": y
        })
        
        # 8. Initialise reporting status and location attributes (address, location, state, clinical_report_outcome, status).
        self_report_date = pd.to_datetime(row.get("self_report_date"), dayfirst=True, errors="coerce")
        has_report = pd.notna(self_report_date)
        if has_report:
            # TODO: Addresses and street names need to be inferred from the x and y coordinates. 
            # G-NAF data could be used for this purpose, although the dataset is approximately 2 GB in size.
            p.address = {
                "road": "Willowdene Avenue",
                "city": "Sydney",
                "state": "New South Wales",
                "ISO3166-2-lvl4": "AU-NSW",
                "postcode": "2745",
                "country": "Australia",
                "country_code": "au"
            }
            full_address = ", ".join([p.address["road"], p.address["city"], p.address["state"], p.address["postcode"], p.address["country"]])
            p.location = Location(
                full_address,
                (y, x, 0.0), # latitude, longitude, altitude
                raw={"address": p.address}
            )
            p.state = p.address["state"]
            p.clinical_report_outcome = True
            p.status = "SP"
            p.case_created_date = self_report_date.strftime("%d/%m/%Y")
            p.custom_info = {"self_report_date": self_report_date.strftime("%d/%m/%Y")}
            p.case_id = 1
        else:
            p.location = None
            p.address = None
            p.state = None
            p.clinical_report_outcome = None
            p.status = "NA"
            p.case_created_date = None
            p.custom_info = {}
            p.case_id = None

        # 9. Assign premises ID and farm population size (id, size).
        p.id = int(i)
        p.size = row["n_total"]
        
        # 10. Assign exposure and clinical dates, excluding dates after the cutoff.
        exposure_date = pd.to_datetime(row["exposure_date"], errors="coerce")
        clinical_date = pd.to_datetime(row["clinical_date"], errors="coerce")
        p.exposure_date = (
            exposure_date.strftime("%d/%m/%Y") 
            if pd.notna(exposure_date) and exposure_date <= cutoff
            else "NA"
        )
        p.clinical_date = (
            clinical_date.strftime("%d/%m/%Y") 
            if pd.notna(clinical_date) and clinical_date <= cutoff
            else "NA"
        )
        
        # 11. Assign administrative region, premises type, and housing typ.
        # if we don't have information on premises and housing types, let them be.
        p.region = row["LGA"] if pd.notna(row.get("LGA")) else ""
        p.type = row["enterprise"] if pd.notna(row.get("enterprise")) else "" # not sure the simulator accept "" value
        p.housing_type = row["housing"] if pd.notna(row.get("housing")) else ""
        p.accepts_hatchlings = ( # Infer hatchling acceptance based on premises type and shed count.
            p.type in {"broiler farm", "pullet farm", "backyard"}
            or "Meat" in p.type
            or "Other" in p.type
            or (
                ("layers" in p.type or "Egg production" in p.type or "Mixed" in p.type)
                and p.num_sheds > 5
            )
        )

        # 12. Approximate infection-related attributes using available exposure data.
        # TODO: Replace random initialisation with a within-premises nfection model accounting for time since exposure and farm size.
        has_exposure = p.exposure_date != "NA"
        if has_exposure and p.size > 0:
            p.infection_status = 1
            p.number_infected = int(rng.integers(1, max(int(p.size), 1) + 1))
            p.cumulative_infections = p.number_infected
            p.prop_infectious = float(p.number_infected / p.size)
            p.prop_clinical = float(p.number_infected / p.size)
        else:
            p.infection_status = 0
            p.number_infected = 0
            p.cumulative_infections = 0
            p.prop_infectious = 0
            p.prop_clinical = 0

        # 13. Assign known or reconstructed farm area and polygon.
        p.area = float(row["area"])
        p.polygon = row["polygon"]
        
        # 14.  Reconstruct shed-level poultry populations.
        # Use the original simulator's age ranges for known premises types.
        # Shed populations are distributed from the current n_total (p.size).
        # These ages are synthetic, not observed outbreak-day ages.
        
        p.sheds = {}
        kind = str(p.type or "").strip().lower()
        size = int(p.size)
        s = int(p.num_sheds)
        if kind == "hatchery":
            p.sheds = {
            j: {
                "eggs": [],
                "chickens": [],
                "cleaning": False,
                "cleaning_completion": None
            }
            for j in range(1, s + 1)
        }

        elif size > 0:                
            # Define age ranges (in weeks) from Premises.init_chickens_eggs().
            if kind == "broiler farm" or "meat" in kind:
                weeks = range(1, 7)
            elif kind == "pullet farm":
                weeks = range(1, 21)
            elif "layers" in kind or "egg production" in kind or "mixed" in kind:
                weeks = range(1, 78) if s > 5 else range(20, 78)
            elif kind == "breeder":
                weeks = range(20, 78)
            elif kind == "abbatoir":
                weeks = [6]
            elif kind == "backyard" or "other" in kind:
                weeks = range(1, 71)
            else:
                weeks = None

            if weeks is not None:
            
                # Distribute chickens across sheds without losing individuals.
                birds_per_shed, remainder = divmod(size, s)

                for j in range(1, s + 1):
                
                    n = birds_per_shed + (j <= remainder)
                    age = int(rng.choice(list(weeks))) * 7

                    p.sheds[j] = {
                        "chickens": [{"n": int(n), "age": age}] if n > 0 else [],
                        "cleaning": False,
                        "cleaning_completion": None
                    }
        # For egg processing, unknown types, and other unresolvable cases,
        # leave p.sheds = {} rather than inventing an age distribution.

        properties.append(p)

    # 13. identify neighbouring premises within 6km (center-to-center distance)
    # an generate 5km circular buffers (puffed_poly) and their areas.
    properties = calculate_spatial_attributes(properties, epsg=f"EPSG:{epsg}", max_distance=6, radius_km=5)
    
    # 14. Restore movement_neighbours and allowed_movement_details from movement_dat
    movement_restored = movement_dat.copy()
    # Exclude external distributors
    movement_restored = movement_restored.loc[
        (movement_restored["from"] >= 0) & (movement_restored["to"] >= 0)].copy()
    # Keep unique directed movements
    movement_restored = movement_restored.drop_duplicates(subset=["from", "to", "facility_type_2"])
    properties = initialise_movement_attributes(properties, movement_dat = movement_restored)
    
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

movement_dat_file = config["general"]["movement_data_file"] # approx_known_data_03_outbreak_detection.csv (premises and first IP info)
movement_dat_path = (Path("../../") / movement_dat_file).resolve()
movement_dat = pd.read_csv(movement_dat_path)

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
    t_today = t_today_config
#    t_today = int(t_today_config) + t_detect # we put t_today (t_detect based; e.g., 3 weeks after t_detect)
#    if t_today > t_max:
#        raise ValueError("t_max must be bigger than (t_detect + t_today).") 
    
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
t_range = np.arange(t_start, t_today + 1) # simulation starts from day 1
# t_range = np.arange(t_detect, t_today + 1)
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
from simulator.spatial_functions import geodesic_point_buffer, calculate_area
from simulator.fixed_spatial_setup import assign_property_locations_in_region
from simulator.management import JobManager
from simulator.disease_simulation import DiseaseSimulation

# create Outbreakobject pickle
# dates
start_date = pd.to_datetime(dat_today['exposure_date'], errors='coerce').min()
start_date = start_date.strftime('%d/%m/%Y')
current_date = pd.to_datetime(approx_dat['self_report_date'], errors='coerce').min()
current_date = current_date.strftime('%d/%m/%Y')

# directories
dat_dir = os.path.dirname(approx_dat_file)
base_dir = os.path.dirname(os.path.dirname(os.getcwd()))
folder_path = os.path.join(base_dir, dat_dir)
folder_path = os.path.normpath(folder_path).replace('\\', '/')
unique_output = os.path.basename(os.path.normpath(folder_path))

# create job_manager
spatial_only_parameters = {
    "n": dat_today.shape[0]
}

job_parameters = {
    "lab_test_sensitivity": priors.loc[priors['param_name'] == 'lab_test_sensitivity', 'value'].values[0],
    "clinical_test_sensitivity": priors.loc[priors['param_name'] == 'clinical_test_sensitivity', 'value'].values[0],
    "cull_delay": priors.loc[priors['param_name'] == 'cull_delay', 'value'].values[0],
    "contact_tracing_delay": priors.loc[priors['param_name'] == 'contact_tracing_delay', 'value'].values[0],
    "lab_test_delay": priors.loc[priors['param_name'] == 'lab_test_delay', 'value'].values[0],
    "clinical_delay": priors.loc[priors['param_name'] == 'clinical_delay', 'value'].values[0],
}

job_manager = JobManager(spatial_only_parameters["n"], **job_parameters)

outbreak = create_outbreak_pickle(
    start_date=start_date,
    current_date=current_date,
    para_names=para_names,
    prior_values=priors["value"].to_numpy(),
    folder_path=folder_path,
    unique_output=unique_output,
    movement_dat=movement_dat,
    xrange=xrange, 
    yrange=yrange,
    job_manager=job_manager,
    vax_modifier=0.6
)

output_file = detection_dir / f"outbreakobject_{unique_output}"

with open(output_file, "wb") as f:
    pickle.dump(outbreak, f, protocol=pickle.HIGHEST_PROTOCOL)

# create Premises objects
LGA_path = Path("../../worldmap/LGA_2025_AUST_GDA2020.shp")
properties =  create_property_pickle(dat=dat_today, approx_known_dat=approx_dat,
                                     movement_dat = movement_dat, LGA_path = LGA_path)

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
# source_dir = Path("../../scenarios/hpai/v06_NSW_123/03_outbreak_detection")
# 
# files_to_copy = [
#     "properties_03_outbreak_detection",
#     "outbreakobject_03_outbreak_detection"
# ]
# 
# detection_dir.mkdir(parents=True, exist_ok=True)
# 
# for filename in files_to_copy:
#     shutil.copy2(
#         source_dir / filename,
#         detection_dir / filename
#     )

### copy approx_known_data and paste to template folder
shutil.copy2(
    approx_dat_path,
    detection_dir / "approx_known_data_03_outbreak_detection.csv"
)

print("done")