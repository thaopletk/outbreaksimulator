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
        print(i)
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


def HPAI_setup(
    xrange,
    yrange,
    folder_path_main,
    num_properties_in_regions={"large": 20, "medium": 50, "small": 100, "very_small": 100},
):
    UCL_gdf = spatial_functions.get_UCL_gdf()
    SAL_gdf = spatial_functions.get_SALs_gdf()
    SA4_gdf = spatial_functions.get_SA4_gdf()

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
                region_shape = list(region_only["geometry"])[0]
        return region_shape

    def expand_region(region, km=50):
        # expansion 50 km
        minx, miny, maxx, maxy = region.bounds
        lat = (miny + maxy) / 2  # y
        lon = (minx + maxx) / 2  # x
        expanded_region = spatial_functions.geodesic_polygon_buffer(lat, lon, region, km)

        return expanded_region

    chicken_meat_property_coordinates = []
    chicken_meat_property_polygons = []
    chicken_meat_property_areas = []

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

    # TODO very small - in areas 100 km around the prior regions, for simplicity..., with less than 20 chickens
    # TODO add in very small properties scattered across the landscape (e.g. with <20 chickens) more generally
    # such that it avoids all the prior areas

    # TODO - add in the processing plants

    # https://www.poultryhub.org/production/meat-chicken-broiler-industry
    # 40,000 chickens per shet, 3-10 sheds per farm

    # CHICKEN EGG
    # can't really find much information, I'll just make them in the same area as chicken meat for now.
    # TODO: improve!!!

    chicken_egg_property_coordinates = []
    chicken_egg_property_polygons = []
    chicken_egg_property_areas = []

    for region in chicken_meat_regions_large:  # note - using chicken meat regions for now
        print(region)
        region_only = get_region_shape(region)
        expanded_region = expand_region(region_only, km=50)
        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            int(np.ceil(num_properties_in_regions["large"] / len(chicken_meat_regions_large))),
            expanded_region,
            average_property_ha=300,
            excluded_regions=chicken_meat_property_polygons,
        )

        chicken_egg_property_coordinates.extend(property_coordinates)
        chicken_egg_property_polygons.extend(property_polygons)
        chicken_egg_property_areas.extend(property_areas)

    for region in chicken_meat_regions_medium:
        print(region)
        region_only = get_region_shape(region)
        expanded_region = expand_region(region_only, km=50)

        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            int(np.ceil(num_properties_in_regions["medium"] / len(chicken_meat_regions_medium))),
            expanded_region,
            average_property_ha=100,
            excluded_regions=chicken_meat_property_polygons,
        )

        chicken_egg_property_coordinates.extend(property_coordinates)
        chicken_egg_property_polygons.extend(property_polygons)
        chicken_egg_property_areas.extend(property_areas)

    for region in chicken_meat_regions_small:
        print(region)
        region_only = get_region_shape(region)
        expanded_region = expand_region(region_only, km=50)

        property_coordinates, property_polygons, property_areas = assign_property_locations_in_region(
            int(np.ceil(num_properties_in_regions["small"] / len(chicken_meat_regions_small))),
            expanded_region,
            average_property_ha=50,
            excluded_regions=chicken_meat_property_polygons,
        )

        chicken_egg_property_coordinates.extend(property_coordinates)
        chicken_egg_property_polygons.extend(property_polygons)
        chicken_egg_property_areas.extend(property_areas)

    # TODO very small - in areas 100 km around the prior regions, for simplicity..., with less than 20 chickens
    # TODO add in very small properties scattered across the landscape (e.g. with <20 chickens) more generally
    # such that it avoids all the prior areas

    # TODO - add in the processing plants

    # DAIRY CATTLE

    # TODO - check naming in LGA / data files
    dairy_cattle_NSW = [
        "Tweed",
        "Lismore",
        "Kyogle",
        "Richmond Valley",
        "Clarence valley",
        "Coffs Harbour",
        "Bellingen",
        "Nambucca Valley",
        "Kempsey",
        "Port Macquarie-Hastings",
        "Mid-Coast",
        "Dungog",
        "Port Stephens",
        "Tamworth Regional",
        "Walcha",
        "Upper Hunter",
        "Muswellbrook",
        "Singleton",
        "Maitland",
        "Lachlan",
        "Forbes",
        "Dubbo Regional",
        "Cabonne",
        "Cowra",
        "Balyney",
        "Bathurst Regional",
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
        "Atherton Tablelands",  # not entirely clear about this i.e. whether it'll appear as an LGA or other kind of region
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

    # TODO: assign wind neighbours, but still return property type information!
    # (
    #     chicken_meat_adjacency_matrix,
    #     chicken_meat_neighbour_pairs,
    #     chicken_meat_neighbourhoods,
    #     chicken_meat_property_polygons_puffed,
    # ) = spatial_setup.assign_neighbours_with_land(
    #     chicken_meat_property_coordinates, chicken_meat_property_polygons, len(chicken_meat_property_coordinates), r=8
    # )

    # TODO: make a plot that actually shows the locations of different facilities
    # output.plot_map_land(
    #     property_polygons,
    #     chicken_meat_property_polygons_puffed,
    #     xrange,
    #     yrange,
    #     folder_path_main,
    # )

    # TODO assign animal numbers based on property size
