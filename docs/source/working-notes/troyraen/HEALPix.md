# HEALPix

- [http://healpix.jpl.nasa.gov/](http://healpix.jpl.nasa.gov/)

  - [https://healpix.jpl.nasa.gov/pdf/intro.pdf](https://healpix.jpl.nasa.gov/pdf/intro.pdf)

- [http://adsabs.harvard.edu/abs/2005ApJ...622..759G](http://adsabs.harvard.edu/abs/2005ApJ...622..759G)

- [http://adsabs.harvard.edu/abs/2007MNRAS.381..865C](http://adsabs.harvard.edu/abs/2007MNRAS.381..865C)

- [Splitting the Sky - HTM and HEALPix](https://ui.adsabs.harvard.edu/abs/2001misk.conf..638O/abstract)
  ([alt link](https://www.researchgate.net/publication/226874931_Splitting_the_sky_-_HTM_and_HEALPix))

## `astropy-healpix`

[docs](https://astropy-healpix.readthedocs.io/en/latest/)

```bash
pip install --no-deps astropy-healpix
```

```python
import astropy
from astropy import units as u
from astropy.coordinates import ICRS, SkyCoord
from astropy_healpix import HEALPix

# instantiate a HEALPix pixelization
n = 11  # ~3 arcmin^2 pixel area (from O'Mullane fig 6, but note it incorrectly states unit as arcsec^2)
n = 12  # ~0.74 arcmin^2 pixel area
n = 13  # ~0.18 arcmin^2 pixel area
nside = 2**n  # must be a power of 2. the power of 2 = HTM depth
frame = ICRS()
order = "nested"  # efficient for nearest neighbor searches
hp = HEALPix(nside=nside, order=order, frame=frame)
hp.pixel_area.to(u.arcsec * u.arcsec)

cv = {"RAdeg": 313.2196851961664, "DEdeg": -2.6646887231578, "name": "J2052-0239"}
coord = SkyCoord(cv["RAdeg"], cv["DEdeg"], frame="icrs", unit="deg")
# get all pixels within the radius
radius = 5 * u.arcsec
hp.cone_search_skycoord(coord, radius=radius)
```
