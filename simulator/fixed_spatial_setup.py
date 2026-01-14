""" Fixed spatial setup

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

    chickenmeatimage = plt.imread(os.path.join(os.path.dirname(__file__), "..", "images", "chickenmeat.png"))
    chickenmeatimage_box = OffsetImage(chickenmeatimage, zoom=0.025)

    eggimage = plt.imread(os.path.join(os.path.dirname(__file__), "..", "images", "egg.png"))
    eggimage_box = OffsetImage(eggimage, zoom=0.1)

    eggcartonimage = plt.imread(os.path.join(os.path.dirname(__file__), "..", "images", "eggcarton.png"))
    eggcartonimage_box = OffsetImage(eggcartonimage, zoom=0.06)

    fig, ax = plt.subplots(1, 1, figsize=(30, 30))  # ,figsize=(10,12)

    for coordinates, marker, markerlabel in [
        [chicken_meat_property_coordinates, chickenimage_box, "Chicken Meat"],
        [chicken_egg_property_coordinates, eggimage_box, "Chicken Egg"],
        [processing_chicken_egg_property_coordinates, eggcartonimage_box, "Chicken Egg Processing"],
        [processing_chicken_meat_property_coordinates, chickenmeatimage_box, "Chicken Meat Processing"],
    ]:
        geometries = []
        print(markerlabel)
        print(coordinates)

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

    ax.set_xlim(xlims)
    ax.set_ylim(ylims)

    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.05),
    #       fancybox=True, shadow=True, fontsize=18)

    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    file_name = f"property_locations_base_map{plot_suffix}.png"

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

    new_p.init_chickens_eggs()

    return new_p


def HPAI_NSW_setup_locations(
    output_filename,
    testing=False,
    data_file=os.path.join(os.path.dirname(__file__), "..", "data", "NSW_properties.xlsx"),
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

    occupied_regions = []
    all_properties = []

    # these are for plotting purposes
    chicken_meat_property_coordinates = []
    processing_chicken_meat_property_coordinates = []
    chicken_egg_property_coordinates = []
    processing_chicken_egg_property_coordinates = []

    for i, row in data_poultryAgTrack.iterrows():

        if "All other poultry" in row["Commodity description or property type"]:
            continue  # skipping other poultry - remove this if we want to include, e.g., ducks

        if testing:
            if "A" in row["Region name"] or "B" in row["Region name"]:
                pass
            else:
                continue  # temporary setup for testing - to limit how long it takes. TODO: REMOVE

        print(row["Region name"])

        region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == row["Region name"], :]
        region_shape = list(region_only["geometry"])[0]

        # TODO: for now, assuming 5000 birds per hectare (of total farm) as an approximate
        average_property_size = int(max(row["Estimate"] / row["Number of agricultural businesses"] / 5000, 1))

        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            int(row["Number of agricultural businesses"]),
            region_shape,
            average_property_ha=average_property_size,
            excluded_regions=occupied_regions,
        )

        occupied_regions.extend(property_polygons)

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
            premises_type = "meat growing-farm"
            animal_type = "chicken"
        # elif "All other poultry" in row["Commodity description or property type"]:
        #     # TODO - not sure about this, just choosing this for now - other poultry farm, for meat, from chick to slaughter
        #     premises_type = "other poultry farm"
        #     animal_type = "poultry"
        elif " All other chickens" in row["Commodity description or property type"]:
            # TODO - should be a mix of pullets and replacement stock, but I'll just make it pullets for now
            premises_type = "pullets farm"
            animal_type = "chicken"
        else:
            raise ValueError(f"commodity/property not expected: {row['Commodity description or property type']}")

        print(premises_type)

        if "layers" in premises_type or "pullets" in premises_type:
            chicken_egg_property_coordinates.extend(property_coordinates)
        else:
            chicken_meat_property_coordinates.extend(property_coordinates)

        for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
            new_p = property_specific_initialisation_animals_no_neighbours(
                coordinates,
                p_polygon,
                p_area,
                wind_radius=5,
                animal_type=animal_type,
                premises_type=premises_type,
                num_animals=int(max(row["Estimate"] / row["Number of agricultural businesses"], 1)),
            )  # note: no movement parameters - will set up a more complex system for direct movement (more direct, less random)

            all_properties.append(new_p)

    for i, row in data_poultryCustom.iterrows():
        if testing:
            if "A" in row["Region name"] or "B" in row["Region name"]:
                pass
            else:
                continue  # temporary setup for testing - to limit how long it takes.
        print(row["Region name"])

        region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == row["Region name"], :]
        region_shape = list(region_only["geometry"])[0]

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
            num_animals = 1000  # TODO: actually need to calculate the number of chickens the hatchery has to support the other stuff
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


def save_chicken_property_csv(properties, time, folder_path, unique_output):

    to_save = properties

    with open(os.path.join(folder_path, "properties_" + str(time)), "wb") as file:
        pickle.dump(to_save, file)

    # print output: all
    header = [
        "id",
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
    ]
    file = os.path.join(folder_path, f"data_underlying_{unique_output}.csv")
    with open(file, "w", newline="") as f:

        # create the csv writer
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

        for premise in properties:
            row = premise.return_output_row_chickens()
            writer.writerow(row)


def HPAI_QLD_setup():
    pass


# NOTE: old function, see HPAI_NSW_setup_locations() instead
# TODO: delete; though kept in case I need parts of it for the QLD data stuff
# def HPAI_setup(
#     xrange,
#     yrange,
#     folder_path_main,
#     output_filename,
#     num_properties_in_regions={"large": 20, "medium": 50, "small": 100, "very_small": 100},
# ):
#     # Australia_gdf = spatial_setup.get_Australia_shape()
#     Australia_shape = spatial_setup.Australia_shape()
#     UCL_gdf = spatial_functions.get_UCL_gdf()
#     SAL_gdf = spatial_functions.get_SALs_gdf()
#     SA4_gdf = spatial_functions.get_SA4_gdf()
#     LGA_gdf = spatial_functions.get_LGA_gdf()

#     # CHICKEN MEAT

#     # https://chicken.org.au/our-product/facts-and-figures/
#     # https://chicken.org.au/wp-content/uploads/2024/09/Industry-Map-8.png
#     # https://chicken.org.au/wp-content/uploads/2024/09/Industry-Map-2.png
#     # https://www.poultryhub.org/production/meat-chicken-broiler-industry

#     # use a 50-100 km radius around these areas
#     chicken_meat_regions_large = [
#         # "Perth (WA)",
#         # "Mount Barker (WA)",
#         # "Adelaide",
#         "Brisbane",
#         "Mount Cotton",
#         "Inglewood (L) (Qld)",
#         "Galston",
#         "Girraween (NSW)",
#         "Griffith",
#         "Hunter Valley exc Newcastle",
#         "Sydney",
#         "Mangrove Mountain",
#     ]
#     chicken_meat_regions_medium = [
#         # "Geelong",
#         "Tamworth",
#         # "Bendigo",
#         "Beresfield",
#     ]
#     chicken_meat_regions_small = [
#         # "Thomastown",
#         "Mareeba",
#         # "Somerville (Vic.)",
#         # "Sassafras (Vic.)",
#         # "Hobart",
#         # "Port Wakefield",
#         # "Murray Bridge",
#         "Goulburn",
#         # "Nagambie",
#         # "Melbourne",
#         # "Mornington Peninsula",
#         # "Devonport",
#         # "Launceston",
#         "Newcastle",
#         "Redland Bay",
#         "Two Wells",
#         "Byron Bay",
#     ]

#     # TODO: assign these as actual locations
#     processing_plant_locations = [
#         # "Perth (WA)",
#         # "Perth (WA)",
#         # "Mount Barker (WA)",
#         "Mareeba",
#         # "Adelaide",
#         # "Adelaide",
#         # "Adelaide",
#         "Brisbane",
#         "Mount Cotton",
#         "Inglewood (L) (Qld)",
#         "Tamworth",
#         "Beresfield",
#         "Galston",
#         "Girraween (NSW)",
#         "Griffith",
#         # "Bendigo",
#         # "Thomastown",
#         # "Geelong",
#         # "Somerville (Vic.)",
#         # "Sassafras (Vic.)",
#         # "Hobart",
#     ]

#     def get_region_shape(region):
#         region_only = UCL_gdf.loc[UCL_gdf["UCL_NAME21"] == region, :]
#         try:
#             region_shape = list(region_only["geometry"])[0]
#         except:
#             region_only = SAL_gdf.loc[SAL_gdf["SAL_NAME21"] == region, :]
#             try:
#                 region_shape = list(region_only["geometry"])[0]
#             except:
#                 region_only = SA4_gdf.loc[SA4_gdf["SA4_NAME21"] == region, :]
#                 try:
#                     region_shape = list(region_only["geometry"])[0]
#                 except:
#                     region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == region, :]
#                     region_shape = list(region_only["geometry"])[0]

#         return region_shape

#     def expand_region(region, km=50):
#         # expansion 50 km
#         minx, miny, maxx, maxy = region.bounds
#         lat = (miny + maxy) / 2  # y
#         lon = (minx + maxx) / 2  # x
#         expanded_region = spatial_functions.geodesic_polygon_buffer(lat, lon, region, km)

#         # making sure the region doesn't include the ocean!!!!
#         expanded_region = expanded_region.intersection(Australia_shape)

#         return expanded_region

#     occupied_regions = []
#     all_properties = []

#     chicken_meat_property_coordinates = []
#     chicken_meat_property_polygons = []
#     chicken_meat_property_areas = []

#     processing_chicken_meat_property_coordinates = []
#     processing_chicken_meat_property_polygons = []
#     processing_chicken_meat_property_areas = []

#     for region in chicken_meat_regions_large:
#         print(region)
#         region_only = get_region_shape(region)
#         expanded_region = expand_region(region_only, km=50)
#         property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
#             int(np.ceil(num_properties_in_regions["large"] / len(chicken_meat_regions_large))),
#             expanded_region,
#             average_property_ha=300,
#         )

#         chicken_meat_property_coordinates.extend(property_coordinates)
#         chicken_meat_property_polygons.extend(property_polygons)
#         chicken_meat_property_areas.extend(property_areas)

#         occupied_regions.extend(property_polygons)

#         for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
#             new_p = property_specific_initialisation_animals_no_neighbours(
#                 coordinates,
#                 p_polygon,
#                 p_area,
#                 wind_radius=5,
#                 animal_type="chicken",
#                 premises_type="chicken-meat-farm",
#                 num_animals=1000,
#                 movement_freq=1,
#                 movement_probability=0.5,
#                 movement_prop_animals=0.2,
#                 allowed_movement={"chicken-meat-farm": 0.6, "chicken-meat-processing": 0.4},
#                 max_daily_movements=1,
#             )

#             all_properties.append(new_p)

#     for region in chicken_meat_regions_medium:
#         print(region)
#         region_only = get_region_shape(region)
#         expanded_region = expand_region(region_only, km=50)

#         property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
#             int(np.ceil(num_properties_in_regions["medium"] / len(chicken_meat_regions_medium))),
#             expanded_region,
#             average_property_ha=100,
#         )

#         chicken_meat_property_coordinates.extend(property_coordinates)
#         chicken_meat_property_polygons.extend(property_polygons)
#         chicken_meat_property_areas.extend(property_areas)

#         occupied_regions.extend(property_polygons)

#         for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
#             new_p = property_specific_initialisation_animals_no_neighbours(
#                 coordinates,
#                 p_polygon,
#                 p_area,
#                 wind_radius=5,
#                 animal_type="chicken",
#                 premises_type="chicken-meat-farm",
#                 num_animals=100,
#                 movement_freq=1,
#                 movement_probability=0.5,
#                 movement_prop_animals=0.2,
#                 allowed_movement={"chicken-meat-farm": 0.6, "chicken-meat-processing": 0.4},
#                 max_daily_movements=1,
#             )

#             all_properties.append(new_p)

#     for region in chicken_meat_regions_small:
#         print(region)
#         region_only = get_region_shape(region)
#         expanded_region = expand_region(region_only, km=50)

#         property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
#             int(np.ceil(num_properties_in_regions["small"] / len(chicken_meat_regions_small))),
#             expanded_region,
#             average_property_ha=50,
#         )

#         chicken_meat_property_coordinates.extend(property_coordinates)
#         chicken_meat_property_polygons.extend(property_polygons)
#         chicken_meat_property_areas.extend(property_areas)

#         occupied_regions.extend(property_polygons)

#         for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
#             new_p = property_specific_initialisation_animals_no_neighbours(
#                 coordinates,
#                 p_polygon,
#                 p_area,
#                 wind_radius=5,
#                 animal_type="chicken",
#                 premises_type="chicken-meat-farm",
#                 num_animals=10,
#                 movement_freq=1,
#                 movement_probability=0.5,
#                 movement_prop_animals=0.2,
#                 allowed_movement={"chicken-meat-farm": 0.6, "chicken-meat-processing": 0.4},
#                 max_daily_movements=1,
#             )

#             all_properties.append(new_p)

#     # TODO very small - in areas 100 km around the prior regions, for simplicity..., with less than 20 chickens
#     # TODO add in very small properties scattered across the landscape (e.g. with <20 chickens) more generally
#     # such that it avoids all the prior areas

#     # add in the processing plants
#     for region in processing_plant_locations:
#         print(region)
#         region_only = get_region_shape(region)
#         expanded_region = expand_region(region_only, km=50)

#         property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
#             1, expanded_region, average_property_ha=50, excluded_regions=occupied_regions  # one per region
#         )

#         processing_chicken_meat_property_coordinates.extend(property_coordinates)
#         processing_chicken_meat_property_polygons.extend(property_polygons)
#         processing_chicken_meat_property_areas.extend(property_areas)

#         occupied_regions.extend(property_polygons)

#         for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
#             new_p = property_specific_initialisation_animals_no_neighbours(
#                 coordinates,
#                 p_polygon,
#                 p_area,
#                 wind_radius=5,
#                 animal_type="chicken",
#                 premises_type="chicken-meat-processing",
#                 num_animals=1000,
#                 movement_freq=1,
#                 movement_probability=0.5,
#                 movement_prop_animals=0.2,
#                 allowed_movement={},
#                 max_daily_movements=1,
#             )

#             all_properties.append(new_p)

#     # TODO - some kind of death sink that removes processed chickens - and similarly, a process that generates more chickens

#     # https://www.poultryhub.org/production/meat-chicken-broiler-industry
#     # 40,000 chickens per shet, 3-10 sheds per farm

#     # CHICKEN EGG
#     # can't really find much information, I'll just make them in the same area as chicken meat for now.
#     # TODO: improve!!!

#     chicken_egg_property_coordinates = []
#     chicken_egg_property_polygons = []
#     chicken_egg_property_areas = []

#     processing_chicken_egg_property_coordinates = []
#     processing_chicken_egg_property_polygons = []
#     processing_chicken_egg_property_areas = []

#     for region in chicken_meat_regions_large:  # note - using chicken meat regions for now
#         print(region)
#         region_only = get_region_shape(region)
#         expanded_region = expand_region(region_only, km=50)
#         property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
#             int(np.ceil(num_properties_in_regions["large"] / len(chicken_meat_regions_large))),
#             expanded_region,
#             average_property_ha=300,
#             excluded_regions=occupied_regions,
#         )

#         chicken_egg_property_coordinates.extend(property_coordinates)
#         chicken_egg_property_polygons.extend(property_polygons)
#         chicken_egg_property_areas.extend(property_areas)

#         occupied_regions.extend(property_polygons)

#         for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
#             new_p = property_specific_initialisation_animals_no_neighbours(
#                 coordinates,
#                 p_polygon,
#                 p_area,
#                 wind_radius=5,
#                 animal_type="chicken",
#                 premises_type="chicken-egg-farm",
#                 num_animals=1000,
#                 movement_freq=1,
#                 movement_probability=0.5,
#                 movement_prop_animals=0.2,
#                 allowed_movement={"chicken-egg-farm": 0.6, "chicken-egg-processing": 0.4},
#                 max_daily_movements=1,
#             )

#             all_properties.append(new_p)

#     for region in chicken_meat_regions_medium:
#         print(region)
#         region_only = get_region_shape(region)
#         expanded_region = expand_region(region_only, km=50)

#         property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
#             int(np.ceil(num_properties_in_regions["medium"] / len(chicken_meat_regions_medium))),
#             expanded_region,
#             average_property_ha=100,
#             excluded_regions=occupied_regions,
#         )

#         chicken_egg_property_coordinates.extend(property_coordinates)
#         chicken_egg_property_polygons.extend(property_polygons)
#         chicken_egg_property_areas.extend(property_areas)

#         occupied_regions.extend(property_polygons)

#         for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
#             new_p = property_specific_initialisation_animals_no_neighbours(
#                 coordinates,
#                 p_polygon,
#                 p_area,
#                 wind_radius=5,
#                 animal_type="chicken",
#                 premises_type="chicken-egg-farm",
#                 num_animals=100,
#                 movement_freq=1,
#                 movement_probability=0.5,
#                 movement_prop_animals=0.2,
#                 allowed_movement={"chicken-egg-farm": 0.6, "chicken-egg-processing": 0.4},
#                 max_daily_movements=1,
#             )

#             all_properties.append(new_p)

#     for region in chicken_meat_regions_small:
#         print(region)
#         region_only = get_region_shape(region)
#         expanded_region = expand_region(region_only, km=50)

#         property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
#             int(np.ceil(num_properties_in_regions["small"] / len(chicken_meat_regions_small))),
#             expanded_region,
#             average_property_ha=50,
#             excluded_regions=occupied_regions,
#         )

#         chicken_egg_property_coordinates.extend(property_coordinates)
#         chicken_egg_property_polygons.extend(property_polygons)
#         chicken_egg_property_areas.extend(property_areas)

#         occupied_regions.extend(property_polygons)

#         for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
#             new_p = property_specific_initialisation_animals_no_neighbours(
#                 coordinates,
#                 p_polygon,
#                 p_area,
#                 wind_radius=5,
#                 animal_type="chicken",
#                 premises_type="chicken-egg-farm",
#                 num_animals=10,
#                 movement_freq=1,
#                 movement_probability=0.5,
#                 movement_prop_animals=0.2,
#                 allowed_movement={"chicken-egg-farm": 0.6, "chicken-egg-processing": 0.4},
#                 max_daily_movements=1,
#             )

#             all_properties.append(new_p)

#     # TODO very small - in areas 100 km around the prior regions, for simplicity..., with less than 20 chickens
#     # TODO add in very small properties scattered across the landscape (e.g. with <20 chickens) more generally
#     # such that it avoids all the prior areas

#     # add in the processing plants
#     for region in processing_plant_locations:
#         print(region)
#         region_only = get_region_shape(region)
#         expanded_region = expand_region(region_only, km=50)

#         property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
#             1, expanded_region, average_property_ha=50, excluded_regions=occupied_regions  # assign one per region
#         )

#         processing_chicken_egg_property_coordinates.extend(property_coordinates)
#         processing_chicken_egg_property_polygons.extend(property_polygons)
#         processing_chicken_egg_property_areas.extend(property_areas)

#         occupied_regions.extend(property_polygons)

#         for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
#             new_p = property_specific_initialisation_animals_no_neighbours(
#                 coordinates,
#                 p_polygon,
#                 p_area,
#                 wind_radius=5,
#                 animal_type="chicken",
#                 premises_type="chicken-egg-processing",
#                 num_animals=100,
#                 movement_freq=1,
#                 movement_probability=0.5,
#                 movement_prop_animals=0.2,
#                 allowed_movement={},
#                 max_daily_movements=1,
#             )

#             all_properties.append(new_p)

#     # DAIRY CATTLE

#     # TODO - check naming in LGA / data files
#     dairy_cattle_NSW = [
#         "Tweed",
#         "Lismore",
#         "Kyogle",
#         "Richmond Valley",
#         "Clarence Valley",
#         "Coffs Harbour",
#         "Bellingen",
#         "Nambucca Valley",
#         "Kempsey",
#         "Port Macquarie-Hastings",
#         "Mid-Coast",
#         "Dungog",
#         "Port Stephens",
#         "Tamworth",  # "Tamworth Regional"
#         "Walcha",
#         "Upper Hunter",
#         "Muswellbrook",
#         "Singleton",
#         "Maitland",
#         "Lachlan",
#         "Forbes",
#         "Dubbo",  # "Dubbo Regional"
#         "Cabonne",
#         "Cowra",
#         "Blayney",
#         "Bathurst",  # "Bathurst Regional"
#         "Liverpool",
#         "Camden",
#         "Wollondilly",
#         "Wingecarribee",
#         "Shellharbour",
#         "Kiama",
#         "Shoalhaven",
#         "Eurobodalla",
#         "Bega Valley",
#         "Snowy Valleys",
#         "Wagga Wagga",
#         "Albury",
#         "Federation",
#         "Murrumbidgee",
#         "Berrigan",
#         "Edward River",
#         "Murray River",
#     ]

#     dairy_NSW_processing = [
#         "Casino",
#         "South Lismore",
#         "Raleigh",
#         "Wauchope",
#         "Wagga Wagga",
#         "Bega",
#         "Penrith",
#         "Erskine Park",
#         "Winston Hills",
#         "Wetherill Park",
#         "Lidcombe",
#         "Ingleburn",
#         "Smeaton Grange",
#         "Albury",
#     ]

#     dairy_QLD = [
#         "Scenic Rim",
#         "Southern Downs",
#         "Toowoomba",
#         "Lockyer Valley",
#         "Ipswich",
#         "Logan",
#         "Western Downs",
#         "South Burnett",
#         "Somerset",
#         "Sunshine Coast",
#         "Moreton Bay",
#         "Gympie",
#         "Fraser Coast",
#         "Gladstone",
#         "Bundaberg",
#         "North Burnett",
#         "Mackay",
#         "Douglas",
#         "Tablelands",  #  "Atherton Tablelands" not entirely clear about this i.e. whether it'll appear as an LGA or other kind of region
#     ]

#     dairy_QLD_processing = [
#         "Malanda",
#         "Crestmead",
#         "South Brisbane",
#         "Byron Bay",
#         "Labrador",
#         "Beaudesert",
#         "Toowoomba",
#         "Gold Coast",
#     ]

#     dairy_property_coordinates = []
#     dairy_property_polygons = []
#     dairy_property_areas = []

#     processing_dairy_property_coordinates = []
#     processing_dairy_property_polygons = []
#     processing_dairy_property_areas = []

#     for region in dairy_cattle_NSW:
#         print(region)
#         region_only = get_region_shape(region)
#         expanded_region = expand_region(region_only, km=50)
#         property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
#             10,
#             expanded_region,
#             average_property_ha=500,
#             excluded_regions=occupied_regions,
#         )

#         dairy_property_coordinates.extend(property_coordinates)
#         dairy_property_polygons.extend(property_polygons)
#         dairy_property_areas.extend(property_areas)

#         occupied_regions.extend(property_polygons)

#         for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
#             new_p = property_specific_initialisation_animals_no_neighbours(
#                 coordinates,
#                 p_polygon,
#                 p_area,
#                 wind_radius=5,
#                 animal_type="cow",
#                 premises_type="dairy-farm",
#                 num_animals=1000,
#                 movement_freq=1,
#                 movement_probability=0.5,
#                 movement_prop_animals=0.2,
#                 allowed_movement={"dairy-farm": 0.6, "dairy-processing": 0.4},
#                 max_daily_movements=1,
#             )

#             all_properties.append(new_p)

#     for region in dairy_QLD:
#         print(region)
#         region_only = get_region_shape(region)
#         expanded_region = expand_region(region_only, km=50)
#         property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
#             10,
#             expanded_region,
#             average_property_ha=1000,
#             excluded_regions=occupied_regions,
#         )

#         dairy_property_coordinates.extend(property_coordinates)
#         dairy_property_polygons.extend(property_polygons)
#         dairy_property_areas.extend(property_areas)

#         occupied_regions.extend(property_polygons)

#         for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
#             new_p = property_specific_initialisation_animals_no_neighbours(
#                 coordinates,
#                 p_polygon,
#                 p_area,
#                 wind_radius=5,
#                 animal_type="cow",
#                 premises_type="dairy-farm",
#                 num_animals=1000,
#                 movement_freq=1,
#                 movement_probability=0.5,
#                 movement_prop_animals=0.2,
#                 allowed_movement={"dairy-farm": 0.6, "dairy-processing": 0.4},
#                 max_daily_movements=1,
#             )

#             all_properties.append(new_p)

#     processing_dairy_property_coordinates = []
#     processing_dairy_property_polygons = []
#     processing_dairy_property_areas = []

#     # TODO -- oop how does dairy processing actually work, surely only milk will be moved to these locations, rather than the cows?
#     for region in dairy_NSW_processing:
#         print(region)
#         region_only = get_region_shape(region)
#         expanded_region = expand_region(region_only, km=50)

#         property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
#             1, expanded_region, average_property_ha=50, excluded_regions=occupied_regions  # one per region
#         )

#         processing_dairy_property_coordinates.extend(property_coordinates)
#         processing_dairy_property_polygons.extend(property_polygons)
#         processing_dairy_property_areas.extend(property_areas)

#         occupied_regions.extend(property_polygons)

#         for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
#             new_p = property_specific_initialisation_animals_no_neighbours(
#                 coordinates,
#                 p_polygon,
#                 p_area,
#                 wind_radius=5,
#                 animal_type="cow",
#                 premises_type="dairy-processing",
#                 num_animals=10,
#                 movement_freq=1,
#                 movement_probability=0.5,
#                 movement_prop_animals=0.2,
#                 allowed_movement={},
#                 max_daily_movements=1,
#             )

#             all_properties.append(new_p)

#     for region in dairy_QLD_processing:
#         print(region)
#         region_only = get_region_shape(region)
#         expanded_region = expand_region(region_only, km=50)

#         property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
#             1, expanded_region, average_property_ha=50, excluded_regions=occupied_regions  # one per region
#         )

#         processing_dairy_property_coordinates.extend(property_coordinates)
#         processing_dairy_property_polygons.extend(property_polygons)
#         processing_dairy_property_areas.extend(property_areas)

#         occupied_regions.extend(property_polygons)

#         for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
#             new_p = property_specific_initialisation_animals_no_neighbours(
#                 coordinates,
#                 p_polygon,
#                 p_area,
#                 wind_radius=5,
#                 animal_type="cow",
#                 premises_type="dairy-processing",
#                 num_animals=10,
#                 movement_freq=1,
#                 movement_probability=0.5,
#                 movement_prop_animals=0.2,
#                 allowed_movement={},
#                 max_daily_movements=1,
#             )

#             all_properties.append(new_p)

#     with open(output_filename, "wb") as file:
#         pickle.dump(
#             [
#                 all_properties,
#                 chicken_meat_property_coordinates,
#                 processing_chicken_meat_property_coordinates,
#                 chicken_egg_property_coordinates,
#                 processing_chicken_egg_property_coordinates,
#                 dairy_property_coordinates,
#                 processing_dairy_property_coordinates,
#             ],
#             file,
#         )

#     return (
#         all_properties,
#         chicken_meat_property_coordinates,
#         processing_chicken_meat_property_coordinates,
#         chicken_egg_property_coordinates,
#         processing_chicken_egg_property_coordinates,
#         dairy_property_coordinates,
#         processing_dairy_property_coordinates,
#     )


def HPAI_setup_part_2(
    all_properties,
    max_movement_km=500,  # 500km max movement
):

    # ensuring the ids match, init'ing animals at the same time
    for p1 in range(0, len(all_properties)):
        all_properties[p1].id = p1
        all_properties[p1].init_animals(
            None
        )  # init with empty "params", as no parameters are actually used to initialise animals

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
    for i, property_i in enumerate(all_properties):
        max_allowable_movement = max_movement_km
        property_i_neighbours = {}
        for allowed_type in property_i.allowed_movement.keys():
            property_i_neighbours[allowed_type] = []

        if property_i.type == "abbatoir":
            # abbatoirs don't move animals to any other property
            property_i.movement_neighbours = property_i_neighbours
        else:
            for j, property_j in enumerate(all_properties):
                if i == j:
                    continue
                if property_j.type in property_i_neighbours and (
                    (property_j.animal_type == property_i.animal_type)
                    or (
                        property_j.type == "abbatoir"
                        and property_j.animal_type == "poultry"
                        and property_i.animal_type == "chicken"
                    )
                ):
                    # poultry abbatoir can accept chickens and poultry as animal types
                    distance = spatial_functions.quick_distance_haversine(
                        property_i.coordinates,
                        property_j.coordinates,
                    )

                    if distance < max_allowable_movement and random.uniform(0, 1) < 0.2:
                        property_i_neighbours[property_j.type].append(j)

            property_i.movement_neighbours = property_i_neighbours

    return all_properties
