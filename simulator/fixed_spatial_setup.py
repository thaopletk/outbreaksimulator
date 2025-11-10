""" Fixed spatial setup

    This script generates random properties (i.e. farms) across the landscape, in latitude,longitude coordinates and areas in hectares and distances in kilometers (where relevant), based on input animal type, in known hard-coded regions, and with taking in AADIS data.

"""

import os
import simulator.spatial_functions as spatial_functions


def fixed_spatial_setup(disease="FMD", AADIS=True):

    if disease == "FMD" and AADIS == True:
        FMD_AADIS_input_setup()
    elif disease == "HPAI" and AADIS == False:
        HPAI_setup()


def FMD_AADIS_input_setup():
    data_folder = os.path.join(os.path.dirname(__file__), "..", "data", "AADIS_derived_data")
    pass


def HPAI_setup():
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
        "Perth (WA)",
        "Mount Barker (WA)",
        "Adelaide",
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
    chicken_meat_regions_medium = ["Geelong", "Tamworth", "Bendigo", "Beresfield"]
    chicken_meat_regions_small = [
        "Thomastown",
        "Mareeba",
        "Somerville (Vic.)",
        "Sassafras (Vic.)",
        "Hobart",
        "Port Wakefield",
        "Murray Bridge",
        "Goulburn",
        "Nagambie",
        "Melbourne",
        "Mornington Peninsula",
        "Devonport",
        "Launceston",
        "Newcastle",
        "Redland Bay",
        "Two Wells",
        "Byron Bay",
    ]

    processing_plant_locations = [
        "Perth (WA)",
        "Perth (WA)",
        "Mount Barker (WA)",
        "Mareeba",
        "Adelaide",
        "Adelaide",
        "Adelaide",
        "Brisbane",
        "Mount Cotton",
        "Inglewood (L) (Qld)",
        "Tamworth",
        "Beresfield",
        "Galston",
        "Girraween (NSW)",
        "Griffith",
        "Bendigo",
        "Thomastown",
        "Geelong",
        "Somerville (Vic.)",
        "Sassafras (Vic.)",
        "Hobart",
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

    for region in chicken_meat_regions_large:
        print(region)
        region_only = get_region_shape(region)

    for region in chicken_meat_regions_medium:
        print(region)
        region_only = get_region_shape(region)

    for region in chicken_meat_regions_small:
        print(region)
        region_only = get_region_shape(region)

    # add in very small properties scattered across the landscape (e.g. with <20 chickens)

    # https://www.poultryhub.org/production/meat-chicken-broiler-industry
    # 40,000 chickens per shet, 3-10 sheds per farm

    # CHICKEN EGG

    # DAIRY CATTLE

    pass
