import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import math
import geopandas as gpd

from scipy.stats import gaussian_kde
from shapely.geometry import box
from shapely import affinity
from matplotlib.ticker import MaxNLocator
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.lines import Line2D

def prep_obs(dat, t1=1, t2=100):    
    
    days = np.arange(t1, t2 + 1)

    columns = {
        "E": "t_e",
        "I": "t_i",
        "C": "t_c",
        "N": "t_n",
        "R": "t_r",
        "D": "t_d",
        "V": "t_v"
    }

    output = pd.DataFrame({"t": days})

    for name, col in columns.items():
        output[name] = (
            pd.to_numeric(dat[col], errors="coerce")
            .value_counts()
            .reindex(days, fill_value=0)
            .to_numpy(dtype=int)
        )

    return output

def predicted_table(sim_data, real_data=None, t_start=1):
    
    # Particle x day matrix
    sim = np.asarray(sim_data, dtype=float)
    days = np.arange(t_start, t_start + sim.shape[1])

    # Summary statistics for each particle
    final_size = np.sum(sim, axis=1)
    peak_n = np.max(sim, axis=1)

    # First day with maximum incidence
    peak_t = days[np.argmax(sim, axis=1)]

    # Last day with non-zero incidence
    duration = np.array([
        days[np.where(row != 0)[0][-1]]
        if np.any(row != 0) else np.nan
        for row in sim
    ])

    def summarise(values):
        return (
            f"{np.nanmedian(values):.0f} "
            f"({np.nanquantile(values, 0.025):.0f}, "
            f"{np.nanquantile(values, 0.975):.0f})"
        )

    result = pd.DataFrame({
        "Predicted": [
            summarise(final_size),
            summarise(peak_t),
            summarise(peak_n),
            summarise(duration)
        ]
    }, index=["final_size", "peak_t", "peak_n", "duration"])

    if real_data is not None:
        observed = real_data["E"].to_numpy()
        observed_days = real_data["t"].to_numpy()

        result["Observed"] = [
            int(observed.sum()),
            int(observed_days[np.argmax(observed)]),
            int(observed.max()),
            int(observed_days[np.where(observed != 0)[0][-1]])
            if np.any(observed != 0) else np.nan
        ]

    return result

def predicted_epicurve(sim_data, real_data=None, target_data=None,
                       t_start=1, t_detect=0, t_today=21, sma_interval=1,
                       plot_ylim=True, ylim=(0, 100), lw=1, axes_text_size=16,
                       policy=None, t_point=None):

    sim = np.asarray(sim_data, dtype=float)
    days = np.arange(t_start, t_start + sim.shape[1])

    # Credible intervals
    median = np.median(sim, axis=0)
    lower95 = np.quantile(sim, 0.025, axis=0)
    upper95 = np.quantile(sim, 0.975, axis=0)
    lower50 = np.quantile(sim, 0.25, axis=0)
    upper50 = np.quantile(sim, 0.75, axis=0)

    # Fitted and forecast periods
    fitted = (days >= t_detect) & (days <= t_today)
    forecast = (days >= t_today)

    fig, ax = plt.subplots(figsize=(15, 11))

    # Fitted credible intervals
    ax.fill_between(days[fitted], lower95[fitted], upper95[fitted],
                    color="lightsteelblue", alpha=0.2, label="95% (fitted)")
    ax.fill_between(days[fitted], lower50[fitted], upper50[fitted],
                    color="lightsteelblue", alpha=0.45, label="50% (fitted)")

    # Forecast credible intervals
    ax.fill_between(days[forecast], lower95[forecast], upper95[forecast],
                    color="tomato", alpha=0.2, label="95% (forecast)")
    ax.fill_between(days[forecast], lower50[forecast], upper50[forecast],
                    color="tomato", alpha=0.4, label="50% (forecast)")

    # Complete observed data
    if real_data is not None:
        real = real_data.copy()
        real["sma"] = real["E"].rolling(window=sma_interval, center=True).mean()
        ax.plot(real["t"], real["sma"],
                color="black", linewidth=lw * 1.25, label="Observed")

    # Target observations
    if target_data is not None:
        target = target_data.copy()
        target["sma"] = target["E"].rolling(window=sma_interval, center=True).mean()
        ax.plot(target["t"], target["sma"],
                color="goldenrod",  alpha=0.5, linewidth=lw * 1.1, label="Reported")

    # Vertical boundaries
    ax.axvline(t_detect, color="steelblue", linewidth=lw)
    ax.axvline(t_today, color="steelblue", linewidth=lw)

    # Axes
    ax.set_xlim(0, days[-1])

    if plot_ylim:
        ax.set_ylim(*ylim)
    else:
        ax.set_ylim(0, np.ceil(np.max(upper95) / 10) * 10)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    
    # Display policies above the plot
    if policy is not None and t_point is not None:

        if len(policy) != len(t_point):
            raise ValueError("policy and t_point must have the same length")

        # Boundaries relative to t_detect
        boundaries = [t_detect] + [t_detect + t for t in t_point]
        for i, plc in enumerate(policy):
            start = boundaries[i]
            end = boundaries[i + 1]
            midpoint = (start + end) / 2

            # Policy label
            ax.text(midpoint, 1.005, plc, transform=ax.get_xaxis_transform(),
                    ha="center", va="bottom", fontsize=axes_text_size * 0.65,
                    color="black", clip_on=False)

            # Policy boundaries
            if i > 0:
                ax.axvline(start, color="grey", linestyle=":", linewidth=0.8, alpha=0.6)

    # Weeks since detection
    ticks = np.arange(t_detect, days[-1] + 1, 14)
    ax.set_xticks(ticks)
    ax.set_xticklabels([str(i * 2) for i in range(len(ticks))])
    ax.set_xlabel("Week", fontsize=axes_text_size)
    ax.set_ylabel("Daily case incidence", fontsize=axes_text_size)

    ax.tick_params(axis="x", labelsize=axes_text_size)
    ax.tick_params(axis="y", labelsize=axes_text_size)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.25),
              ncol=3, frameon=False, fontsize=axes_text_size * 1.05)
    #fig.tight_layout()
    fig.tight_layout(rect=[0, 0.04, 1, 0.98])

    return fig, ax

def plot_posteriors(sim_data, ncols=3, figsize_per_panel=(4.5, 3.5), font_size=12, use_weights=True):

    para_names = np.asarray(sim_data["para_names"])
    paras_index = np.asarray(sim_data["paras_index"], dtype=int)
    paras_fixed = np.asarray(sim_data["paras_fixed"], dtype=int)
    paras_index_ratio = np.asarray(sim_data["paras_index_ratio"], dtype=int)

    theta = np.asarray(sim_data["theta_old"], dtype=float)
    lm_low = np.asarray(sim_data["lm_low"], dtype=float)
    lm_upp = np.asarray(sim_data["lm_upp"], dtype=float)

    # Particle weights
    if use_weights:
        weights = sim_data["w_old"]
    else:
        weights = None

    # Estimated parameters only
    plot_indices = [
        j for j, idx in enumerate(paras_index)
        if idx not in paras_fixed
    ]
    n_params = len(plot_indices)
    nrows = math.ceil(n_params / ncols)

    fig, axes = plt.subplots(
        nrows, ncols,
        figsize=(figsize_per_panel[0] * ncols, figsize_per_panel[1] * nrows)
    )

    axes = np.atleast_1d(axes).ravel()

    def weighted_quantile(values, quantiles, weights=None):
        if weights is None:
            return np.quantile(values, quantiles)

        sorter = np.argsort(values)
        values = values[sorter]
        w = weights[sorter]
        cumulative = (np.cumsum(w) - 0.5 * w) / w.sum()

        return np.interp(quantiles, cumulative, values)

    for panel, j in enumerate(plot_indices):

        ax = axes[panel]
        idx = paras_index[j]
        name = para_names[idx]
        values = theta[:, j]

        # Remove missing values
        valid = np.isfinite(values)
        values = values[valid]

        w = weights[valid] if weights is not None else None
        if w is not None:
            w = w / w.sum()

        # Median and 95% credible interval
        q025, median, q975 = weighted_quantile(values, [0.025, 0.5, 0.975], w)

        # Prior bounds
        is_ratio = idx in paras_index_ratio
        if is_ratio:
            lower = 10 ** lm_low[j]
            upper = 10 ** lm_upp[j]
        else:
            lower = lm_low[j]
            upper = lm_upp[j]

        x = np.linspace(lower, upper, 500)

        # Posterior KDE
        kde = gaussian_kde(values, weights=w)
        density = kde(x)
        ax.plot(x, density, color="darkorange", linewidth=2, label="Posterior")
        ax.fill_between(x, density, color="orange", alpha=0.25)   

        # Uniform prior density
        if is_ratio: # Log-uniform prior on original scale            
            prior_density = 1 / (x * np.log(10) * (lm_upp[j] - lm_low[j]))
        else:
            prior_density = np.full_like(x, 1 / (upper - lower))
        ax.plot(x, prior_density, color="grey", linestyle="--", linewidth=1.5, label="Prior")

        # Summary annotation
        ax.text(0.5, 0.95,
            f"Median: {median:.3g}\n"
            f"95% CrI: [{q025:.3g}, {q975:.3g}]",
            transform=ax.transAxes, ha="center", va="top", fontsize=font_size * 0.85,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.8)
        )

        ax.set_title(name, fontsize=font_size + 1)
        ax.set_xlim(lower, upper)

        if is_ratio:
            ax.set_xscale("log")

        ax.tick_params(axis="both", labelsize=font_size * 0.8)
        ax.set_yticks([])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)

    # Remove unused panels
    for ax in axes[n_params:]:
        ax.axis("off")

    # Shared legend
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, fontsize=font_size)
    fig.tight_layout(rect=[0, 0.04, 1, 1])

    return fig, axes

def abc_plot(sim_data, real_data=None, ymax=None,
             t_start=1, t_detect=0, t_today=21,
             ncols=2, figsize_per_panel=(5, 3.5)):

    generations = sorted(sim_data.keys())
    n_gen = len(generations)
    nrows = math.ceil(n_gen / ncols)

    # Determine upper bound
    if ymax is None:
        if real_data is not None:
            ymax = np.ceil(real_data["E"].max() / 50) * 50
        else:
            ymax = max(np.max(sim_data[g]["sim_temp_all"]) for g in generations)

    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(figsize_per_panel[0] * ncols, figsize_per_panel[1] * nrows),
                             squeeze=False)
    axes = axes.ravel()

    for idx, g in enumerate(generations):

        ax = axes[idx]

        # Particle x day matrix
        sim = np.asarray(sim_data[g]["sim_temp_all"], dtype=float)
        days = np.arange(t_start, t_start + sim.shape[1])

        # Plot all particle trajectories
        for particle in sim:
            ax.plot(days, particle, color="0.25", alpha=0.05, linewidth=0.8)

        # Observed epicurve
        if real_data is not None:
            ax.plot(real_data["t"], real_data["E"], color="black", linewidth=1.2)

        # Vertical boundaries
        ax.axvline(t_detect, color="skyblue", linewidth=0.8)
        ax.axvline(t_today, color="skyblue", linewidth=0.8)

        # Axis settings
        ax.set_xlim(0, days[-1])
        ax.set_ylim(0, ymax)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_title(f"Step {g}", fontsize=14)
        ax.set_xlabel("Days", fontsize=11)
        ax.set_ylabel("Daily case incidence", fontsize=11)
        ax.tick_params(axis="x")
        ax.grid(False)

    # Hide unused panels
    for ax in axes[n_gen:]:
        ax.axis("off")

    fig.tight_layout()

    return fig, axes

def predicted_risk_map(sim_data, dat_today,
                       t_today, t_max, horizon=7, rank_map=False,
                       pt_size=5, figsize=(9, 8), title=None, ax=None, 
                       shp_path=None, epsg=None):
    
    # 1. Load simulation results
    sim_t_e = np.asarray(sim_data["sim_t_e_all"], dtype=float)
    sim_ids = np.asarray(sim_data["sim_ids"])
    n_particles, n_premises = sim_t_e.shape

    if len(sim_ids) != n_premises:
        raise ValueError("sim_ids and sim_t_e_all dimensions do not match")

    if len(dat_today) != n_premises:
        raise ValueError("dat_today and sim_t_e_all dimensions do not match")

    # 2. Define forecast horizon
    if horizon is None:
        t_end = t_max
        horizon_label = "Entire forecast horizon"
    else:
        t_end = min(t_today + horizon, t_max)
        horizon_label = f"{horizon // 7}-week ahead"

    # 3. Calculate proportion of simulations with an event
    infected = ((sim_t_e > t_today) & (sim_t_e <= t_end))
    prop_inf = infected.mean(axis=0)

    # 4. Prepare map data
    dat_risk = dat_today[["id", "x_km", "y_km"]].copy().reset_index(drop=True)
    dat_risk["prop_inf"] = prop_inf
    dat_risk["previous_IP"] = (dat_today["t_e"].notna() & (dat_today["t_e"] <= t_today)).to_numpy()

    # Keep original projected coordinates
    dat_risk["x_plot"] = dat_risk["x_km"]
    dat_risk["y_plot"] = dat_risk["y_km"]
    
    # 5. Create plot
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    if title is None:
        title = f"Simulated up to: {horizon_label}"
        
    # Scatter plot extent
    xmin = dat_risk["x_plot"].min()
    xmax = dat_risk["x_plot"].max()
    ymin = dat_risk["y_plot"].min()
    ymax = dat_risk["y_plot"].max()
        
    # 6. Add shapefile background
    if shp_path is not None:
        
        if epsg is None:
            raise ValueError("epsg must be provided when shp_path is used")
        
        # Convert shapefile to the same CRS as scatter plot
        world = gpd.read_file(shp_path)
        world_projected = world.to_crs(epsg=epsg)
        
        # Convert metres to kilometres
        world_projected["geometry"] = (
            world_projected.geometry.apply(
                lambda geom: affinity.scale(geom, xfact=0.001, yfact=0.001, origin=(0, 0))
                )
            )
        
        # Clip world map to scatter plot extent
        bbox = box(xmin, ymin, xmax, ymax)
        world_clipped = world_projected.clip(bbox)

        # Plot ocean and ground
        ax.set_facecolor("aliceblue")
        world_clipped.plot(ax=ax, facecolor="whitesmoke", edgecolor="grey", linewidth=0.6, zorder=0)

    # 7. Exclude previously infected premises from risk plotting
    plot_data = dat_risk.loc[~dat_risk["previous_IP"]].copy()

    # 8. Plot predicted risk
    if rank_map:
        # Quintiles of positive probabilities
        p = plot_data["prop_inf"].to_numpy()
        positive = p[p > 0]
        groups = np.full(len(plot_data), "zero", dtype=object)

        if len(positive) > 0:
            breaks = np.quantile(positive, [0.2, 0.4, 0.6, 0.8])

            groups[(p > 0) & (p <= breaks[0])] = "0_20"
            groups[(p > breaks[0]) & (p <= breaks[1])] = "20_40"
            groups[(p > breaks[1]) & (p <= breaks[2])] = "40_60"
            groups[(p > breaks[2]) & (p <= breaks[3])] = "60_80"
            groups[p > breaks[3]] = "80_100"

        colors = {"zero": "lightgrey", "0_20": "yellow", "20_40": "gold", "40_60": "orange", "60_80": "red", "80_100": "darkred"}

        # Plot zero-risk points first
        for group, color in colors.items():       
            mask = groups == group    
            ax.scatter(plot_data.loc[mask, "x_plot"], plot_data.loc[mask, "y_plot"],
                       s=pt_size, c=color, edgecolors="none", zorder=3)

        handles = [
            Line2D([0], [0], marker="s", linestyle="", color="none", markerfacecolor=color,
                   markeredgecolor="none", markersize=8, label=label)
            for label, color in [
                ("Previously infected", "blue"),
                ("80–100%", "darkred"),
                ("60–80%", "red"),
                ("40–60%", "orange"),
                ("20–40%", "gold"),
                ("0–20%", "yellow"),
                ("Not infected", "lightgrey")
            ]
        ]

    else:
        cmap = LinearSegmentedColormap.from_list("risk", ["lightgrey", "yellow", "orange", "red", "darkred"])

        scatter = ax.scatter(plot_data["x_plot"], plot_data["y_plot"], c=plot_data["prop_inf"], cmap=cmap,
                             norm=Normalize(vmin=0, vmax=1), s=pt_size, edgecolors="none", zorder=3)
        cbar = fig.colorbar(scatter, ax=ax, shrink=0.65, fraction=0.035, pad=0.02)
        cbar.set_label("Proportion of simulations with an event", fontsize=9)
        cbar.ax.tick_params(labelsize=8)

    # 9. Plot previously infected premises in blue
    previous_IP = dat_risk.loc[dat_risk["previous_IP"]]
    ax.scatter(previous_IP["x_plot"], previous_IP["y_plot"],
               s=pt_size * 1.5, c="blue", edgecolors="none", label="Previously infected", zorder=5)
    
    # 10. Legend
    if rank_map:
        ax.legend(handles=handles, title="Simulated Risk\n(Quintile Rank)",
                  loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False)    
    else:  
        ax.legend(loc="lower left", fontsize=9, framealpha=0.8, frameon=True, markerscale=2)
    
    # 11. Formatting
    ax.set_title(title, fontsize=15)
    ax.set_xlabel("Easting (km)")
    ax.set_ylabel("Northing (km)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(False)
    # Preserve scatter plot extent
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)

    return fig, ax, dat_risk