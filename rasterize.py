# script rasterizzazione vettoriale con openEO
import geopandas as gpd
import matplotlib.pyplot as plt
import rasterio
from rasterio import features
from rasterio.enums import MergeAlg
from rasterio.plot import show
from numpy import int16


# Lettura vettoriale
vector = gpd.read_file(r"../_static/e_vector_shapefiles/sf_bay_counties/sf_bay_counties.shp")

# lista delle geometrie di tutte le features nel vettoriale
geom = [shapes for shapes in vector.geometry]

# Lettura raster che servirà per il riferimento finale
raster = rasterio.open(r"../_static/e_raster/bay-area-wells_kde_sklearn.tif")

# create a numeric unique value for each row
vector['id'] = range(0,len(vector))

# create tuples of geometry, value pairs, where value is the attribute value you want to burn
geom_value = ((geom,value) for geom, value in zip(vector.geometry, vector['id']))

# Rasterize vector using the shape and transform of the raster
rasterized = features.rasterize(geom_value,
                                out_shape = raster.shape,
                                transform = raster.transform,
                                all_touched = True,
                                fill = -5,   # background value
                                merge_alg = MergeAlg.replace,
                                dtype = int16)

# Plot raster
fig, ax = plt.subplots(1, figsize = (10, 10))
show(rasterized, ax = ax)
plt.gca().invert_yaxis()


######secondo metodo
import rasterio
import rasterio.features
from shapely.geometry import Polygon
from osgeo import gdal

max_gdal_cache_gb=64

# Create a global rasterio environment
global_env = rasterio.Env(GDAL_CACHEMAX=int(max_gdal_cache_gb * 1e9))

with global_env:
    # Get the current cache size
    rasterio_cache_size = gdal.GetConfigOption("GDAL_CACHEMAX")
    print(f"Rasterio cache size: {rasterio_cache_size} bytes")


p1 = Polygon([[0,0], [32000,0], [32000,32000], [0,0]])
out_shape = (32000, 32000)
# The default transform is fine here
with global_env:
    r = rasterio.features.rasterize([p1], out_shape=out_shape)