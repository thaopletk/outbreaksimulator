"""Fixed spatial setup

This script generates random properties (i.e. farms) across the landscape, in latitude,longitude coordinates and areas in hectares and distances in kilometers (where relevant), based on input animal type, in known hard-coded regions, and with taking in AADIS data.

"""

import os
import simulator.spatial_functions as spatial_functions
import simulator.spatial_setup as spatial_setup
from shapely.ops import transform, unary_union
import numpy as np
import simulator.random_rectangles as random_rectangles
import simulator.output as output
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, MultiPoint
import shapely.plotting
import geopandas as gpd
import contextily as ctx
from matplotlib_scalebar.scalebar import ScaleBar
import simulator.premises as premises
import time
import random
import pickle
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import pandas as pd
import csv
import math


# copied from HPAIfunctions
def rounding_entities(val):
    if val < 10:
        return val
    if val < 100:
        return math.floor(val / 5) * 5
    if val < 500:
        return math.floor(val / 50) * 50
    if val < 1000:
        return math.floor(val / 100) * 100
    if val < 10000:
        return math.floor(val / 1000) * 1000
    if val < 100000:
        return math.floor(val / 10000) * 10000
    return math.floor(val / 100000) * 100000


def less_rounding_entities(val):
    if val < 500:
        return val
    if val < 1000:
        return math.floor(val / 5) * 5
    if val < 10000:
        return math.floor(val / 10) * 10
    if val < 100000:
        return math.floor(val / 100) * 100
    if val < 1000000:
        return math.floor(val / 1000) * 1000
    return math.floor(val / 10000) * 10000


# def fixed_spatial_setup(xrange, yrange, folder_path_main, disease="FMD", AADIS=True):

#     if disease == "FMD" and AADIS == True:
#         FMD_AADIS_input_setup()
#     elif disease == "HPAI" and AADIS == False:
#         HPAI_setup(
#             xrange,
#             yrange,
#             folder_path_main,
#         )


# def FMD_AADIS_input_setup():
#     data_folder = os.path.join(os.path.dirname(__file__), "..", "data", "AADIS_derived_data")
#     pass


def assign_property_locations_in_region(n, region, average_property_ha=100, excluded_regions=None):
    """Generates n random properties (with rectangular shapes)  within the the input region

    Parameters
    ----------
    n : int
        number of properties to generate
    region : shape
        list of geometric chapes
    average_property_ha : double or int
        a rough target for the average property size, in hectares

    Returns
    -------
    property_coordinates : list
        list of coordinates of the properties (center)
    property_polygons : list of Polygons
        the list containing the properties' shapely Polygon shape
    property_areas : list
        list of sizes/areas (in hectares) of the generated properties

    """
    minx, miny, maxx, maxy = region.bounds

    excluded_regions = unary_union(excluded_regions)

    bounding_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [minx, miny],
                [maxx, miny],
                [maxx, maxy],
                [minx, maxy],
                [minx, miny],
            ]
        ],
    }

    area_in_hectares = spatial_functions.calculate_area(bounding_polygon)

    num_recs_to_generate = max(int(np.ceil(area_in_hectares / average_property_ha)), n * 20)
    num_rectangles = num_recs_to_generate  # n  # keeping all generated rectangles for now

    #  x1, y1, x2, y2
    generate_region = random_rectangles.Rect(minx, miny, maxx, maxy)
    random_recs = random_rectangles.return_random_rectangles(num_rectangles, num_recs_to_generate, generate_region)
    # the resultant rectangles could become properties

    property_coordinates = np.zeros((n, 2))
    property_polygons = []
    property_areas = []

    i_random_recs = -1
    for i in range(n):
        print(i + 1)
        inside_region = False
        while not inside_region:
            i_random_recs += 1
            if i_random_recs >= len(random_recs):
                raise Exception("Not enough generated rectangles within region!")

            rectangle = random_recs[i_random_recs]
            # make polygons
            property_polygon = {
                "type": "Polygon",
                "coordinates": [
                    [
                        [rectangle.min.x, rectangle.min.y],
                        [rectangle.max.x, rectangle.min.y],
                        [rectangle.max.x, rectangle.max.y],
                        [rectangle.min.x, rectangle.max.y],
                        [rectangle.min.x, rectangle.min.y],
                    ]
                ],
            }
            Polygon_obj = spatial_functions.convert_dict_poly_to_Polygon(property_polygon)  # Shapely Polygon object

            # check if the polygon is inside the region
            if region.contains(Polygon_obj):
                if excluded_regions == None:
                    inside_region = True
                else:
                    if excluded_regions.contains(Polygon_obj):
                        pass
                    else:
                        inside_region = True

        property_areas.append(spatial_functions.calculate_area(property_polygon))

        property_polygons.append(Polygon_obj)

        property_coordinates[i, 0] = (rectangle.min.x + rectangle.max.x) / 2
        property_coordinates[i, 1] = (rectangle.min.y + rectangle.max.y) / 2

    return property_coordinates, property_polygons, property_areas


def plot_map_land_HPAI(
    chicken_meat_property_coordinates,
    processing_chicken_meat_property_coordinates,
    chicken_egg_property_coordinates,
    processing_chicken_egg_property_coordinates,
    xlims,
    ylims,
    folder_path,
    plot_suffix="",
):
    """Plot properties"""

    chickenimage = plt.imread(os.path.join(os.path.dirname(__file__), "..", "images", "chicken.png"))
    chickenimage_box = OffsetImage(chickenimage, zoom=0.1)

    # chickenmeatimage = plt.imread(os.path.join(os.path.dirname(__file__), "..", "images", "chickenmeat.png"))
    # chickenmeatimage_box = OffsetImage(chickenmeatimage, zoom=0.03)
    chickenmeatimage = plt.imread(os.path.join(os.path.dirname(__file__), "..", "images", "factory.png"))
    chickenmeatimage_box = OffsetImage(chickenmeatimage, zoom=0.3)

    eggimage = plt.imread(os.path.join(os.path.dirname(__file__), "..", "images", "egg.png"))
    eggimage_box = OffsetImage(eggimage, zoom=0.1)

    eggcartonimage = plt.imread(os.path.join(os.path.dirname(__file__), "..", "images", "eggcarton.png"))
    eggcartonimage_box = OffsetImage(eggcartonimage, zoom=0.055)

    fig, ax = plt.subplots(1, 1, figsize=(30, 30))  # ,figsize=(10,12)

    for coordinates, marker, markerlabel in [
        [chicken_meat_property_coordinates, chickenimage_box, "Chicken Meat"],
        [chicken_egg_property_coordinates, eggimage_box, "Chicken Egg"],
        [processing_chicken_egg_property_coordinates, eggcartonimage_box, "Chicken Egg Processing"],
        [processing_chicken_meat_property_coordinates, chickenmeatimage_box, "Chicken Meat Processing"],
    ]:
        geometries = []
        # print(markerlabel)
        # print(coordinates)

        if len(coordinates) == 0:
            continue

        for long, lat in coordinates:
            curr_farm = Point(long, lat)
            geometries.append(curr_farm)

        geo_df = gpd.GeoDataFrame(geometry=geometries)
        geo_df.crs = {"init": "epsg:4326"}
        # plot the marker
        ax = geo_df.plot(ax=ax, markersize=20)

        for x, y in coordinates:
            ab = AnnotationBbox(marker, (x, y), frameon=False)
            ax.add_artist(ab)

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    ctx.add_basemap(ax, crs={"init": "epsg:4326"}, source=ctx.providers.OpenStreetMap.Mapnik)

    # https://geopandas.org/en/stable/gallery/matplotlib_scalebar.html
    points = gpd.GeoSeries([Point(-73.5, 40.5), Point(-74.5, 40.5)], crs=4326)  # Geographic WGS 84 - degrees
    points = points.to_crs(32619)  # Projected WGS 84 - meters
    distance_meters = points[0].distance(points[1])
    ax.add_artist(
        ScaleBar(
            distance_meters,
            box_alpha=0.1,
            location="lower right",
        )
    )

    ax.set_title("Map", fontsize=18)

    ax.set_ylabel("latitude", fontsize=16)
    ax.set_xlabel("longitude", fontsize=16)

    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
    #       fancybox=True, shadow=True, fontsize=18)

    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    file_name = f"property_locations_base_map{plot_suffix}.png"

    file_name = os.path.join(folder_path, file_name)

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()


def plot_map_land_HPAI_2(
    properties,
    xlims,
    ylims,
    folder_path,
    plot_suffix="",
    property_type_list=[
        "layers free-range",
        "layers caged",
        "layers barn",
        "broiler farm",
        "pullet farm",
        "egg processing",
        "abbatoir",
        "hatchery",
        "breeder",
        "backyard",
    ],
):
    """Plot properties"""

    geometries = {prop_type: [] for prop_type in property_type_list}

    for facility in properties:
        long, lat = facility.coordinates
        curr_farm = Point(long, lat)
        geometries[facility.type].append(curr_farm)

    fig, ax = plt.subplots(1, 1, figsize=(30, 30))  # ,figsize=(10,12)

    for markerlabel, geometry in geometries.items():

        geo_df = gpd.GeoDataFrame(geometry=geometry)
        geo_df.crs = {"init": "epsg:4326"}
        # plot the marker
        ax = geo_df.plot(ax=ax, markersize=20, label=markerlabel)

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    ctx.add_basemap(ax, crs={"init": "epsg:4326"}, source=ctx.providers.OpenStreetMap.Mapnik)

    # https://geopandas.org/en/stable/gallery/matplotlib_scalebar.html
    points = gpd.GeoSeries([Point(-73.5, 40.5), Point(-74.5, 40.5)], crs=4326)  # Geographic WGS 84 - degrees
    points = points.to_crs(32619)  # Projected WGS 84 - meters
    distance_meters = points[0].distance(points[1])
    ax.add_artist(
        ScaleBar(
            distance_meters,
            box_alpha=0.1,
            location="lower right",
        )
    )

    ax.set_title("Map", fontsize=18)

    ax.set_ylabel("latitude", fontsize=16)
    ax.set_xlabel("longitude", fontsize=16)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.05), fancybox=True, shadow=True, fontsize=18)

    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    file_name = f"property_locations_base_map_types{plot_suffix}.png"

    file_name = os.path.join(folder_path, file_name)

    plt.savefig(file_name, bbox_inches="tight")

    plt.close()


def property_specific_initialisation_animals_no_neighbours(
    property_coordinates,
    property_polygon,
    property_polygon_area,
    wind_radius,
    animal_type,
    premises_type,
    num_animals,
    movement_freq=1,
    movement_probability=0,
    movement_prop_animals=0,
    allowed_movement={},
    max_daily_movements=1,
    LGA="NA",
):
    lat = property_coordinates[1]  # y
    lon = property_coordinates[0]  # x
    puff_p1 = spatial_setup.geodesic_polygon_buffer(lat, lon, property_polygon, wind_radius)

    try:
        new_p = premises.Premises(
            num_animals=num_animals,  # at least five animals per property
            movement_freq=movement_freq,
            coordinates=property_coordinates,
            area_ha=property_polygon_area,
            neighbourhood=[],  # TODO - code to get neighbours once all properties are determined; and update self.total_neighbours
            property_polygon=property_polygon,
            property_polygon_puffed=puff_p1,
            property_type=premises_type,
            movement_probability=movement_probability,
            movement_prop_animals=movement_prop_animals,
            allowed_movement=allowed_movement,
            max_daily_movements=max_daily_movements,
            animal_type=animal_type,
        )
        new_p.region = LGA
    except Exception as e:
        print("Error in creating new premises:")
        print(e)
        time.sleep(120.0)
        new_p = premises.Premises(
            num_animals=num_animals,  # at least five animals per property
            movement_freq=movement_freq,
            coordinates=property_coordinates,
            area_ha=property_polygon_area,
            neighbourhood=[],
            property_polygon=property_polygon,
            property_polygon_puffed=puff_p1,
            property_type=premises_type,
            movement_probability=movement_probability,
            movement_prop_animals=movement_prop_animals,
            allowed_movement=allowed_movement,
            max_daily_movements=max_daily_movements,
            animal_type=animal_type,
        )
        new_p.region = LGA

    new_p.init_chickens_eggs()

    return new_p


def HPAI_NSW_setup_locations(
    output_filename,
    testing=False,
    data_file=os.path.join(os.path.dirname(__file__), "..", "data", "NSW_properties.xlsx"),
    wind_radius=5,
):
    """
    Generates locations for poultry and egg premises in NSW, and creates "Premises" objects from them.

    output_filename : location to save the list of premises objects
    testing : flag for testing purposes, it generates fewer properties (and so runs faster)
    data_file : file that contains LGA + premises type + number of premises, used to generate properties
    """
    Australia_shape = spatial_setup.Australia_shape()
    LGA_gdf = spatial_functions.get_LGA_gdf()

    data_poultryAgTrack = pd.read_excel(data_file, sheet_name="PoultryAgTrack")
    data_poultryCustom = pd.read_excel(data_file, sheet_name="PoultryCustom")

    occupied_regions = {}
    # all_properties = []

    # these are for plotting purposes
    chicken_meat_property_coordinates = []
    processing_chicken_meat_property_coordinates = []
    chicken_egg_property_coordinates = []
    processing_chicken_egg_property_coordinates = []

    total_chickens_LGA = {}

    ALL_coordinates = []
    ALL_p_polygon = []
    ALL_p_area = []
    ALL_wind_radius = []
    ALL_animal_type = []
    ALL_premises_type = []
    ALL_num_animals = []
    ALL_LGAs = []

    property_data_by_LGA = {}

    for i, row in data_poultryAgTrack.iterrows():

        if "All other poultry" in row["Commodity description or property type"]:
            continue  # skipping other poultry - remove this if we want to include, e.g., ducks

        if testing:
            if (
                "A" in row["Region name"]
                or "B" in row["Region name"]
                or "C" in row["Region name"]
                or "D" in row["Region name"]
                or "E" in row["Region name"]
            ):
                pass
            else:
                continue  # temporary setup for testing - to limit how long it takes. TODO: REMOVE

        LGA = row["Region name"]

        print(LGA)

        if LGA not in property_data_by_LGA:
            property_data_by_LGA[LGA] = {"total_properties": 0, "animal_type": [], "premises_type": [], "num_animals": []}

        if LGA in total_chickens_LGA:
            total_chickens_LGA[LGA] += row["Estimate"]
        else:
            total_chickens_LGA[LGA] = row["Estimate"]

        property_data_by_LGA[LGA]["total_properties"] += int(row["Number of agricultural businesses"])

        premises_type = ""

        if "Layers - Free-range" in row["Commodity description or property type"]:
            premises_type = "layers free-range"
            animal_type = "chicken"
        elif "Layers - Caged" in row["Commodity description or property type"]:
            premises_type = "layers caged"
            animal_type = "chicken"
        elif "Layers - Barn" in row["Commodity description or property type"]:
            premises_type = "layers barn"
            animal_type = "chicken"
        elif "Meat chickens" in row["Commodity description or property type"]:
            premises_type = "broiler farm"
            animal_type = "chicken"
        # elif "All other poultry" in row["Commodity description or property type"]:
        #     # TODO - not sure about this, just choosing this for now - other poultry farm, for meat, from chick to slaughter
        #     premises_type = "other poultry farm"
        #     animal_type = "poultry"
        elif " All other chickens" in row["Commodity description or property type"]:
            # TODO - should be a mix of pullets and replacement stock, but I'll just make it pullets for now
            premises_type = "pullet farm"
            animal_type = "chicken"
        else:
            raise ValueError(f"commodity/property not expected: {row['Commodity description or property type']}")

        print(premises_type)

        for _ in range(int(row["Number of agricultural businesses"])):
            num_animals = int(max(row["Estimate"] / row["Number of agricultural businesses"], 1))
            num_animals = max(100, int(num_animals / 2))
            # assuming some production cycle, animals will get replaced at least once...
            # plus will leave some animals for hatchery, breeder farms
            if premises_type == "broiler farm":
                num_animals = max(100, int(num_animals / 2))  # assuming even more of a production cycle???

            property_data_by_LGA[LGA]["animal_type"].append(animal_type)
            property_data_by_LGA[LGA]["premises_type"].append(premises_type)
            property_data_by_LGA[LGA]["num_animals"].append(num_animals)
            # could add in minimun or maximum hectare size if I want

    for i, row in data_poultryCustom.iterrows():
        if testing:
            if (
                "A" in row["Region name"]
                or "B" in row["Region name"]
                or "C" in row["Region name"]
                or "D" in row["Region name"]
                or "E" in row["Region name"]
            ):
                pass
            else:
                continue  # temporary setup for testing - to limit how long it takes.
        LGA = row["Region name"]
        print(LGA)

        property_data_by_LGA[LGA]["total_properties"] += int(row["Number of agricultural businesses"])

        premises_type = row["Commodity description or property type"]

        if premises_type == "egg processing":
            animal_type = "chicken"
            num_animals = 0  # no chickens, only eggs
        elif premises_type == "abbatoir":
            animal_type = "chicken"
            num_animals = 1000  # assuming some initial live chickens
        elif premises_type == "hatchery":
            animal_type = "chicken"
            num_animals = max(200, int(total_chickens_LGA[LGA] / 10))  # hmmm how are these actually counted???
        elif premises_type == "breeder":
            animal_type = "chicken"
            num_animals = max(200, int(total_chickens_LGA[LGA] / 10))  # hmmm how are these actually counted???
        else:
            raise ValueError(f"premises type not expected: {premises_type}")

        print(premises_type)

        for _ in range(int(row["Number of agricultural businesses"])):
            property_data_by_LGA[LGA]["animal_type"].append(animal_type)
            property_data_by_LGA[LGA]["premises_type"].append(premises_type)
            property_data_by_LGA[LGA]["num_animals"].append(num_animals)

        # add a few random backyard properties
        print("backyard")
        num_backyard = random.randint(1, 3)
        property_data_by_LGA[LGA]["total_properties"] += num_backyard
        for _ in range(num_backyard):
            property_data_by_LGA[LGA]["animal_type"].append("chicken")
            property_data_by_LGA[LGA]["premises_type"].append("backyard")
            property_data_by_LGA[LGA]["num_animals"].append(random.randint(3, 50))

    for LGA, LGA_properties_data in property_data_by_LGA.items():
        if LGA not in occupied_regions:
            occupied_regions[LGA] = []

        region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == LGA, :]
        region_shape = list(region_only["geometry"])[0]

        # # for now, assuming 5000 birds per hectare (of total farm) as an approximate
        # average_property_size = int(max(row["Estimate"] / row["Number of agricultural businesses"] / 5000, 1))
        average_property_size = 50  # a random estimate lol

        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            LGA_properties_data["total_properties"],
            region_shape,
            average_property_ha=average_property_size,
            excluded_regions=occupied_regions[LGA],
        )

        occupied_regions[LGA].extend(property_polygons)

        # sort by sizes
        if len(property_areas) > 1:
            property_areas, property_coordinates, property_polygons = map(
                list, zip(*sorted(zip(property_areas, property_coordinates, property_polygons)))
            )

            # sort the property data by sizes too
            zipped = zip(
                property_data_by_LGA[LGA]["num_animals"], property_data_by_LGA[LGA]["animal_type"], property_data_by_LGA[LGA]["premises_type"]
            )
            property_data_by_LGA[LGA]["num_animals"], property_data_by_LGA[LGA]["animal_type"], property_data_by_LGA[LGA]["premises_type"] = map(
                list, zip(*sorted(zipped))
            )

        for i in range(len(property_data_by_LGA[LGA]["animal_type"])):
            animal_type = property_data_by_LGA[LGA]["animal_type"][i]
            premises_type = property_data_by_LGA[LGA]["premises_type"][i]
            num_animals = property_data_by_LGA[LGA]["num_animals"][i]
            coordinates = property_coordinates[i]
            p_polygon = property_polygons[i]
            p_area = property_areas[i]

            if "layers" in premises_type or "pullet" in premises_type:
                chicken_egg_property_coordinates.extend(property_coordinates)
            if premises_type == "egg processing":
                processing_chicken_egg_property_coordinates.extend(property_coordinates)
            elif premises_type == "abbatoir":
                processing_chicken_meat_property_coordinates.extend(property_coordinates)
            elif premises_type == "hatchery":
                processing_chicken_egg_property_coordinates.extend(property_coordinates)
            elif premises_type == "breeder" or premises_type == "backyard":
                chicken_egg_property_coordinates.extend(property_coordinates)
            else:
                chicken_meat_property_coordinates.extend(property_coordinates)

            ALL_coordinates.append(coordinates)
            ALL_p_polygon.append(p_polygon)
            ALL_p_area.append(p_area)
            ALL_wind_radius.append(wind_radius)
            ALL_animal_type.append(animal_type)
            ALL_premises_type.append(premises_type)
            ALL_num_animals.append(num_animals)
            ALL_LGAs.append(LGA)

    with open(output_filename, "wb") as file:
        pickle.dump(
            [
                ALL_coordinates,
                ALL_p_polygon,
                ALL_p_area,
                ALL_wind_radius,
                ALL_animal_type,
                ALL_premises_type,
                ALL_num_animals,
                ALL_LGAs,
                chicken_meat_property_coordinates,
                processing_chicken_meat_property_coordinates,
                chicken_egg_property_coordinates,
                processing_chicken_egg_property_coordinates,
            ],
            file,
        )

    return (
        ALL_coordinates,
        ALL_p_polygon,
        ALL_p_area,
        ALL_wind_radius,
        ALL_animal_type,
        ALL_premises_type,
        ALL_num_animals,
        ALL_LGAs,
        chicken_meat_property_coordinates,
        processing_chicken_meat_property_coordinates,
        chicken_egg_property_coordinates,
        processing_chicken_egg_property_coordinates,
    )


def initialise_all_properties(
    ALL_coordinates,
    ALL_p_polygon,
    ALL_p_area,
    ALL_wind_radius,
    ALL_animal_type,
    ALL_premises_type,
    ALL_num_animals,
    ALL_LGAs,
    output_filename,
):
    all_properties = []
    for coordinates, p_polygon, p_area, wind_radius, animal_type, premises_type, num_animals, LGA in zip(
        ALL_coordinates, ALL_p_polygon, ALL_p_area, ALL_wind_radius, ALL_animal_type, ALL_premises_type, ALL_num_animals, ALL_LGAs
    ):
        new_p = property_specific_initialisation_animals_no_neighbours(
            coordinates,
            p_polygon,
            p_area,
            wind_radius=wind_radius,
            animal_type=animal_type,
            premises_type=premises_type,
            num_animals=num_animals,
            LGA=LGA,
        )  # note: no movement parameters - will set up a more complex system for direct movement (more direct, less random)
        all_properties.append(new_p)

    with open(output_filename, "wb") as file:
        pickle.dump(all_properties, file)

    return all_properties


def save_chicken_property_csv(properties, time, folder_path, unique_output):

    to_save = properties

    with open(os.path.join(folder_path, "properties_" + str(time)), "wb") as file:
        pickle.dump(to_save, file)

    # print output: all
    header = [
        "sim_id",
        "case_id",
        "status",
        "ip",
        "exposure_date",
        "clinical_date",
        "notification_date",
        "removal_date",
        "recovery_date",
        "vacc_date",
        "region",
        "county",
        "cluster",
        "xcoord",
        "ycoord",
        "area",
        "type",
        "animal",
        "total",
        "sheds",
        "chickens",
        "eggs",
        "fertilised eggs",
    ]
    file = os.path.join(folder_path, f"data_underlying_{unique_output}.csv")
    with open(file, "w", newline="") as f:

        # create the csv writer
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

        for premise in properties:
            # if premise.data_source != "":
            row = premise.return_output_row_chickens()
            writer.writerow(row)


def HPAI_QLD_setup_locations(
    output_filename,
    testing=False,
    data_file=os.path.join(os.path.dirname(__file__), "..", "data", "QLD_properties.xlsx"),
    shp_file=os.path.join(os.path.dirname(__file__), "..", "data", "QLD_intensive_livestock", "Intensive_livestock.shp"),
):
    """
    Generates locations for poultry and egg premises in QLD, and creates "Premises" objects from them.

    output_filename : location to save the list of premises objects
    testing : flag for testing purposes, it generates fewer properties (and so runs faster)
    data_file : file that contains LGA + premises type + number of premises, used to generate properties
    shp_file : QLD's intensive_livestock shape file that contains locations of various poultry farming premises
    """

    Australia_shape = spatial_setup.Australia_shape()
    LGA_gdf = spatial_functions.get_LGA_gdf()

    # contains custom egg processing, hatchery, abbatoirs - format same as NSW
    data_poultryCustom = pd.read_excel(data_file, sheet_name="PoultryCustom")

    data_poultry = gpd.read_file(shp_file)

    data_poultry = data_poultry.loc[data_poultry["era"] == "Poultry farming", :]

    occupied_regions = []
    all_properties = []

    # these are for plotting purposes
    chicken_meat_property_coordinates = []
    processing_chicken_meat_property_coordinates = []
    chicken_egg_property_coordinates = []
    processing_chicken_egg_property_coordinates = []

    total_chickens_LGA = {}

    for index, row in data_poultry.iterrows():

        region_name = row["lga"]
        if testing:
            if "A" in region_name or "B" in region_name or "C" in region_name:
                pass
            else:
                continue  # temporary setup for testing

        if " City" in region_name:
            region_name = region_name.replace(" City", "")
        if " Regional" in region_name:
            region_name = region_name.replace(" Regional", "")
        if " Council" in region_name:
            region_name = region_name.replace(" Council", "")
        print(region_name)

        region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == region_name, :]  # checking if the region name is actually standard or not lol
        if region_only.empty:
            raise ValueError(f"{region_name} doesn't exist")

        property_polygon = row["geometry"]
        minx, miny, maxx, maxy = row["geometry"].bounds
        property_area = spatial_functions.calculate_area(property_polygon)
        property_coordinates = [property_polygon.centroid.x, property_polygon.centroid.y]

        occupied_regions.append(property_polygon)

        premises_type = random.choices(
            ["layers free-range", "layers caged", "layers barn", "broiler farm", "pullet farm"],
            weights=(10, 10, 10, 10, 5),
        )[0]
        animal_type = "chicken"

        print(premises_type)

        if "layers" in premises_type or "pullet" in premises_type:
            chicken_egg_property_coordinates.append(property_coordinates)
        else:
            chicken_meat_property_coordinates.append(property_coordinates)

        approx_num_animals = row["ea_cap"].replace(" ", "").replace(",", "").split("-")
        print(f"approx_num_animals: {approx_num_animals}")
        if len(approx_num_animals) == 2:
            lower_lim = int(approx_num_animals[0].replace(">", ""))
            upper_lim = int(approx_num_animals[1])

            num_animals = random.randint(lower_lim, upper_lim)
        else:
            lower_lim = int(approx_num_animals[0].replace(">", ""))
            if ">" in approx_num_animals:
                num_animals = random.randint(lower_lim, 600000)
            else:
                num_animals = random.randint(int(lower_lim * 0.9), int(lower_lim * 1.1))

        print(f"num_animals: {num_animals}")

        if region_name in total_chickens_LGA:
            total_chickens_LGA[region_name] += num_animals
        else:
            total_chickens_LGA[region_name] = num_animals

        new_p = property_specific_initialisation_animals_no_neighbours(
            property_coordinates,
            property_polygon,
            property_area,
            wind_radius=5,
            animal_type=animal_type,
            premises_type=premises_type,
            num_animals=num_animals,
            LGA=region_name,
        )
        all_properties.append(new_p)

    for i, row in data_poultryCustom.iterrows():
        if testing:
            if "A" in row["Region name"] or "B" in row["Region name"] or "C" in row["Region name"]:
                pass
            else:
                continue  # temporary setup for testing - to limit how long it takes.
        print(row["Region name"])

        region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == row["Region name"], :]
        region_shape = list(region_only["geometry"])[0]

        if row["Region name"] in total_chickens_LGA:
            pass
        else:
            continue  # would mean that there aren't chicken properties in this LGA....

        # TODO: random number chosen
        average_property_size = 50

        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            int(row["Number of agricultural businesses"]),
            region_shape,
            average_property_ha=average_property_size,
            excluded_regions=occupied_regions,
        )

        occupied_regions.extend(property_polygons)

        premises_type = row["Commodity description or property type"]
        print(premises_type)

        if premises_type == "egg processing":
            processing_chicken_egg_property_coordinates.extend(property_coordinates)
            animal_type = "chicken"
            num_animals = 0  # no chickens, only eggs
        elif premises_type == "abbatoir":
            processing_chicken_meat_property_coordinates.extend(property_coordinates)
            animal_type = "chicken"
            num_animals = 1000  # assuming some initial live chickens
        elif premises_type == "hatchery":
            processing_chicken_egg_property_coordinates.extend(property_coordinates)
            animal_type = "chicken"
            # num_animals = 1000
            num_animals = max(200, int(total_chickens_LGA[row["Region name"]] / 10))  # hmmm how are these actually counted???
        elif premises_type == "breeder":
            chicken_egg_property_coordinates.extend(property_coordinates)
            animal_type = "chicken"
            num_animals = max(200, int(total_chickens_LGA[row["Region name"]] / 10))  # hmmm how are these actually counted???
        else:
            raise ValueError(f"premises type not expected: {premises_type}")

        for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
            new_p = property_specific_initialisation_animals_no_neighbours(
                coordinates,
                p_polygon,
                p_area,
                wind_radius=5,
                animal_type=animal_type,
                premises_type=premises_type,
                num_animals=num_animals,
                LGA=row["Region name"],
            )  # note: no movement parameters - will set up a more complex system for direct movement (more direct, less random)

            all_properties.append(new_p)

        # while I'm here, add a few random backyard properties
        num_backyard = random.randint(1, 5)
        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            num_backyard,
            region_shape,
            average_property_ha=1,
            excluded_regions=occupied_regions,
        )
        occupied_regions.extend(property_polygons)

        for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
            new_p = property_specific_initialisation_animals_no_neighbours(
                coordinates,
                p_polygon,
                p_area,
                wind_radius=5,
                animal_type="chicken",
                premises_type="backyard",
                num_animals=random.randint(3, 50),
                LGA=row["Region name"],
            )  # note: no movement parameters - will set up a more complex system for direct movement (more direct, less random)

            all_properties.append(new_p)

    with open(output_filename, "wb") as file:
        pickle.dump(
            [
                all_properties,
                chicken_meat_property_coordinates,
                processing_chicken_meat_property_coordinates,
                chicken_egg_property_coordinates,
                processing_chicken_egg_property_coordinates,
            ],
            file,
        )

    return (
        all_properties,
        chicken_meat_property_coordinates,
        processing_chicken_meat_property_coordinates,
        chicken_egg_property_coordinates,
        processing_chicken_egg_property_coordinates,
    )


def HPAI_movement_network_setup(
    all_properties,
    max_movement_km=500,  # 500km max movement
    data_file=os.path.join(os.path.dirname(__file__), "..", "data", "MovementNetwork.xlsx"),
):
    """
    Sets up wind neighbours and movement neighbours

    :param all_properties: Description
    :param max_movement_km: Description
    """

    # ensuring the ids match, not "initialising" animal objects for now to limit
    for p1 in range(0, len(all_properties)):
        all_properties[p1].id = p1
        # all_properties[p1].init_animals(
        #     None
        # )  # init with empty "params", as no parameters are actually used to initialise animals

    # assigning random (scrambled) simids and data sources
    random_ids = np.random.choice(range(1, 10 * len(all_properties)), size=len(all_properties), replace=False)
    for p1 in range(0, len(all_properties)):
        all_properties[p1].sim_id = random_ids[p1]

        # TODO: this is so messy LOL
        if all_properties[p1].get_num_chickens() > 100:
            all_properties[p1].data_source = random.choice(
                ["ALSR", "bio response app", "community survey", "farm records", "poultry licensing", "poultry licensing", "poultry licensing"]
            )
        else:
            if all_properties[p1].type == "backyard":
                all_properties[p1].data_source = random.choice(
                    ["bio response app", "community survey", "", "", "", "", "", "", "", ""]
                )  # weighting them to be unknown altogether
            else:
                all_properties[p1].data_source = random.choice(["ALSR", "bio response app", "community survey", "farm records", "", ""])

        if all_properties[p1].data_source == "ALSR":
            all_properties[p1].known_sheds = ""
            if random.uniform(0, 1) < 0.5:
                all_properties[p1].known_sheds = all_properties[p1].num_sheds
            all_properties[p1].known_birds = rounding_entities(all_properties[p1].get_num_chickens())
            # TODO - or maybe rather than rounding, it should be something else....
        elif all_properties[p1].data_source == "bio response app":
            all_properties[p1].known_sheds = ""
            all_properties[p1].known_birds = less_rounding_entities(all_properties[p1].get_num_chickens())
        elif all_properties[p1].data_source == "community survey":
            all_properties[p1].known_sheds = all_properties[p1].num_sheds
            all_properties[p1].known_birds = less_rounding_entities(all_properties[p1].get_num_chickens())
        elif all_properties[p1].data_source == "farm records":
            all_properties[p1].known_sheds = all_properties[p1].num_sheds
            all_properties[p1].known_birds = all_properties[p1].get_num_chickens()
        elif all_properties[p1].data_source == "poultry licensing":
            all_properties[p1].known_sheds = ""
            if random.uniform(0, 1) < 0.5:
                all_properties[p1].known_sheds = all_properties[p1].num_sheds
            all_properties[p1].known_birds = ""
        elif all_properties[p1].data_source == "":
            all_properties[p1].known_sheds = ""
            all_properties[p1].known_birds = ""

        if all_properties[p1].type in ["egg processing", "abbatoir", "backyard"]:
            all_properties[p1].known_sheds = ""
            all_properties[p1].known_area = ""
        else:
            if all_properties[p1].get_num_chickens() > 100:
                all_properties[p1].known_area = all_properties[p1].area
            else:
                all_properties[p1].known_area = ""

    # assign wind neighbours and update self.total_neighbours
    for p1 in range(0, len(all_properties)):
        p1_neighbourhood = []
        puff_p1 = all_properties[p1].puffed_poly
        for p2 in range(0, len(all_properties)):
            if p1 != p2:
                # calculate distance between centres
                # dist = np.linalg.norm(np.array(property_coordinates[p1]) - np.array(property_coordinates[p2]))
                dist_centres = spatial_functions.quick_distance_haversine(
                    all_properties[p1].coordinates, all_properties[p2].coordinates
                )  # distance in km

                # calculate whether they're wind-neighbours
                p2_poly = all_properties[p2].polygon

                if puff_p1.intersects(p2_poly):
                    # they're wind-neighbours, congrats
                    p1_neighbourhood.append([p2, dist_centres])

        all_properties[p1].neighbourhood = p1_neighbourhood
        all_properties[p1].total_neighbours = len(p1_neighbourhood)

    # now construct and assign movement neighbours
    # data_allowed_movements = pd.read_excel(data_file, sheet_name="PoultryMovement")

    # allowed_movement_setup = {}
    # allowed_movement_details = {}
    # for i, row in data_allowed_movements.iterrows():
    #     if row["From"] in allowed_movement_setup:
    #         allowed_movement_setup[row["From"]][row["To"]] = 1  # movement probability/allowance: 100%
    #         allowed_movement_details[row["From"]][row["To"]] = {"entity": row["What"], "age": row["Age"]}
    #     else:
    #         allowed_movement_setup[row["From"]] = {row["To"]: 1}
    #         allowed_movement_details[row["From"]] = {row["To"]: {"entity": row["What"], "age": row["Age"]}}

    # print(allowed_movement_setup)
    # print(allowed_movement_details)

    for i, property_i in enumerate(all_properties):  # TODO: refactor this to not be hard coded
        property_i.allowed_movement = {}  # will ignore this original / old structure
        if property_i.type == "breeder":
            property_i.allowed_movement_details = {
                "chickens": {"age": 546, "property_types": ["abbatoir"], "properties": []},
                "eggs": {"property_types": ["hatchery"], "properties": []},
            }
        elif property_i.type == "hatchery":
            property_i.allowed_movement_details = {
                "chickens": {
                    "age": 1,
                    "property_types": [
                        "pullet farm",
                        "broiler farm",
                        "layers free-range",
                        "layers barn",
                        "layers caged",
                        "backyard",
                    ],
                    "properties": [],
                }
            }
        elif property_i.type == "pullet farm":
            property_i.allowed_movement_details = {
                "chickens": {
                    "age": 119,
                    "property_types": ["layers free-range", "layers barn", "layers caged", "breeder", "backyard"],
                    "properties": [],
                }
            }
        elif "layers" in property_i.type:
            property_i.allowed_movement_details = {
                "chickens": {"age": 546, "property_types": ["abbatoir"], "properties": []},
                "eggs": {"property_types": ["egg processing"], "properties": []},
            }
        elif property_i.type == "broiler farm":
            property_i.allowed_movement_details = {"chickens": {"age": 50, "property_types": ["abbatoir"], "properties": []}}
        elif property_i.type == "egg processing":
            property_i.allowed_movement_details = {}
        elif property_i.type == "abbatoir":
            property_i.allowed_movement_details = {}
        elif property_i.type == "backyard":
            property_i.allowed_movement_details = {}
        else:
            raise ValueError(f"Property type not expected: {property_i.type}")

        max_allowable_movement = max_movement_km

        property_i.movement_neighbours = {
            "layers free-range": [],
            "layers caged": [],
            "layers barn": [],
            "broiler farm": [],
            "pullet farm": [],
            "egg processing": [],
            "abbatoir": [],
            "hatchery": [],
            "breeder": [],
            "backyard": [],
        }

        if property_i.type in ["abbatoir", "egg processing", "backyard"]:
            pass
        else:
            for j, property_j in enumerate(all_properties):
                if i == j:
                    continue
                if "chickens" in property_i.allowed_movement_details:
                    if (
                        property_j.type in property_i.allowed_movement_details["chickens"]["property_types"]
                    ):  # animal type checking (property_j.animal_type == property_i.animal_type) was removed - bring back when putting back ducks or something TODO
                        distance = spatial_functions.quick_distance_haversine(
                            property_i.coordinates,
                            property_j.coordinates,
                        )
                        if distance < max_allowable_movement:
                            if property_i.type == "hatchery":
                                if property_j.accepts_hatchlings:
                                    property_i.allowed_movement_details["chickens"]["properties"].append(j)
                                    property_i.movement_neighbours[property_j.type].append(j)
                            else:
                                property_i.allowed_movement_details["chickens"]["properties"].append(j)
                                property_i.movement_neighbours[property_j.type].append(j)
                if "eggs" in property_i.allowed_movement_details:
                    if property_j.type in property_i.allowed_movement_details["eggs"]["property_types"]:
                        distance = spatial_functions.quick_distance_haversine(
                            property_i.coordinates,
                            property_j.coordinates,
                        )
                        if distance < max_allowable_movement:
                            property_i.allowed_movement_details["eggs"]["properties"].append(j)
                            property_i.movement_neighbours[property_j.type].append(j)

    return all_properties
