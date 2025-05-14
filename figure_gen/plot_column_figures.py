import os
import pickle
import datetime as dt
import sys
from pathlib import Path

sys.path.append(os.path.join(Path(__file__).parent.parent))

import click
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from simulator.premises import convert_time_to_date


def plot_time_series_columns(
        x_data,
        y_data,
        x_label=None,
        y_label=None,
        title=None,
        legend=None,
        save=False,
        folder_path="figures",
        save_name=None,
        max_x_ticks=5,
        max_y_ticks=5,
        **kwargs
):
    # Check maximum values along each axis
    x_scale = len(x_data)
    if y_data.ndim == 1:
        y_scale = max(y_data)
    else:
        y_scale = max(y_data.sum(axis=0))

    # Space out x and y ticks accordingly
    if x_scale <= 21:
        x_spacing = 2
    else:
        x_spacing = int(7 * np.ceil((x_scale / max_x_ticks) / 7))  # np.pow(2, int(np.floor(nx / 21) - 1))

    if y_scale <= 5:
        y_spacing = 1
    else:
        y_spacing = int(5 * np.ceil((y_scale / max_y_ticks) / 5))

    x_ticks = list(range(x_scale))
    x_tick_labels = [
        convert_time_to_date(x, dt.datetime(year=2026, month=3, day=9), "%d/%m")
        for x in x_ticks[::x_spacing]
    ]

    # Set up figure
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    ax.grid(zorder=0)

    # Plot (either stacked or single)
    if type(y_data) == np.ndarray and y_data.ndim > 1:
        # TODO: define colormap
        bottom = np.zeros(len(y_data[0]))
        for ii in range(len(y_data)):
            ax.bar(x_data, y_data[ii], zorder=3, bottom=bottom, **kwargs)
            bottom += y_data[ii]
    else:
        ax.bar(x_data, y_data, color="#666", zorder=3, **kwargs)

    ax.set_xticks(x_ticks[::x_spacing])
    ax.set_yticks(np.arange(0, max(ax.get_yticks()) + y_spacing, step=y_spacing))
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=14)
    ax.set_xticklabels(x_tick_labels, fontsize=14)

    # Set axes parameters
    if x_label is not None: ax.set_xlabel(x_label, fontsize=14)
    if y_label is not None: ax.set_ylabel(y_label, fontsize=14)
    if title is not None: ax.set_title(title, fontsize=14)
    if legend is not None: ax.legend(legend, loc="upper left", fontsize=14)

    if save:
        file_name = os.path.join(folder_path, f"{save_name}.png")
        plt.tight_layout()
        plt.savefig(file_name, bbox_inches="tight")
        plt.close()
    else:
        plt.show()

    return


@click.command()
@click.argument("filename", type=click.Path(exists=True))
def main(filename):
    print(os.getcwd())
    try:
        print(f"Attempting to load properties information from {filename} ... ", end="")
        with open(filename, "rb") as file:
            properties = pickle.load(file)
        print("done.")
    except Exception as e:
        print("failed.")
        raise e

    folder = f"figures_{os.path.basename(filename).split(".")[0]}"
    os.makedirs(folder, exist_ok=True)

    # Get relevant data into a DataFrame
    print("Plotting column graphs... ", end="")
    ids = [ii.id for ii in properties if ii.notification_date != "NA"]
    states_list = [ii.address["state"] for ii in properties if ii.notification_date != "NA"]
    notification_list = [ii.notification_date for ii in properties if ii.notification_date != "NA"]
    date_series = pd.to_datetime(notification_list)
    start_date = pd.to_datetime("2026-03-09")
    days_from_start = (date_series - start_date).days
    df = pd.DataFrame(
        {
            "property_id": ids,
            "state": states_list,
            "notification_date": date_series,
            "days_from_start": days_from_start,
        }
    )

    # Filter and plot at state level
    bins = np.arange(-0.5, max(days_from_start) + 1.5, step=1)
    x_values = bins[1:] - 0.5
    separate_by = "state"
    unique_labels = sorted(df[separate_by].unique())
    for ii, state in enumerate(unique_labels):
        data = df[df[separate_by] == state]["days_from_start"]
        counts, _ = np.histogram(data, bins=bins)

        plot_time_series_columns(
            x_values,
            counts,
            "Date",
            "Daily confirmed infected premises",
            legend=[state],
            save=True,
            folder_path=folder,
            save_name=f"daily_state_{state.lower().replace(" ", "_")}",
        )

        plot_time_series_columns(
            x_values,
            counts.cumsum(),
            "Date",
            "Total confirmed infected premises",
            legend=[state],
            save=True,
            folder_path=folder,
            save_name=f"total_state_{state.lower().replace(" ", "_")}",
        )

        if ii == 0:
            all_counts = counts
        else:
            all_counts = np.vstack([all_counts, counts])

    # Plot Australia-wide
    plot_time_series_columns(
        x_values,
        all_counts,
        "Date",
        "Daily confirmed infected premises",
        legend=unique_labels,
        save=True,
        folder_path=folder,
        save_name=f"daily_all_stacked",
    )
    plot_time_series_columns(
        x_values,
        all_counts.sum(axis=0),
        "Date",
        "Daily confirmed infected premises",
        legend=["Australia"],
        save=True,
        folder_path=folder,
        save_name=f"daily_all_combined",
    )
    plot_time_series_columns(
        x_values,
        all_counts.cumsum(axis=1),
        "Date",
        "Total confirmed infected premises",
        legend=unique_labels,
        save=True,
        folder_path=folder,
        save_name=f"total_all_stacked",
    )
    plot_time_series_columns(
        x_values,
        all_counts.sum(axis=0).cumsum(),
        "Date",
        "Total confirmed infected premises",
        legend=["Australia"],
        save=True,
        folder_path=folder,
        save_name=f"total_all_combined",
    )
    print("done.")


if __name__ == "__main__":
    """
    This file uses the click library and can be run from the command line.
    Provide a path to the pickle file which is part of the simulation output.
    
    Usage: 
        python3 plot_column_figures.py FILENAME
    
    Outputs:
        several PNGs  in directory "figures_FILENAME"
    """
    main()
