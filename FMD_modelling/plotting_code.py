from collections import namedtuple
import numpy as np
from scipy.integrate import odeint
import matplotlib.pyplot as plt
import random as rand
from scipy.stats import hypergeom
from tqdm import tqdm
import csv
import pandas as pd
from IPython import display
import time
from pathlib import Path
from moviepy.editor import ImageSequenceClip
import os
from matplotlib.patches import Circle
from shapely.geometry import Point
from shapely.geometry import Polygon
import math


def plot_graph(properties, property_coordinates, time):
    fig, ax = plt.subplots()
    # nodes
    for index, premise in enumerate(properties):
        infectious_prop = premise.prop_infectious
        # plot neighbours using edges
        for farm in premise.neighbourhood:
            ax.plot(
                [premise.coordinates[0], property_coordinates[farm[0], 0]],
                [premise.coordinates[1], property_coordinates[farm[0], 1]],
                alpha=0.2,
                color="black",
            )

        if premise.infection_status:
            ax.scatter(premise.coordinates[0], premise.coordinates[1], color="purple", label="infected")
            circle = Circle((premise.coordinates[0], premise.coordinates[1]), premise.radius, alpha=0.5 * infectious_prop + 0.5, color="purple")
            ax.add_patch(circle)

        elif premise.culled_status:
            ax.scatter(premise.coordinates[0], premise.coordinates[1], color="red", label="culled")
            circle = Circle((premise.coordinates[0], premise.coordinates[1]), premise.radius, alpha=0.5, color="red")
            ax.add_patch(circle)

        elif premise.vaccination_status:
            ax.scatter(premise.coordinates[0], premise.coordinates[1], color="green", label="vaccinated")
            circle = Circle((premise.coordinates[0], premise.coordinates[1]), premise.radius, alpha=0.5, color="green")
            ax.add_patch(circle)

        else:
            ax.scatter(premise.coordinates[0], premise.coordinates[1], color="orange", label="susceptible")
            circle = Circle((premise.coordinates[0], premise.coordinates[1]), premise.radius, alpha=0.5, color="orange")
            ax.add_patch(circle)

    plt.title("Time = " + str(time))
    if time < 10:
        file_name = "00" + str(time) + ".jpg"
    elif time < 100:
        file_name = "0" + str(time) + ".jpg"
    else:
        file_name = str(time) + ".jpg"
    plt.savefig(file_name)
    return


def make_video():
    # current_dir = os.getcwd()
    # parent_dir = os.path.dirname(current_dir)

    image_files = [os.path.join(os.getcwd(), img) for img in sorted(os.listdir(os.getcwd())) if img.endswith(("jpg"))]

    # file_path = str(parent_dir) + "*.eps"
    fps = 1
    clip = ImageSequenceClip(image_files, fps=fps)
    output_file = "plot_video.mp4"
    clip.write_videofile(output_file)
    # ffmpeg.input(file_path, pattern_type = 'glob', framerate = 1).output('plot.mp4').run()
    return
