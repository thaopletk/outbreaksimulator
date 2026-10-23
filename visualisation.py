#------ required packages ------
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

#------ please set your working directory here ------
workdir = Path(__file__).resolve().parent
folder_name = "config_HPAI"
gmax0 = 8
plot_y_max = 20

#------ auto from here ------
#------ required functions ------
import visualisation_function

#------ load all generations ------
base_dir = workdir / "abc_output" / folder_name / "Out"
simdat = {}
output_dir = workdir / "forecast_outputs" / folder_name
output_dir.mkdir(parents=True, exist_ok=True)

for g in range(1, gmax0+1):
    file = base_dir / f"abc.g{g}.postclust.joblib"

    if file.exists():
        simdat[g] = joblib.load(file)
        print(f"Generation {g}: {simdat[g]['N_particles']} particles")
    else:
        print(f"Generation {g}: file not found")

gmax = max(simdat)
latest = simdat[gmax]

print("Latest generation:", gmax)
print("Available variables:", latest.keys())

#------ load master setup ------
setup_file = base_dir / "abc.setup.joblib"
setup = joblib.load(setup_file)

today_temporal = visualisation_function.prep_obs(
    dat=setup["dat_today"],
    t1=setup["t_start"],
    t2=setup["t_today"]
)

#------ descriptive analysis ------
IP_incidence = latest["sim_temp_all"]
summ_pred = visualisation_function.predicted_table(sim_data=IP_incidence, t_start=setup["t_start"])
print(summ_pred)

#------ epidemic curve ------
if plot_y_max is None:
    plot_y_max = np.ceil(today_temporal["E"].max() / 5) * 5 * 2

fig_epicurve, ax = visualisation_function.predicted_epicurve(sim_data=IP_incidence, target_data=today_temporal,
                                                             t_start=setup["t_start"], t_detect=setup["t_detect"], t_today=setup["t_today"],
                                                             sma_interval=1, plot_ylim=True, ylim=(0, plot_y_max), lw=1, axes_text_size=20,
                                                             policy=setup["previous_policy"], t_point=setup["previous_t_point"])
fig_epicurve.savefig(output_dir / "epicurve.png", dpi=600, bbox_inches="tight", facecolor="white")

# The CrI coincided with the median. It is possible that the same results would have been obtained even if the parameters had been varied.
sim = np.asarray(simdat[gmax]["sim_temp_all"], dtype=float)
cri_summary = pd.DataFrame({
    "day": np.arange(setup["t_start"], setup["t_start"] + sim.shape[1]),
    "median": np.median(sim, axis=0),
    "lower50": np.quantile(sim, 0.25, axis=0),
    "upper50": np.quantile(sim, 0.75, axis=0),
    "lower95": np.quantile(sim, 0.025, axis=0),
    "upper95": np.quantile(sim, 0.975, axis=0)
})
print(cri_summary.to_string(index=False))

#------ outbreak map ------
fig_map, axes = plt.subplots(1, 3, figsize=(18, 7))
for ax, horizon, title in zip(
    axes,
    [7, 14, None],
    ["1-week ahead", "2-weeks ahead", "Entire forecast horizon"]
):
    visualisation_function.predicted_risk_map(
        sim_data=latest,
        dat_today=setup["dat_today"],
        t_today=setup["t_today"],
        t_max=setup["t_max"],
        horizon=horizon,
        rank_map=False, # if True, they will show quintiles results (top 20, 40, 60, 80, 100 %)
        pt_size=3,
        ax=ax,
        title=title,
        shp_path = workdir / "worldmap" / "world-administrative-boundaries.shp", # if None, they will not draw background map
        epsg = setup["epsg"]
    )

fig_map.tight_layout()
plt.show()

fig_map.savefig(output_dir / "spatial_risk_maps.png", dpi=600, bbox_inches="tight", facecolor="white")

#------ posteriors ------
fig_post, axes = visualisation_function.plot_posteriors(sim_data=latest, ncols=2, font_size=12, use_weights=True)
fig_post.savefig(output_dir / "posteior.png", dpi=600, bbox_inches="tight", facecolor="white")

#------ abc plots ------
abc, axes = visualisation_function.abc_plot(sim_data=simdat, real_data=today_temporal, ymax=plot_y_max,
                                            t_start=setup["t_start"], t_detect=setup["t_detect"], t_today=setup["t_today"],
                                            ncols=2, figsize_per_panel=(5, 3.5))
abc.savefig(output_dir / "abc_steps.png", dpi=600, bbox_inches="tight", facecolor="white")

# Running time
# Load timestamps
generations = sorted(simdat.keys())
timestamps = [datetime.fromisoformat(setup["time"])]
timestamps += [
    datetime.fromisoformat(simdat[g]["time"])
    for g in generations
]

# Calculate generation runtime in hours
runtime = np.array([
    (timestamps[i + 1] - timestamps[i]).total_seconds() / 3600
    for i in range(len(generations))
])

cumulative = np.concatenate([[0], np.cumsum(runtime)])

# Plot
fig_time, ax = plt.subplots(figsize=(12, 2.5))

colors = plt.cm.Set2(np.linspace(0, 1, len(generations)))

for i, g in enumerate(generations):

    ax.barh(y=0, width=runtime[i], left=cumulative[i],
        height=0.45, color=colors[i], edgecolor="white", linewidth=1.5)

    # Generation label
    midpoint = cumulative[i] + runtime[i] / 2

    ax.text(midpoint, 0, f"Gen {g}", ha="center",
            va="center", fontsize=11, fontweight="bold")

# X-axis: cumulative elapsed time
ax.set_xticks(cumulative)
ax.set_xticklabels([
    f"{int(t)}h {int(round((t % 1) * 60)):02d}m"
    for t in cumulative
])

ax.set_xlabel("Elapsed time", fontsize=12)
ax.set_yticks([])
ax.set_xlim(0, cumulative[-1])
ax.set_ylim(-0.4, 0.4)
ax.spines[["top", "right", "left"]].set_visible(False)
ax.tick_params(axis="x", length=0, labelsize=9)
ax.set_title(f"ABC–SMC runtime (Total: {cumulative[-1]:.2f} hours)", fontsize=13, pad=15)

fig_time.tight_layout()
plt.show()

fig_time.savefig(output_dir / "abc_runtime.png", dpi=600, bbox_inches="tight", facecolor="white")
