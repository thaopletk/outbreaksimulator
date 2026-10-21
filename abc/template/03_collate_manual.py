#%%
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
import re
from scipy.stats import norm
from datetime import datetime

# working directory
workdir = Path("C:/TK/outbreaksimulator/abc/template") #not needed for HPC
os.chdir(workdir)
out_dir = Path("Out")

# load setup
setup_file = Path((out_dir / "abc.setup.file.txt").read_text(encoding="utf-8").strip())
setup = joblib.load(setup_file)
globals().update(setup)

# load generation
g = int((out_dir / "g.txt").read_text(encoding="utf-8").strip())

if g > 1:
    previous_file = out_dir / f"abc.g{g-1}.postclust.joblib"
    previous_results = joblib.load(previous_file)
    globals().update(previous_results)
    g += 1

print("Generation:", g)

# find accepted particles
pattern = re.compile(rf"^gen_{g}_task_\d+_particle_\d+_iter_\d+\.joblib$")
particle_files = sorted(
    p for p in out_dir.iterdir()
    if p.is_file() and pattern.fullmatch(p.name)
)

print("Accepted particle files:", len(particle_files))

# limit number of particles
if len(particle_files) > N_particles:
    extra_files = particle_files[N_particles:]

    for file in extra_files:
        file.unlink()

    particle_files = particle_files[:N_particles]

# adjust particle count
N_particles = min(N_particles, len(particle_files))
print("N_particles:", N_particles)

if g == 1:
    theta_new = np.full((N_particles, len(paras_index)), np.nan)

    dist_temporal_all = np.full((N_particles, G), np.nan)
    dist_spatial_all = np.full((N_particles, G), np.nan)
    iters_all = np.full((N_particles, G), np.nan)
    seed_all = np.full((N_particles, G), np.nan)

    # particle weights
    w_old = np.full((N_particles, 1), np.nan)
    w_new = np.full((N_particles, 1), np.nan)


# estimated parameter names
estimated_names = np.asarray(para_names)[paras_index]

# initialise arrays
theta_store = np.full((N_particles, len(paras_index)), np.nan)
dist_temporal_store = np.full(N_particles, np.nan)
dist_spatial_store = np.full(N_particles, np.nan)
sim_temp_store = np.full((N_particles, len(np.arange(t_start, t_max + 1))), np.nan)
sim_t_e_store = np.full((N_particles, len(dat_today)), np.nan)
iters_store = np.full(N_particles, np.nan)
seed_store = np.full(N_particles, np.nan)
sim_ids = None

# preserve previous generation estimates
theta_old = theta_new.copy()

expected_ids = dat_today["id"].to_numpy()

for idx, file in enumerate(particle_files):

    result = joblib.load(file)

    # 1. estimated parameters
    theta_store[idx, :] = [
        float(result["paras"][name])
        for name in estimated_names
    ]

    # 2. distances
    dist_temporal_store[idx] = result["distance_temporal"]
    dist_spatial_store[idx] = result["distance_spatial"]

    # 3. temporal simulation results
    sim_temporal = result["sim_temporal"]
    sim_E = sim_temporal.set_index("t")["E"]
    sim_temp_store[idx, :] = sim_E.to_numpy(dtype=float)

    # 4. premises-level exposure times
    sim_t_e = result["sim_t_e"]
    if sim_ids is None:
        sim_ids = sim_t_e["id"].to_numpy().copy()
    sim_t_e_store[idx, :] = sim_t_e["t_e"].to_numpy(dtype=float)

    # 5. iteration and seed
    iters_store[idx] = result["k"]
    seed_store[idx] = result["seed"]

    print(
        f"{idx + 1} of {N_particles} "
        f"({(idx + 1) / N_particles * 100:.1f}%)",
        end="\r",
        flush=True
    )

# current generation estimates
theta_new = theta_store.copy()

# store distances across generations
dist_temporal_all[:N_particles, g - 1] = dist_temporal_store
dist_spatial_all[:N_particles, g - 1] = dist_spatial_store

# store current generation simulation outputs
sim_temp_all = sim_temp_store.copy()
sim_t_e_all = sim_t_e_store.copy()

# store iteration and seed information
iters_all[:N_particles, g - 1] = iters_store
seed_all[:N_particles, g - 1] = seed_store

# remove temporary variables
temp_vars = ["theta_store", "dist_temporal_store", "dist_spatial_store", "sim_temp_store",
    "sim_t_e_store", "iters_store", "seed_store", "k"]
for var in temp_vars:
    globals().pop(var, None)

# update particle weights
theta_new = np.asarray(theta_new, dtype=float)

if g == 1:
    w_new = np.full(N_particles, 1.0 / N_particles)
else:
    # theta_new = np.asarray(theta_new, dtype=float)
    theta_old = np.asarray(theta_old, dtype=float)
    w_old = np.asarray(w_old, dtype=float).ravel()
    tau_var_old = np.asarray(tau_var_old, dtype=float).ravel()
    n_params = len(paras_index)

    # transform ratio-scale parameters to log10 scale
    ratio_mask = np.isin(paras_index, paras_index_ratio)    
    theta_new_trans = theta_new.copy()
    theta_old_trans = theta_old.copy()
    if ratio_mask.any():
        theta_new_trans[:, ratio_mask] = np.log10(theta_new[:, ratio_mask])
        theta_old_trans[:, ratio_mask] = np.log10(theta_old[:, ratio_mask])

    # prior probability (normalised uniform density)
    prior_valid = (
        (theta_new_trans >= np.asarray(lm_low))
        & (theta_new_trans <= np.asarray(lm_upp))
    ).all(axis=1)

    # Calculate unnormalised weights
    w_new = np.zeros(N_particles, dtype=float)
    
    for np_idx in range(N_particles):
    
        # Numerator
        # Since uniform prior densities are normalised, the numerator (w1) equals 1,
        # when all estimated parameters fall within their respective prior bounds.
        w1 = float(prior_valid[np_idx])

        # Denominator
        w2_components = np.zeros(n_params, dtype=float)

        for a in range(n_params):
            z = (theta_new_trans[np_idx, a] - theta_old_trans[:, a]) / np.sqrt(2 * tau_var_old)[a]
            w2_components[a] = np.sum(w_old * norm.pdf(z))

        w2 = np.sum(w2_components)

        w_new[np_idx] = w1 / w2

        print(
            f"weight calculations: {np_idx + 1} of {N_particles} "
            f"({(np_idx + 1) / N_particles * 100:.1f}%)",
            end="\r",
            flush=True
        )

# update theta and normalise weights
theta_old = theta_new.copy()
w_old = w_new / np.sum(w_new)

# identify ratio-scale parameters
ratio_mask = np.isin(paras_index, paras_index_ratio)
theta_trans = theta_old.copy()
if ratio_mask.any():
    theta_trans[:, ratio_mask] = np.log10(theta_old[:, ratio_mask])

# weighted empirical mean
tau_mu_old = np.sum(theta_trans * w_old[:, None], axis=0)

# weighted empirical variance
tau_var_old = np.sum(
    w_old[:, None] * (theta_trans - tau_mu_old) ** 2,
    axis=0
) / ((N_particles - 1) / N_particles)

# clean up temporary variables
for var in ["dat", "dat_today"]:
    globals().pop(var, None)

# record completion time
time = datetime.now().astimezone().isoformat(timespec="seconds")

# save generation results
postclust_results = {
    **setup,
    "g": g,
    "time": time,
    "N_particles": N_particles,

    # parameters and weights
    "theta_new": theta_new,
    "theta_old": theta_old,
    "w_new": w_new,
    "w_old": w_old,
    "tau_mu_old": tau_mu_old,
    "tau_var_old": tau_var_old,

    # distances
    "dist_temporal_all": dist_temporal_all,
    "dist_spatial_all": dist_spatial_all,

    # simulation results
    "sim_temp_all": sim_temp_all,
    "sim_t_e_all": sim_t_e_all,
    "sim_ids": sim_ids,

    # iterations and seeds
    "iters_all": iters_all,
    "seed_all": seed_all
}

output_file = out_dir / f"abc.g{g}.postclust.joblib"
joblib.dump(postclust_results, output_file)
print("Saved:", output_file)

# increment generation
g += 1
(out_dir / "g.txt").write_text(str(g), encoding="utf-8")
