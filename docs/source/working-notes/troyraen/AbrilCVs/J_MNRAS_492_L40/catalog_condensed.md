# docs/source/working-notes/troyraen/AbrilCVs/J_MNRAS_492_L40/catalog_condensed.md

## Create `catalog_condensed.dat`

- Calculate HEALPix indexes of CV catalog.
- Save index and a subset of data columns to `catalog_condensed.dat` in a format that can be easily loaded by `pandas`.


```python
import os
import pandas as pd
from astropy.coordinates import ICRS, SkyCoord
fcat = "catalog.dat"
fcat_condensed = "catalog_condensed.dat"

def radec_to_skycoord(row):
    return SkyCoord(row["RAdeg"], row["DEdeg"], frame='icrs', unit='deg')
def skycoord_to_healpix(row):
    return hp.skycoord_to_healpix(row['SkyCoord'])

# load Abril CV catalog
names = [
    "Name",
    "AltName",
    "RAdeg",
    "DEdeg",
    "Type1",
    "Type2",
    "mag1",
    "Orb.Per",
    "Outburst",
    "MagRange",
    "SpType2",
    "SpType1",
    "Source",
    "RAGdeg",
    "e_RAGdeg",
    "DEGdeg",
    "e_DEGdeg",
    "rest",
    "b_rest",
    "B_rest",
    "rlen",
    "plx",
    "e_plx",
    "pmRA",
    "e_pmRA",
    "pmDE",
    "e_pmDE",
    "FG",
    "e_FG",
    "Gmag",
    "GMAG",
    "FBP",
    "e_FBP",
    "BPmag",
    "FRP",
    "e_FRP",
    "RPmag",
    "BP-RP",
    "Teff",
]
abrildf = pd.read_fwf(fcat, names=names, header=None, index=None)

# instantiate pixelization
n = 17
nside = 2**n
frame = ICRS()
order = 'nested'
hp = HEALPix(nside=nside, order=order, frame=frame)

# calculate indexes
abrildf['SkyCoord'] = abrildf.apply(radec_to_skycoord, axis=1)
abrildf[f'HEALPix_{n}_idx'] = abrildf.apply(skycoord_to_healpix, axis=1)

# save csv
keep_cols = ['Name', 'RAdeg', 'DEdeg', f'HEALPix_{n}_idx']
abrildf[keep_cols].to_csv(fcat_condensed, index=False)
```
