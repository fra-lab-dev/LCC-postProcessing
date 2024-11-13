
#ripulitura di cluster della dimensione di 2 pixel (o inferiore) da un raster

import numpy as np
import rasterio
from rasterio.features import sieve


with rasterio.open('tests/data/shade.tif') as src:

    # Sieve out features 1 pixels or smaller.
    sieved = sieve(src, 2, out=np.zeros(src.shape, src.dtypes[0]))

    # Write out the sieved raster.
    kwargs = src.profile
    with rasterio.open('sieved.tif', 'w', **kwargs) as dst:
        dst.write(sieved, indexes=1)