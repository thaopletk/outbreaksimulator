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
import shapely.wkt
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
import pointpats


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
        # print(i + 1)
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
        if geometry == []:
            continue

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
    property_type=None,
    housing_type=None,
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

        if property_type != None:
            new_p.QLD_property_type = property_type
        if housing_type != None:
            new_p.housing_type = housing_type
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

        if property_type != None:
            new_p.QLD_property_type = property_type
        if housing_type != None:
            new_p.housing_type = housing_type

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
                continue  # temporary setup for testing - to limit how long it takes.

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
    ALL_property_type=None,
    ALL_housing_type=None,
    ALL_datasource=None,
):
    all_properties = []

    if ALL_property_type == None and ALL_housing_type == None:
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
    else:
        for (
            coordinates,
            p_polygon,
            p_area,
            wind_radius,
            animal_type,
            premises_type,
            num_animals,
            LGA,
            property_type,
            housing_type,
            data_source,
        ) in zip(
            ALL_coordinates,
            ALL_p_polygon,
            ALL_p_area,
            ALL_wind_radius,
            ALL_animal_type,
            ALL_premises_type,
            ALL_num_animals,
            ALL_LGAs,
            ALL_property_type,
            ALL_housing_type,
            ALL_datasource,
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
                property_type=property_type,
                housing_type=housing_type,
            )  # note: no movement parameters - will set up a more complex system for direct movement (more direct, less random)
            new_p.data_source = data_source
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
        "data_source",
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
    wind_radius=5,
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

    # data from https://spatial-gis.information.qld.gov.au/arcgis/rest/services/Farming/Agriculture/MapServer - layers and egg processing
    data_AgTrends = pd.read_excel(data_file, sheet_name="PoultryAgTrends")

    data_poultry = gpd.read_file(shp_file)

    data_poultry = data_poultry.loc[data_poultry["era"] == "Poultry farming", :]

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

    # reading actual actual data
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
        if " Shire" in region_name:
            region_name = region_name.replace(" Shire", "")

        LGA = region_name
        print(LGA)

        if LGA not in property_data_by_LGA:
            property_data_by_LGA[LGA] = {"total_properties": 0, "animal_type": [], "premises_type": [], "num_animals": []}

        region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == LGA, :]  # checking if the region name is actually standard or not lol
        if region_only.empty:
            raise ValueError(f"{LGA} doesn't exist")

        property_polygon = row["geometry"]
        # minx, miny, maxx, maxy = row["geometry"].bounds
        property_area = spatial_functions.calculate_area(property_polygon)
        property_coordinates = [property_polygon.centroid.x, property_polygon.centroid.y]

        premises_type = random.choices(["broiler farm", "pullet farm"], weights=(10, 5))[0]
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

        if LGA in total_chickens_LGA:
            total_chickens_LGA[LGA] += num_animals
        else:
            total_chickens_LGA[LGA] = num_animals

        if LGA not in occupied_regions:
            occupied_regions[LGA] = [property_polygon]
        else:
            occupied_regions[LGA].append(property_polygon)
        ALL_coordinates.append(property_coordinates)
        ALL_p_polygon.append(property_polygon)
        ALL_p_area.append(property_area)
        ALL_wind_radius.append(wind_radius)
        ALL_animal_type.append(animal_type)
        ALL_premises_type.append(premises_type)
        ALL_num_animals.append(num_animals)
        ALL_LGAs.append(LGA)

    QLD_LGAs = LGA_gdf.loc[LGA_gdf["STE_NAME21"] == "Queensland", :]
    QLD_LGA_list = QLD_LGAs["LGA_NAME24"].tolist()

    print(QLD_LGA_list)

    for i, row in data_AgTrends.iterrows():
        animal_type = "chicken"
        x_coord = row["x"]
        y_coord = row["y"]
        layer_or_egg_processing = row["Commodity description or property type"]
        if "layer" in layer_or_egg_processing:
            premises_type = random.choices(["layers free-range", "layers caged", "layers barn"], weights=(10, 10, 10))[0]
            num_animals = random.randint(100, 50000)  # just randomly made...
        else:
            premises_type = layer_or_egg_processing
            num_animals = 0
        # num = row["Number of agricultural businesses"] = 1
        curr_farm = Point(x_coord, y_coord)
        farm_LGA = 0
        for LGA in QLD_LGA_list:
            region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == LGA, :]
            region_shape = list(region_only["geometry"])[0]
            if region_shape != None and region_shape.contains(curr_farm):
                print(LGA)
                farm_LGA = LGA
                break

        property_coordinates = [x_coord, y_coord]
        property_polygon = Polygon(
            spatial_functions.geodesic_point_buffer(y_coord, x_coord, km=random.uniform(0.01, 0.5))
        )  # making a small round property for ease
        property_area = spatial_functions.calculate_area(property_polygon)

        chicken_egg_property_coordinates.append(property_coordinates)

        if farm_LGA not in occupied_regions:
            occupied_regions[farm_LGA] = [property_polygon]
        else:
            occupied_regions[farm_LGA].append(property_polygon)

        if farm_LGA in total_chickens_LGA:
            total_chickens_LGA[farm_LGA] += num_animals
        else:
            total_chickens_LGA[farm_LGA] = num_animals

        ALL_coordinates.append(property_coordinates)
        ALL_p_polygon.append(property_polygon)
        ALL_p_area.append(property_area)
        ALL_wind_radius.append(wind_radius)
        ALL_animal_type.append(animal_type)
        ALL_premises_type.append(premises_type)
        ALL_num_animals.append(num_animals)
        ALL_LGAs.append(LGA)

    # reading in my fake data - not assigning property areas yet
    # actually, should be replaceable with actual QLD data
    for i, row in data_poultryCustom.iterrows():
        if testing:
            if "A" in row["Region name"] or "B" in row["Region name"] or "C" in row["Region name"]:
                pass
            else:
                continue  # temporary setup for testing - to limit how long it takes.
        LGA = row["Region name"]
        print(LGA)

        region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == LGA, :]
        region_shape = list(region_only["geometry"])[0]

        if LGA in total_chickens_LGA:
            pass
        else:
            continue  # would mean that there aren't chicken properties in this LGA....

        # technically shouldn't need to do this, doing it just in case
        if LGA not in property_data_by_LGA:
            property_data_by_LGA[LGA] = {"total_properties": 0, "animal_type": [], "premises_type": [], "num_animals": []}

        property_data_by_LGA[LGA]["total_properties"] += int(row["Number of agricultural businesses"])
        premises_type = row["Commodity description or property type"]

        print(premises_type)

        if premises_type == "abbatoir":
            animal_type = "chicken"
            num_animals = 1000  # assuming some initial live chickens
        elif premises_type == "hatchery":
            animal_type = "chicken"
            # num_animals = 1000
            num_animals = max(200, int(total_chickens_LGA[row["Region name"]] / 10))  # hmmm how are these actually counted???
        elif premises_type == "breeder":
            animal_type = "chicken"
            num_animals = max(200, int(total_chickens_LGA[row["Region name"]] / 10))  # hmmm how are these actually counted???
        else:
            raise ValueError(f"premises type not expected: {premises_type}")

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

        # TODO: random number chosen
        average_property_size = 50

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


def HPAI_QLD_setup_locations_provided(
    output_filename,
    data_file=os.path.join(os.path.dirname(__file__), "..", "data", "QLD_data", "LGA_w_poultry", "LocalGovernmen_PairwiseInter.shp"),
    data_file_AgTrends=os.path.join(os.path.dirname(__file__), "..", "data", "QLD_properties.xlsx"),
    wind_radius=5,
    max_x_coord=152.769,
    max_y_coord=-26.529,
    min_x_coord=150.877,
    min_y_coord=-28.27,
):
    """Reads in provided locations from the data file"""

    Australia_shape = spatial_setup.Australia_shape()
    LGA_gdf = spatial_functions.get_LGA_gdf()

    # data from https://spatial-gis.information.qld.gov.au/arcgis/rest/services/Farming/Agriculture/MapServer
    # - layers, egg processing, and meat processing
    # we will use the egg processing and meat processing ("abbatoirs") for our purposes
    data_AgTrends = pd.read_excel(data_file_AgTrends, sheet_name="PoultryAgTrends")

    # contains producers - eggs, meat
    data_properties = gpd.read_file(data_file)

    occupied_regions = {}

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
    ALL_property_type = []
    ALL_premises_type = []
    ALL_housing_type = []
    ALL_num_animals = []
    ALL_LGAs = []
    ALL_datasource = []

    property_data_by_LGA = {}

    QLD_LGAs = LGA_gdf.loc[LGA_gdf["STE_NAME21"] == "Queensland", :]
    QLD_LGA_list = QLD_LGAs["LGA_NAME24"].tolist()

    LGAs_to_focus_on = []

    for index, row in data_properties.iterrows():
        # print(row)
        LGA = row["LGA_1"]
        if LGA == "Pittsworth":
            LGA = "Toowoomba"  # a fix

        region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == LGA, :]  # checking if the region name is actually standard or not lol
        if region_only.empty:

            raise ValueError(f"{LGA} doesn't exist")

        LGAs_to_focus_on.append(LGA)  # we're only going to focus on some LGAs

        property_polygon = row["geometry"]
        property_area = spatial_functions.calculate_area(property_polygon)
        property_coordinates = [property_polygon.centroid.x, property_polygon.centroid.y]

        animal_type = "chicken"

        QLD_property_type = row["PIC"]  # just hijacking QLD property type to store PICs now
        housing_type = row["Enterprise"]  # Free Range or Intensive OR Abbatoir
        product_type = row["Product"]

        estimated_animals = int(row["Estimated_"])

        if housing_type == "":
            raise ValueError("empty housing type")

        if housing_type in ["Free Range", "Intensive"]:
            if product_type == "Egg":
                if estimated_animals < 15:
                    premises_type = "backyard"
                else:
                    premises_type = random.choices(["layers", "breeder", "hatchery"], weights=(15, 1, 1))[0]
                chicken_egg_property_coordinates.append(property_coordinates)
            elif product_type == "Meat":
                premises_type = random.choices(["broiler farm", "pullet farm"], weights=(15, 5))[0]
                chicken_meat_property_coordinates.append(property_coordinates)
            else:
                raise ValueError(f"product type {product_type} not expected")
        else:
            if product_type == "Egg":
                premises_type = "egg processing"
                processing_chicken_egg_property_coordinates.append(property_coordinates)
            elif product_type == "Meat":
                premises_type = "abbatoir"
                processing_chicken_meat_property_coordinates.append(property_coordinates)
            else:
                raise ValueError(f"product type {product_type} not expected for abbatoir")

            housing_type = ""

        # assumption that the estimated value is an underestimate (i.e., that people would prefer to under report)
        num_animals = num_animals = random.randint(estimated_animals, estimated_animals * 2)

        if LGA in total_chickens_LGA:
            total_chickens_LGA[LGA] += num_animals
        else:
            total_chickens_LGA[LGA] = num_animals

        if LGA not in occupied_regions:
            occupied_regions[LGA] = [property_polygon]
        else:
            occupied_regions[LGA].append(property_polygon)

        ALL_coordinates.append(property_coordinates)
        ALL_p_polygon.append(property_polygon)
        ALL_p_area.append(property_area)
        ALL_wind_radius.append(wind_radius)
        ALL_animal_type.append(animal_type)
        ALL_premises_type.append(premises_type)
        ALL_num_animals.append(num_animals)
        ALL_LGAs.append(LGA)
        ALL_property_type.append(QLD_property_type)
        ALL_housing_type.append(housing_type)
        ALL_datasource.append("RBE")

        if LGA not in property_data_by_LGA:
            property_data_by_LGA[LGA] = {"total_properties": 0, "animal_type": [], "premises_type": [], "num_animals": []}

        # add a few random backyard properties that are not yet known
        if random.uniform(0, 1) < 0.01:
            print("backyard")
            property_data_by_LGA[LGA]["total_properties"] += 1
            property_data_by_LGA[LGA]["animal_type"].append("chicken")
            property_data_by_LGA[LGA]["premises_type"].append("backyard")
            property_data_by_LGA[LGA]["num_animals"].append(random.randint(1, 10))  # very small backyard

    for i, row in data_AgTrends.iterrows():
        animal_type = "chicken"
        x_coord = row["x"]
        y_coord = row["y"]

        if x_coord < max_x_coord and x_coord > min_x_coord and y_coord < max_y_coord and y_coord > min_y_coord:
            pass
        else:
            continue

        property_type = row["Commodity description or property type"]
        if "layer" in property_type:
            continue  # not taking these
        elif "egg processing" in property_type:
            premises_type = property_type
            num_animals = 0
        elif "abbatoir" in property_type:
            if random.uniform(0, 1) < 0.3:

                premises_type = property_type
                # num_animals = 1000  # assuming some initial live chickens
                num_animals = 0
            else:
                continue
        else:
            raise ValueError(f"Not expecting this property type: {property_type}")
        # num = row["Number of agricultural businesses"] = 1
        curr_farm = Point(x_coord, y_coord)
        farm_LGA = 0
        for LGA in QLD_LGA_list:
            region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == LGA, :]
            region_shape = list(region_only["geometry"])[0]
            if region_shape != None and region_shape.contains(curr_farm):
                # print(LGA)
                farm_LGA = LGA
                break

        if farm_LGA in LGAs_to_focus_on:  # only include if it's in the right area

            property_coordinates = [x_coord, y_coord]
            property_polygon = Polygon(
                spatial_functions.geodesic_point_buffer(y_coord, x_coord, km=random.uniform(0.01, 0.5))
            )  # making a small round property for ease

            # check that this point isn't already in somewhere...
            preoccupied_region = unary_union(occupied_regions[farm_LGA])
            if preoccupied_region.contains(curr_farm):
                continue  # skip this!

            property_area = spatial_functions.calculate_area(property_polygon)

            if premises_type == "egg processing":
                processing_chicken_egg_property_coordinates.append(property_coordinates)
            else:
                processing_chicken_meat_property_coordinates.append(property_coordinates)

            if farm_LGA not in occupied_regions:
                occupied_regions[farm_LGA] = [property_polygon]
            else:
                occupied_regions[farm_LGA].append(property_polygon)

            if farm_LGA in total_chickens_LGA:
                total_chickens_LGA[farm_LGA] += num_animals
            else:
                total_chickens_LGA[farm_LGA] = num_animals

            ALL_coordinates.append(property_coordinates)
            ALL_p_polygon.append(property_polygon)
            ALL_p_area.append(property_area)
            ALL_wind_radius.append(wind_radius)
            ALL_animal_type.append(animal_type)
            ALL_premises_type.append(premises_type)
            ALL_num_animals.append(num_animals)
            ALL_LGAs.append(LGA)
            QLD_property_type = ""  # nothing
            ALL_property_type.append(QLD_property_type)
            housing_type = ""  # not relevant
            ALL_housing_type.append(housing_type)
            ALL_datasource.append("EA")

    for LGA, LGA_properties_data in property_data_by_LGA.items():
        if LGA not in occupied_regions:
            occupied_regions[LGA] = []

        region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == LGA, :]
        region_shape = list(region_only["geometry"])[0]

        # TODO: random number chosen
        average_property_size = 1

        if LGA_properties_data["total_properties"] > 0:

            excluded_regions = unary_union(occupied_regions[LGA])

            # Generates 5 points inside polygon
            points_inside_LGA = pointpats.random.poisson(region_shape, size=2 * LGA_properties_data["total_properties"])
            i_random_points = -1
            for i in range(LGA_properties_data["total_properties"]):
                suitable = False
                while not suitable:
                    i_random_points += 1
                    if i_random_points >= len(points_inside_LGA):
                        raise Exception("Not enough generated points within region!")

                    coords = points_inside_LGA[i_random_points]
                    x_coord = coords[0]
                    y_coord = coords[1]
                    property_polygon = Polygon(
                        spatial_functions.geodesic_point_buffer(y_coord, x_coord, km=random.uniform(0.01, 0.5))
                    )  # making a small round property for ease

                    if region_shape.contains(property_polygon) and not excluded_regions.contains(property_polygon):
                        suitable = True

                        property_area = spatial_functions.calculate_area(property_polygon)

                        occupied_regions[LGA].append(property_polygon)

                        animal_type = property_data_by_LGA[LGA]["animal_type"][i]
                        premises_type = property_data_by_LGA[LGA]["premises_type"][i]
                        num_animals = property_data_by_LGA[LGA]["num_animals"][i]
                        property_coordinates = [x_coord, y_coord]

                        ALL_coordinates.append(property_coordinates)
                        ALL_p_polygon.append(property_polygon)
                        ALL_p_area.append(property_area)
                        ALL_wind_radius.append(wind_radius)
                        ALL_animal_type.append(animal_type)
                        ALL_premises_type.append(premises_type)
                        ALL_num_animals.append(num_animals)
                        ALL_LGAs.append(LGA)
                        ALL_property_type.append("")
                        ALL_housing_type.append("Free Range")
                        ALL_datasource.append("")

                        if "layers" in premises_type or "pullet" in premises_type:
                            chicken_egg_property_coordinates.append(property_coordinates)
                        if premises_type == "egg processing":
                            processing_chicken_egg_property_coordinates.append(property_coordinates)
                        elif premises_type == "abbatoir":
                            processing_chicken_meat_property_coordinates.append(property_coordinates)
                        elif premises_type == "hatchery":
                            processing_chicken_egg_property_coordinates.append(property_coordinates)
                        elif premises_type == "breeder" or premises_type == "backyard":
                            chicken_egg_property_coordinates.append(property_coordinates)
                        else:
                            chicken_meat_property_coordinates.append(property_coordinates)

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
                ALL_property_type,
                ALL_housing_type,
                ALL_datasource,
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
        ALL_property_type,
        ALL_housing_type,
        ALL_datasource,
        chicken_meat_property_coordinates,
        processing_chicken_meat_property_coordinates,
        chicken_egg_property_coordinates,
        processing_chicken_egg_property_coordinates,
    )


def HPAI_movement_network_setup(
    all_properties,
    max_movement_km=500,  # 500km max movement
    data_file=os.path.join(os.path.dirname(__file__), "..", "data", "MovementNetwork.xlsx"),
    state="NSW",
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
        if state == "NSW":
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
        elif state == "QLD":
            if all_properties[p1].type != "backyard":
                all_properties[p1].data_source = "RBE"
            else:
                all_properties[p1].data_source = random.choice(
                    ["RBE", "RBE", "", "", "", "", "", "", "", ""]
                )  # weighting them to be unknown altogether

            if all_properties[p1].data_source == "RBE":
                all_properties[p1].known_sheds = all_properties[p1].num_sheds
                all_properties[p1].known_birds = all_properties[p1].get_num_chickens()
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
        elif state == "QLD-provided":
            if all_properties[p1].data_source == "RBE":
                all_properties[p1].known_sheds = all_properties[p1].num_sheds
                all_properties[p1].known_birds = all_properties[p1].get_num_chickens()
                all_properties[p1].known_area = all_properties[p1].area
            elif all_properties[p1].data_source == "":
                all_properties[p1].known_sheds = ""
                all_properties[p1].known_birds = ""
                all_properties[p1].known_area = ""
            elif all_properties[p1].data_source == "EA":  # should only be abbatoirs and egg processors
                all_properties[p1].known_sheds = ""
                all_properties[p1].known_birds = ""
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
                        "breeder",
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
        elif property_i.type == "broiler farm" or property_i.type == "Meat production; ":
            property_i.allowed_movement_details = {"chickens": {"age": 50, "property_types": ["abbatoir"], "properties": []}}
        elif property_i.type == "egg processing":
            property_i.allowed_movement_details = {}
        elif property_i.type == "abbatoir":
            property_i.allowed_movement_details = {}
        elif property_i.type == "backyard" or property_i.type == "Other; ":
            property_i.allowed_movement_details = {}
        elif property_i.type == "Egg production; " or property_i.type == "Mixed; ":
            property_i.allowed_movement_details = {
                "chickens": {"age": 546, "property_types": ["abbatoir"], "properties": []},
                "eggs": {"property_types": ["egg processing"], "properties": []},
            }
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


def FMD_VIC_setup_locations(
    output_filename,
    data_folder=os.path.join(os.path.dirname(__file__), "..", "data", "FMDVIC"),
    wind_radius=20,
):
    """
    Reads in provided farm (herd) locations and sizes

    output_filename : location to save the processed data
    data_folder : folder that contains various data available for property set up
    wind_radius : max distance for wind dispersal of fomites
    """

    Victoria_shape = spatial_setup.get_Victoria_shape()
    LGA_gdf = spatial_functions.get_LGA_gdf()

    herd_data = pd.read_csv(os.path.join(data_folder, "herd.csv"))
    herd_type = pd.read_csv(os.path.join(data_folder, "herd_type.csv"))
    species_data = pd.read_csv(os.path.join(data_folder, "species.csv"))

    herd_type = herd_type[["herd type id", "herd type name", "species ID"]]
    species_data = species_data[["species id", "species desc"]]  # What is "other" here...
    species_data.rename(columns={"species id": "species ID", "species desc": "animal_type"}, inplace=True)
    herd_type = pd.merge(herd_type, species_data, on="species ID")
    herd_type.rename(columns={"herd type id": "herd type"}, inplace=True)

    herd_data = pd.merge(herd_data, herd_type, on="herd type")

    lga = pd.read_csv(os.path.join(data_folder, "lga.csv"))
    lga = lga[["AADIS id", "Lga code10", "Lga name10", "State id"]]
    lga.rename(columns={"AADIS id": "lga id"}, inplace=True)

    herd_data = pd.merge(herd_data, lga, on="lga id")
    # filter out things not in Victoria, State id = 2
    herd_data = herd_data[herd_data["State id"] == 2]

    # various facilities
    abattoir_data = pd.read_csv(os.path.join(data_folder, "abattoir.csv"))
    export_facility_data = pd.read_csv(os.path.join(data_folder, "export_facility.csv"))
    saleyard_data = pd.read_csv(os.path.join(data_folder, "saleyard.csv"))

    occupied_regions = {}

    beef_coordinates = []
    sheep_coordinates = []
    dairy_coordinates = []
    pigs_coordinates = []
    facility_coordinates = []
    other_coordinates = []

    ALL_coordinates = []
    ALL_p_polygon = []
    ALL_p_area = []
    ALL_wind_radius = []
    ALL_animal_type = []
    ALL_premises_type = []
    ALL_num_animals = []
    ALL_LGAs = []
    # new FMD specific
    ALL_extra_info = []

    # property_data_by_LGA = {}

    for i, row in herd_data.iterrows():
        LGA = row["Lga name10"]
        LGA = (LGA[:-4]).rstrip()  # removing the last few characters
        # print(LGA)

        region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == LGA, :]  # checking if the region name is actually standard or not lol
        if region_only.empty:
            if LGA == "Unincorporated":
                LGA = LGA + " Vic"
            elif LGA == "Colac-Otway":
                LGA = "Colac Otway"
            elif LGA == "Moreland":
                LGA = "Merri-bek"
            else:
                LGA = LGA + " (Vic.)"
            region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == LGA, :]  # checking if the region name is actually standard or not lol
            if region_only.empty:
                print(row)
                raise ValueError(f"{LGA} doesn't exist")

        property_coordinates = [row["herd long"], row["herd lat"]]
        property_polygon = Polygon(
            spatial_functions.geodesic_point_buffer(row["herd lat"], row["herd long"], km=random.uniform(0.01, 0.5))
        )  # making a small round property for ease ; to update with Vic property parcel data if possible

        property_area = spatial_functions.calculate_area(property_polygon)

        premises_type = row["herd type name"]
        animal_type = row["animal_type"]
        if animal_type == "other":
            animal_type = random.choices(["cattle", "sheep", "pigs"])[0]

        if "beef" in premises_type:
            beef_coordinates.append(property_coordinates)
        elif "feedlot" in premises_type:
            facility_coordinates.append(property_coordinates)
        elif "sheep" in premises_type:
            sheep_coordinates.append(property_coordinates)
        elif "dairy" in premises_type:
            dairy_coordinates.append(property_coordinates)
        elif "pigs" in premises_type:
            pigs_coordinates.append(property_coordinates)
        else:
            other_coordinates.append(property_coordinates)  # small holders

        num_animals = int(row["herd size"])

        if LGA not in occupied_regions:
            occupied_regions[LGA] = [property_polygon]
        else:
            occupied_regions[LGA].append(property_polygon)

        ALL_coordinates.append(property_coordinates)
        ALL_p_polygon.append(property_polygon)
        ALL_p_area.append(property_area)
        ALL_wind_radius.append(wind_radius)
        ALL_animal_type.append(animal_type)
        ALL_premises_type.append(premises_type)
        ALL_num_animals.append(num_animals)
        ALL_LGAs.append(LGA)
        # new FMD specific
        ALL_extra_info.append({"herd_id": int(row["herd id"]), "farm_id": int(row["farm id"]), "saleyard_id": int(row["saleyard id"])})

    VIC_LGAs = LGA_gdf.loc[LGA_gdf["STE_NAME21"] == "Victoria", :]
    VIC_LGA_list = VIC_LGAs["LGA_NAME24"].tolist()

    for i, row in abattoir_data.iterrows():
        x_coord = row["longitude"]
        y_coord = row["latitude"]

        # check if it is in Victoria or not
        curr_farm = Point(x_coord, y_coord)
        if not Victoria_shape.contains(curr_farm):
            continue

        # Find the LGA
        farm_LGA = 0
        for LGA in VIC_LGA_list:
            region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == LGA, :]
            region_shape = list(region_only["geometry"])[0]
            if region_shape != None and region_shape.contains(curr_farm):
                print(LGA)
                farm_LGA = LGA
                break
        if farm_LGA == 0:
            print(row)
            raise ValueError("Unable to find LGA")
        LGA = farm_LGA

        property_coordinates = [x_coord, y_coord]
        property_polygon = Polygon(
            spatial_functions.geodesic_point_buffer(y_coord, x_coord, km=random.uniform(0.01, 0.5))
        )  # making a small round property for ease ; to update with Vic property parcel data if possible
        property_area = spatial_functions.calculate_area(property_polygon)

        premises_type = "abattoir"
        animal_type = []
        if row["cattle"]:  # if true
            animal_type.append("cattle")
        if row["sheep"]:
            animal_type.append("sheep")
        if row["pigs"]:
            animal_type.append("pigs")

        facility_coordinates.append(property_coordinates)

        num_animals = 0

        if LGA not in occupied_regions:
            occupied_regions[LGA] = [property_polygon]
        else:
            occupied_regions[LGA].append(property_polygon)

        ALL_coordinates.append(property_coordinates)
        ALL_p_polygon.append(property_polygon)
        ALL_p_area.append(property_area)
        ALL_wind_radius.append(wind_radius)
        ALL_animal_type.append(animal_type)
        ALL_premises_type.append(premises_type)
        ALL_num_animals.append(num_animals)
        ALL_LGAs.append(LGA)
        # new FMD specific
        ALL_extra_info.append({"id": row["ID"], "PIC": row["PIC"], "name": row["Name"], "export": int(row["export"])})

    for i, row in saleyard_data.iterrows():
        x_coord = row["longitude"]
        y_coord = row["latitude"]

        # check if it is in Victoria or not
        curr_farm = Point(x_coord, y_coord)
        if not Victoria_shape.contains(curr_farm):
            continue

        # Find the LGA
        farm_LGA = 0
        for LGA in VIC_LGA_list:
            region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == LGA, :]
            region_shape = list(region_only["geometry"])[0]
            if region_shape != None and region_shape.contains(curr_farm):
                print(LGA)
                farm_LGA = LGA
                break
        if farm_LGA == 0:
            print(row)
            raise ValueError("Unable to find LGA")
        LGA = farm_LGA

        property_coordinates = [x_coord, y_coord]
        property_polygon = Polygon(
            spatial_functions.geodesic_point_buffer(y_coord, x_coord, km=random.uniform(0.01, 0.5))
        )  # making a small round property for ease ; to update with Vic property parcel data if possible
        property_area = spatial_functions.calculate_area(property_polygon)

        premises_type = "saleyard"
        animal_type = ["cattle", "sheep", "pigs"]

        facility_coordinates.append(property_coordinates)

        num_animals = 0

        if LGA not in occupied_regions:
            occupied_regions[LGA] = [property_polygon]
        else:
            occupied_regions[LGA].append(property_polygon)

        ALL_coordinates.append(property_coordinates)
        ALL_p_polygon.append(property_polygon)
        ALL_p_area.append(property_area)
        ALL_wind_radius.append(wind_radius)
        ALL_animal_type.append(animal_type)
        ALL_premises_type.append(premises_type)
        ALL_num_animals.append(num_animals)
        ALL_LGAs.append(LGA)
        # new FMD specific
        ALL_extra_info.append({"id": row["id"], "name": row["name"]})

    for i, row in export_facility_data.iterrows():
        x_coord = row["longitude"]
        y_coord = row["latitude"]

        # check if it is in Victoria or not
        curr_farm = Point(x_coord, y_coord)
        if not Victoria_shape.contains(curr_farm):
            continue

        # Find the LGA
        farm_LGA = 0
        for LGA in VIC_LGA_list:
            region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == LGA, :]
            region_shape = list(region_only["geometry"])[0]
            if region_shape != None and region_shape.contains(curr_farm):
                print(LGA)
                farm_LGA = LGA
                break
        if farm_LGA == 0:
            print(row)
            raise ValueError("Unable to find LGA")
        LGA = farm_LGA

        property_coordinates = [x_coord, y_coord]
        property_polygon = Polygon(
            spatial_functions.geodesic_point_buffer(y_coord, x_coord, km=random.uniform(0.01, 0.5))
        )  # making a small round property for ease ; to update with Vic property parcel data if possible
        property_area = spatial_functions.calculate_area(property_polygon)

        premises_type = "export_facility"
        animal_type = ["cattle", "sheep", "pigs"]

        facility_coordinates.append(property_coordinates)

        num_animals = 0

        if LGA not in occupied_regions:
            occupied_regions[LGA] = [property_polygon]
        else:
            occupied_regions[LGA].append(property_polygon)

        ALL_coordinates.append(property_coordinates)
        ALL_p_polygon.append(property_polygon)
        ALL_p_area.append(property_area)
        ALL_wind_radius.append(wind_radius)
        ALL_animal_type.append(animal_type)
        ALL_premises_type.append(premises_type)
        ALL_num_animals.append(num_animals)
        ALL_LGAs.append(LGA)
        # new FMD specific
        ALL_extra_info.append({"id": row["ID"], "name": row["Name"], "PIC": row["PIC"], "capacity": row["capacity"]})

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
                ALL_extra_info,
                beef_coordinates,
                sheep_coordinates,
                dairy_coordinates,
                pigs_coordinates,
                facility_coordinates,
                other_coordinates,
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
        ALL_extra_info,
        beef_coordinates,
        sheep_coordinates,
        dairy_coordinates,
        pigs_coordinates,
        facility_coordinates,
        other_coordinates,
    )


def plot_map_land_FMD(
    beef_coordinates,
    sheep_coordinates,
    dairy_coordinates,
    pigs_coordinates,
    facility_coordinates,
    other_coordinates,
    xlims,
    ylims,
    folder_path,
    plot_suffix="",
):
    """Plot properties"""

    brown_cow = plt.imread(os.path.join(os.path.dirname(__file__), "..", "images", "cow_brown.png"))
    brown_cow = OffsetImage(brown_cow, zoom=0.02)

    cow = plt.imread(os.path.join(os.path.dirname(__file__), "..", "images", "cow.png"))
    cow = OffsetImage(cow, zoom=0.1)

    sheep = plt.imread(os.path.join(os.path.dirname(__file__), "..", "images", "sheep.png"))
    sheep = OffsetImage(sheep, zoom=0.02)

    pig = plt.imread(os.path.join(os.path.dirname(__file__), "..", "images", "pig.png"))
    pig = OffsetImage(pig, zoom=0.02)

    fence = plt.imread(os.path.join(os.path.dirname(__file__), "..", "images", "fence.png"))
    fence = OffsetImage(fence, zoom=0.01)

    factory = plt.imread(os.path.join(os.path.dirname(__file__), "..", "images", "factory.png"))
    factory = OffsetImage(factory, zoom=0.02)

    fig, ax = plt.subplots(1, 1, figsize=(40, 40))  # ,figsize=(10,12)

    for coordinates, marker, markerlabel in [
        [beef_coordinates, brown_cow, "beef"],
        [sheep_coordinates, sheep, "sheep"],
        [dairy_coordinates, cow, "dairy"],
        [pigs_coordinates, pig, "pigs"],
        [facility_coordinates, factory, "facilities"],
        [other_coordinates, fence, "other"],
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
