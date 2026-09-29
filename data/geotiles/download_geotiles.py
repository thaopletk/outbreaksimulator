import contextily as ctx

import os
import json

with open(os.path.join(os.path.dirname(__file__), "keys.json"), "r") as file:
    keys = json.load(file)

# format
# {
#     "OpenStreetMap": { "User-Agent": "HPAIProject (EMAIL)" },
#     "CartoDB": { "API_key": "KEY" }
# }

state = "VIC"
# state = "EasternAustralia"
# state = "Australia"

if state == "NSW":
    # Boundaries for NSW
    xrange = [140, 155]
    yrange = [-38, -28]
elif state == "QLD":
    # Boundaries for QLD
    xrange = [140, 155]
    yrange = [-30, -10]
elif state == "VIC":
    xrange = [140.0, 151.0]
    yrange = [-39.5, -33.5]
elif state == "EasternAustralia":
    xrange = [140, 155]
    yrange = [-39.5, -10]
elif state == "Australia":
    xrange = [110, 155]
    yrange = [-45, -10]
else:
    raise ValueError(f"{state} state not expected")

# limits for the figures
xlims = [
    round(xrange[0], 2) - 0.005,
    round(xrange[1], 2) + 0.005,
]
ylims = [
    round(yrange[0], 1) - 0.05,
    round(yrange[1], 1) + 0.05,
]


geo_tile_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "geotiles", f"{state}.tif")
if not os.path.exists(geo_tile_path):
    img, ext = ctx.bounds2raster(xlims[0], ylims[0], xlims[1], ylims[1], geo_tile_path, ll=True, zoom=6)

ctx_header = keys["OpenStreetMap"]
geo_tile_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "geotiles", f"{state}_Mapnik.tif")
if not os.path.exists(geo_tile_path):
    img, ext = ctx.bounds2raster(
        xlims[0], ylims[0], xlims[1], ylims[1], geo_tile_path, ll=True, source=ctx.providers.OpenStreetMap.Mapnik, headers=ctx_header, zoom=6
    )

geo_tile_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "geotiles", f"{state}_Mapnik_10.tif")
if not os.path.exists(geo_tile_path):
    img, ext = ctx.bounds2raster(
        xlims[0], ylims[0], xlims[1], ylims[1], geo_tile_path, ll=True, source=ctx.providers.OpenStreetMap.Mapnik, headers=ctx_header, zoom=10
    )


geo_tile_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "geotiles", f"{state}_CartoDBPositron.tif")
API_key = keys["CartoDB"]["API_key"]
print(ctx.providers.CartoDB.Positron(key=API_key))
if not os.path.exists(geo_tile_path):
    img, ext = ctx.bounds2raster(
        xlims[0],
        ylims[0],
        xlims[1],
        ylims[1],
        geo_tile_path,
        ll=True,
        source="https://basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}.png?key=" + API_key,
        zoom=6,
    )
