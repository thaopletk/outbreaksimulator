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


def fixed_spatial_setup(xrange, yrange, folder_path_main, disease="FMD", AADIS=True):

    if disease == "FMD" and AADIS == True:
        FMD_AADIS_input_setup()
    elif disease == "HPAI" and AADIS == False:
        HPAI_setup(
            xrange,
            yrange,
            folder_path_main,
        )


def FMD_AADIS_input_setup():
    data_folder = os.path.join(os.path.dirname(__file__), "..", "data", "AADIS_derived_data")
    pass


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
    dairy_property_coordinates,
    processing_dairy_property_coordinates,
    xlims,
    ylims,
    folder_path,
):
    """Plot property boundaries"""
    fig, ax = plt.subplots(1, 1, figsize=(20, 20))  # ,figsize=(10,12)

    #         long, lat = premise.coordinates
    # curr_farm = Point(long, lat) -> geometries?

    for geometries, marker, markerlabel in [
        [chicken_meat_property_coordinates, "$\U0001F414$", "Chicken Meat"],
        [processing_chicken_meat_property_coordinates, "$\U0001F3ED$", "Chicken Meat Processing"],
        [chicken_egg_property_coordinates, "$\U0001F95A$", "Chicken Egg"],
        [processing_chicken_egg_property_coordinates, "$\U0001F4E6$", "Chicken Egg Processing"],
        [dairy_property_coordinates, "$\U0001F404$", "Dairy Farm"],
        [processing_dairy_property_coordinates, "$\U0001F95B$", "Dairy Processing"],
    ]:

        geo_df = gpd.GeoDataFrame(geometry=geometries)
        geo_df.crs = {"init": "epsg:4326"}
        # plot the marker
        ax = geo_df.plot(ax=ax, markersize=10, marker=marker, label=markerlabel)

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
    #       fancybox=True, shadow=True, ncol=5,fontsize=18)

    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=14)

    file_name = "property_locations_base_map.png"

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
    movement_freq,
    movement_probability,
    movement_prop_animals,
    allowed_movement,
    max_daily_movements,
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
    except:
        time.sleep(60.0)
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

    return new_p


def HPAI_setup(
    xrange,
    yrange,
    folder_path_main,
    num_properties_in_regions={"large": 20, "medium": 50, "small": 100, "very_small": 100},
):
    # Australia_gdf = spatial_setup.get_Australia_shape()
    Australia_shape = spatial_setup.Australia_shape()
    UCL_gdf = spatial_functions.get_UCL_gdf()
    SAL_gdf = spatial_functions.get_SALs_gdf()
    SA4_gdf = spatial_functions.get_SA4_gdf()
    LGA_gdf = spatial_functions.get_LGA_gdf()

    # CHICKEN MEAT

    # https://chicken.org.au/our-product/facts-and-figures/
    # https://chicken.org.au/wp-content/uploads/2024/09/Industry-Map-8.png
    # https://chicken.org.au/wp-content/uploads/2024/09/Industry-Map-2.png
    # https://www.poultryhub.org/production/meat-chicken-broiler-industry

    # use a 50-100 km radius around these areas
    chicken_meat_regions_large = [
        # "Perth (WA)",
        # "Mount Barker (WA)",
        # "Adelaide",
        "Brisbane",
        "Mount Cotton",
        "Inglewood (L) (Qld)",
        "Galston",
        "Girraween (NSW)",
        "Griffith",
        "Hunter Valley exc Newcastle",
        "Sydney",
        "Mangrove Mountain",
    ]
    chicken_meat_regions_medium = [
        # "Geelong",
        "Tamworth",
        # "Bendigo",
        "Beresfield",
    ]
    chicken_meat_regions_small = [
        # "Thomastown",
        "Mareeba",
        # "Somerville (Vic.)",
        # "Sassafras (Vic.)",
        # "Hobart",
        # "Port Wakefield",
        # "Murray Bridge",
        "Goulburn",
        # "Nagambie",
        # "Melbourne",
        # "Mornington Peninsula",
        # "Devonport",
        # "Launceston",
        "Newcastle",
        "Redland Bay",
        "Two Wells",
        "Byron Bay",
    ]

    # TODO: assign these as actual locations
    processing_plant_locations = [
        # "Perth (WA)",
        # "Perth (WA)",
        # "Mount Barker (WA)",
        "Mareeba",
        # "Adelaide",
        # "Adelaide",
        # "Adelaide",
        "Brisbane",
        "Mount Cotton",
        "Inglewood (L) (Qld)",
        "Tamworth",
        "Beresfield",
        "Galston",
        "Girraween (NSW)",
        "Griffith",
        # "Bendigo",
        # "Thomastown",
        # "Geelong",
        # "Somerville (Vic.)",
        # "Sassafras (Vic.)",
        # "Hobart",
    ]

    def get_region_shape(region):
        region_only = UCL_gdf.loc[UCL_gdf["UCL_NAME21"] == region, :]
        try:
            region_shape = list(region_only["geometry"])[0]
        except:
            region_only = SAL_gdf.loc[SAL_gdf["SAL_NAME21"] == region, :]
            try:
                region_shape = list(region_only["geometry"])[0]
            except:
                region_only = SA4_gdf.loc[SA4_gdf["SA4_NAME21"] == region, :]
                try:
                    region_shape = list(region_only["geometry"])[0]
                except:
                    region_only = LGA_gdf.loc[LGA_gdf["LGA_NAME24"] == region, :]
                    region_shape = list(region_only["geometry"])[0]

        return region_shape

    def expand_region(region, km=50):
        # expansion 50 km
        minx, miny, maxx, maxy = region.bounds
        lat = (miny + maxy) / 2  # y
        lon = (minx + maxx) / 2  # x
        expanded_region = spatial_functions.geodesic_polygon_buffer(lat, lon, region, km)

        # making sure the region doesn't include the ocean!!!!
        expanded_region = expanded_region.intersection(Australia_shape)

        return expanded_region

    occupied_regions = []
    all_properties = []

    chicken_meat_property_coordinates = []
    chicken_meat_property_polygons = []
    chicken_meat_property_areas = []

    processing_chicken_meat_property_coordinates = []
    processing_chicken_meat_property_polygons = []
    processing_chicken_meat_property_areas = []

    for region in chicken_meat_regions_large:
        print(region)
        region_only = get_region_shape(region)
        expanded_region = expand_region(region_only, km=50)
        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            int(np.ceil(num_properties_in_regions["large"] / len(chicken_meat_regions_large))),
            expanded_region,
            average_property_ha=300,
        )

        chicken_meat_property_coordinates.extend(property_coordinates)
        chicken_meat_property_polygons.extend(property_polygons)
        chicken_meat_property_areas.extend(property_areas)

        occupied_regions.extend(property_polygons)

        for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
            new_p = property_specific_initialisation_animals_no_neighbours(
                coordinates,
                p_polygon,
                p_area,
                wind_radius=5,
                animal_type="chicken",
                premises_type="chicken-meat-farm",
                num_animals=1000,
                movement_freq=1,
                movement_probability=0.5,
                movement_prop_animals=0.2,
                allowed_movement={"chicken-meat-farm": 0.6, "chicken-meat-processing": 0.4},
                max_daily_movements=1,
            )

            all_properties.append(new_p)

    for region in chicken_meat_regions_medium:
        print(region)
        region_only = get_region_shape(region)
        expanded_region = expand_region(region_only, km=50)

        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            int(np.ceil(num_properties_in_regions["medium"] / len(chicken_meat_regions_medium))),
            expanded_region,
            average_property_ha=100,
        )

        chicken_meat_property_coordinates.extend(property_coordinates)
        chicken_meat_property_polygons.extend(property_polygons)
        chicken_meat_property_areas.extend(property_areas)

        occupied_regions.extend(property_polygons)

        for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
            new_p = property_specific_initialisation_animals_no_neighbours(
                coordinates,
                p_polygon,
                p_area,
                wind_radius=5,
                animal_type="chicken",
                premises_type="chicken-meat-farm",
                num_animals=100,
                movement_freq=1,
                movement_probability=0.5,
                movement_prop_animals=0.2,
                allowed_movement={"chicken-meat-farm": 0.6, "chicken-meat-processing": 0.4},
                max_daily_movements=1,
            )

            all_properties.append(new_p)

    for region in chicken_meat_regions_small:
        print(region)
        region_only = get_region_shape(region)
        expanded_region = expand_region(region_only, km=50)

        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            int(np.ceil(num_properties_in_regions["small"] / len(chicken_meat_regions_small))),
            expanded_region,
            average_property_ha=50,
        )

        chicken_meat_property_coordinates.extend(property_coordinates)
        chicken_meat_property_polygons.extend(property_polygons)
        chicken_meat_property_areas.extend(property_areas)

        occupied_regions.extend(property_polygons)

        for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
            new_p = property_specific_initialisation_animals_no_neighbours(
                coordinates,
                p_polygon,
                p_area,
                wind_radius=5,
                animal_type="chicken",
                premises_type="chicken-meat-farm",
                num_animals=10,
                movement_freq=1,
                movement_probability=0.5,
                movement_prop_animals=0.2,
                allowed_movement={"chicken-meat-farm": 0.6, "chicken-meat-processing": 0.4},
                max_daily_movements=1,
            )

            all_properties.append(new_p)

    # TODO very small - in areas 100 km around the prior regions, for simplicity..., with less than 20 chickens
    # TODO add in very small properties scattered across the landscape (e.g. with <20 chickens) more generally
    # such that it avoids all the prior areas

    # add in the processing plants
    for region in processing_plant_locations:
        print(region)
        region_only = get_region_shape(region)
        expanded_region = expand_region(region_only, km=50)

        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            1, expanded_region, average_property_ha=50, excluded_regions=occupied_regions  # one per region
        )

        processing_chicken_meat_property_coordinates.extend(property_coordinates)
        processing_chicken_meat_property_polygons.extend(property_polygons)
        processing_chicken_meat_property_areas.extend(property_areas)

        occupied_regions.extend(property_polygons)

        for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
            new_p = property_specific_initialisation_animals_no_neighbours(
                coordinates,
                p_polygon,
                p_area,
                wind_radius=5,
                animal_type="chicken",
                premises_type="chicken-meat-processing",
                num_animals=1000,
                movement_freq=1,
                movement_probability=0.5,
                movement_prop_animals=0.2,
                allowed_movement={},
                max_daily_movements=1,
            )

            all_properties.append(new_p)

    # TODO - some kind of death sink that removes processed chickens - and similarly, a process that generates more chickens

    # https://www.poultryhub.org/production/meat-chicken-broiler-industry
    # 40,000 chickens per shet, 3-10 sheds per farm

    # CHICKEN EGG
    # can't really find much information, I'll just make them in the same area as chicken meat for now.
    # TODO: improve!!!

    chicken_egg_property_coordinates = []
    chicken_egg_property_polygons = []
    chicken_egg_property_areas = []

    processing_chicken_egg_property_coordinates = []
    processing_chicken_egg_property_polygons = []
    processing_chicken_egg_property_areas = []

    for region in chicken_meat_regions_large:  # note - using chicken meat regions for now
        print(region)
        region_only = get_region_shape(region)
        expanded_region = expand_region(region_only, km=50)
        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            int(np.ceil(num_properties_in_regions["large"] / len(chicken_meat_regions_large))),
            expanded_region,
            average_property_ha=300,
            excluded_regions=occupied_regions,
        )

        chicken_egg_property_coordinates.extend(property_coordinates)
        chicken_egg_property_polygons.extend(property_polygons)
        chicken_egg_property_areas.extend(property_areas)

        occupied_regions.extend(property_polygons)

        for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
            new_p = property_specific_initialisation_animals_no_neighbours(
                coordinates,
                p_polygon,
                p_area,
                wind_radius=5,
                animal_type="chicken",
                premises_type="chicken-egg-farm",
                num_animals=1000,
                movement_freq=1,
                movement_probability=0.5,
                movement_prop_animals=0.2,
                allowed_movement={"chicken-egg-farm": 0.6, "chicken-egg-processing": 0.4},
                max_daily_movements=1,
            )

            all_properties.append(new_p)

    for region in chicken_meat_regions_medium:
        print(region)
        region_only = get_region_shape(region)
        expanded_region = expand_region(region_only, km=50)

        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            int(np.ceil(num_properties_in_regions["medium"] / len(chicken_meat_regions_medium))),
            expanded_region,
            average_property_ha=100,
            excluded_regions=occupied_regions,
        )

        chicken_egg_property_coordinates.extend(property_coordinates)
        chicken_egg_property_polygons.extend(property_polygons)
        chicken_egg_property_areas.extend(property_areas)

        occupied_regions.extend(property_polygons)

        for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
            new_p = property_specific_initialisation_animals_no_neighbours(
                coordinates,
                p_polygon,
                p_area,
                wind_radius=5,
                animal_type="chicken",
                premises_type="chicken-egg-farm",
                num_animals=100,
                movement_freq=1,
                movement_probability=0.5,
                movement_prop_animals=0.2,
                allowed_movement={"chicken-egg-farm": 0.6, "chicken-egg-processing": 0.4},
                max_daily_movements=1,
            )

            all_properties.append(new_p)

    for region in chicken_meat_regions_small:
        print(region)
        region_only = get_region_shape(region)
        expanded_region = expand_region(region_only, km=50)

        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            int(np.ceil(num_properties_in_regions["small"] / len(chicken_meat_regions_small))),
            expanded_region,
            average_property_ha=50,
            excluded_regions=occupied_regions,
        )

        chicken_egg_property_coordinates.extend(property_coordinates)
        chicken_egg_property_polygons.extend(property_polygons)
        chicken_egg_property_areas.extend(property_areas)

        occupied_regions.extend(property_polygons)

        for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
            new_p = property_specific_initialisation_animals_no_neighbours(
                coordinates,
                p_polygon,
                p_area,
                wind_radius=5,
                animal_type="chicken",
                premises_type="chicken-egg-farm",
                num_animals=10,
                movement_freq=1,
                movement_probability=0.5,
                movement_prop_animals=0.2,
                allowed_movement={"chicken-egg-farm": 0.6, "chicken-egg-processing": 0.4},
                max_daily_movements=1,
            )

            all_properties.append(new_p)

    # TODO very small - in areas 100 km around the prior regions, for simplicity..., with less than 20 chickens
    # TODO add in very small properties scattered across the landscape (e.g. with <20 chickens) more generally
    # such that it avoids all the prior areas

    # add in the processing plants
    for region in processing_plant_locations:
        print(region)
        region_only = get_region_shape(region)
        expanded_region = expand_region(region_only, km=50)

        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            1, expanded_region, average_property_ha=50, excluded_regions=occupied_regions  # assign one per region
        )

        processing_chicken_egg_property_coordinates.extend(property_coordinates)
        processing_chicken_egg_property_polygons.extend(property_polygons)
        processing_chicken_egg_property_areas.extend(property_areas)

        occupied_regions.extend(property_polygons)

        for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
            new_p = property_specific_initialisation_animals_no_neighbours(
                coordinates,
                p_polygon,
                p_area,
                wind_radius=5,
                animal_type="chicken",
                premises_type="chicken-egg-processing",
                num_animals=100,
                movement_freq=1,
                movement_probability=0.5,
                movement_prop_animals=0.2,
                allowed_movement={},
                max_daily_movements=1,
            )

            all_properties.append(new_p)

    # DAIRY CATTLE

    # TODO - check naming in LGA / data files
    dairy_cattle_NSW = [
        "Tweed",
        "Lismore",
        "Kyogle",
        "Richmond Valley",
        "Clarence Valley",
        "Coffs Harbour",
        "Bellingen",
        "Nambucca Valley",
        "Kempsey",
        "Port Macquarie-Hastings",
        "Mid-Coast",
        "Dungog",
        "Port Stephens",
        "Tamworth",  # "Tamworth Regional"
        "Walcha",
        "Upper Hunter",
        "Muswellbrook",
        "Singleton",
        "Maitland",
        "Lachlan",
        "Forbes",
        "Dubbo",  # "Dubbo Regional"
        "Cabonne",
        "Cowra",
        "Balyney",
        "Bathurst",  # "Bathurst Regional"
        "Liverpool",
        "Camden",
        "Wollondilly",
        "Wingecarribee",
        "Shellharbour",
        "Kiama",
        "Shoalhaven",
        "Eurobodalla",
        "Bega Valley",
        "Snowy Valleys",
        "Wagga Wagga",
        "Albury",
        "Federation",
        "Murrumbidgee",
        "Berrigan",
        "Edward River",
        "Murray River",
    ]

    dairy_NSW_processing = [
        "Casino",
        "South Lismore",
        "Releigh",
        "Wauchope",
        "Wagga Wagga",
        "Bega",
        "Penrith",
        "Erskine Park",
        "Winston Hills",
        "Wetherill Park",
        "Lidcombe",
        "Ingleburn",
        "Smeaton Grange",
        "Albury",
    ]

    dairy_QLD = [
        "Scenic Rim",
        "Sothern Downs",
        "Toowoomba",
        "Lockyer Valley",
        "Ipswich",
        "Logan",
        "Western Downs",
        "South Burnett",
        "Somerset",
        "Sunshine Coast",
        "Moreton Bay",
        "Gympie",
        "Fraser Coast",
        "Gladstone",
        "Bundaberg",
        "North Burnett",
        "Mackey",
        "Douglas",
        "Tablelands",  #  "Atherton Tablelands" not entirely clear about this i.e. whether it'll appear as an LGA or other kind of region
    ]

    dairy_QLD_processing = [
        "Malanda",
        "Crestmead",
        "South Brisbane",
        "Byron Bay",
        "Labrador",
        "Beaudesert",
        "Toowoomba",
        "Gold Coast",
    ]

    dairy_property_coordinates = []
    dairy_property_polygons = []
    dairy_property_areas = []

    processing_dairy_property_coordinates = []
    processing_dairy_property_polygons = []
    processing_dairy_property_areas = []

    for region in dairy_cattle_NSW:
        print(region)
        region_only = get_region_shape(region)
        expanded_region = expand_region(region_only, km=50)
        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            10,
            expanded_region,
            average_property_ha=500,
            excluded_regions=occupied_regions,
        )

        dairy_property_coordinates.extend(property_coordinates)
        dairy_property_polygons.extend(property_polygons)
        dairy_property_areas.extend(property_areas)

        occupied_regions.extend(property_polygons)

        for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
            new_p = property_specific_initialisation_animals_no_neighbours(
                coordinates,
                p_polygon,
                p_area,
                wind_radius=5,
                animal_type="cow",
                premises_type="dairy-farm",
                num_animals=1000,
                movement_freq=1,
                movement_probability=0.5,
                movement_prop_animals=0.2,
                allowed_movement={"dairy-farm": 0.6, "dairy-processing": 0.4},
                max_daily_movements=1,
            )

            all_properties.append(new_p)

    for region in dairy_QLD:
        print(region)
        region_only = get_region_shape(region)
        expanded_region = expand_region(region_only, km=50)
        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            10,
            expanded_region,
            average_property_ha=1000,
            excluded_regions=occupied_regions,
        )

        dairy_property_coordinates.extend(property_coordinates)
        dairy_property_polygons.extend(property_polygons)
        dairy_property_areas.extend(property_areas)

        occupied_regions.extend(property_polygons)

        for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
            new_p = property_specific_initialisation_animals_no_neighbours(
                coordinates,
                p_polygon,
                p_area,
                wind_radius=5,
                animal_type="cow",
                premises_type="dairy-farm",
                num_animals=1000,
                movement_freq=1,
                movement_probability=0.5,
                movement_prop_animals=0.2,
                allowed_movement={"dairy-farm": 0.6, "dairy-processing": 0.4},
                max_daily_movements=1,
            )

            all_properties.append(new_p)

    processing_dairy_property_coordinates = []
    processing_dairy_property_polygons = []
    processing_dairy_property_areas = []

    # TODO -- oop how does dairy processing actually work, surely only milk will be moved to these locations, rather than the cows?
    for region in dairy_NSW_processing:
        print(region)
        region_only = get_region_shape(region)
        expanded_region = expand_region(region_only, km=50)

        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            1, expanded_region, average_property_ha=50, excluded_regions=occupied_regions  # one per region
        )

        processing_dairy_property_coordinates.extend(property_coordinates)
        processing_dairy_property_polygons.extend(property_polygons)
        processing_dairy_property_areas.extend(property_areas)

        occupied_regions.extend(property_polygons)

        for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
            new_p = property_specific_initialisation_animals_no_neighbours(
                coordinates,
                p_polygon,
                p_area,
                wind_radius=5,
                animal_type="cow",
                premises_type="dairy-processing",
                num_animals=10,
                movement_freq=1,
                movement_probability=0.5,
                movement_prop_animals=0.2,
                allowed_movement={},
                max_daily_movements=1,
            )

            all_properties.append(new_p)

    for region in dairy_QLD_processing:
        print(region)
        region_only = get_region_shape(region)
        expanded_region = expand_region(region_only, km=50)

        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            1, expanded_region, average_property_ha=50, excluded_regions=occupied_regions  # one per region
        )

        processing_dairy_property_coordinates.extend(property_coordinates)
        processing_dairy_property_polygons.extend(property_polygons)
        processing_dairy_property_areas.extend(property_areas)

        occupied_regions.extend(property_polygons)

        for coordinates, p_polygon, p_area in zip(property_coordinates, property_polygons, property_areas):
            new_p = property_specific_initialisation_animals_no_neighbours(
                coordinates,
                p_polygon,
                p_area,
                wind_radius=5,
                animal_type="cow",
                premises_type="dairy-processing",
                num_animals=10,
                movement_freq=1,
                movement_probability=0.5,
                movement_prop_animals=0.2,
                allowed_movement={},
                max_daily_movements=1,
            )

            all_properties.append(new_p)

    # plot that actually shows the locations of different facilities
    plot_map_land_HPAI(
        chicken_meat_property_coordinates,
        processing_chicken_meat_property_coordinates,
        chicken_egg_property_coordinates,
        processing_chicken_egg_property_coordinates,
        dairy_property_coordinates,
        processing_dairy_property_coordinates,
        xrange,
        yrange,
        folder_path_main,
    )

    # TODO assign animal numbers based on property size

    # TODO: assign wind neighbours, but still return property type information! ... though maybe I can do this all in one go, since I never use the adjacency matrix anyway?
    # (
    #     chicken_meat_adjacency_matrix,
    #     chicken_meat_neighbour_pairs,
    #     chicken_meat_neighbourhoods,
    #     chicken_meat_property_polygons_puffed,
    # ) = spatial_setup.assign_neighbours_with_land(
    #     chicken_meat_property_coordinates, chicken_meat_property_polygons, len(chicken_meat_property_coordinates), r=8
    # )
