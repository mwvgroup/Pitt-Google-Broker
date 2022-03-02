# Rubin DPO

## TAP

- [PyVO](https://pyvo.readthedocs.io/en/latest/index.html)
- [get TAP service. source code for DP0 notebook](https://github.com/lsst-sqre/rubin-jupyter-lab/blob/master/rubin_jupyter_utils/lab/notebook/catalog.py)
- [DP0 notebook 6: Comparing_Object_and_Truth_Tables](https://data.lsst.cloud/nb/user/troyraen/lab/tree/notebooks/tutorial-notebooks/06_Comparing_Object_and_Truth_Tables.ipynb)
- [DP0 notebook 2: Intermediate_TAP_Query](https://data.lsst.cloud/nb/user/troyraen/lab/tree/notebooks/tutorial-notebooks/02_Intermediate_TAP_Query.ipynb)
- [RSP API aspect](https://data.lsst.cloud/api-aspect)

Much of this code is taken from the DP0 notebooks.

```python
import os
import requests
from astropy import units as u
from astropy.coordinates import SkyCoord
import matplotlib.pyplot as plt
import numpy as np
import pyvo

params = {
    "axes.labelsize": 28,
    "font.size": 24,
    "legend.fontsize": 18,
    "xtick.major.width": 3,
    "xtick.minor.width": 2,
    "xtick.major.size": 12,
    "xtick.minor.size": 6,
    "xtick.direction": "in",
    "xtick.top": True,
    "lines.linewidth": 3,
    "axes.linewidth": 3,
    "axes.labelweight": 3,
    "axes.titleweight": 3,
    "ytick.major.width": 3,
    "ytick.minor.width": 2,
    "ytick.major.size": 12,
    "ytick.minor.size": 6,
    "ytick.direction": "in",
    "ytick.right": True,
    "figure.figsize": [10, 8],
    "figure.facecolor": "White",
}
plt.rcParams.update(params)


def _get_auth(tap_url, access_token):
    """https://github.com/lsst-sqre/rubin-jupyter-lab/blob/master/rubin_jupyter_utils/lab/notebook/catalog.py"""
    # tap_url = _get_tap_url()
    s = requests.Session()
    s.headers["Authorization"] = "Bearer " + access_token
    auth = pyvo.auth.authsession.AuthSession()
    auth.credentials.set("lsst-token", s)
    auth.add_security_method_for_url(tap_url, "lsst-token")
    auth.add_security_method_for_url(tap_url + "/sync", "lsst-token")
    auth.add_security_method_for_url(tap_url + "/async", "lsst-token")
    auth.add_security_method_for_url(tap_url + "/tables", "lsst-token")
    return auth


tap_url = "https://data.lsst.cloud/api/tap"
# username = "x-oauth-basic"
auth = _get_auth(tap_url, os.getenv("DP0token"))
service = pyvo.dal.TAPService(tap_url, auth)

# get table descriptions
results = service.search("SELECT description, table_name FROM TAP_SCHEMA.tables")
resultsdf = results.to_table().to_pandas()

# --- CMD and CCD from cone search
query = (
    "SELECT obj.objectId, obj.ra, obj.dec, obj.mag_g, obj.mag_r, "
    "obj.mag_i, obj.mag_g_cModel, obj.mag_r_cModel, obj.mag_i_cModel, "
    "obj.psFlux_g, obj.psFlux_r, obj.psFlux_i, obj.cModelFlux_g, "
    "obj.cModelFlux_r, obj.cModelFlux_i, obj.tract, obj.patch, "
    "obj.extendedness, obj.good, obj.clean, "
    "truth.mag_r as truth_mag_r, truth.match_objectId, "
    "truth.flux_g, truth.flux_r, truth.flux_i, truth.truth_type,  "
    "truth.match_sep, truth.is_variable "
    "FROM dp01_dc2_catalogs.object as obj "
    "JOIN dp01_dc2_catalogs.truth_match as truth "
    "ON truth.match_objectId = obj.objectId "
    "WHERE CONTAINS(POINT('ICRS', obj.ra, obj.dec), "
    "CIRCLE('ICRS', 62.0, -37.0, 0.10)) = 1 "
    "AND truth.match_objectid >= 0 "
    "AND truth.is_good_match = 1"
)
results = service.search(query)
df = results.to_table().to_pandas()
# separate stars and galaxies
star = np.where(results["truth_type"] == 2)
gx = np.where(results["truth_type"] == 1)

ccd_cmd(results, star, gx)
compare_fluxes(results, star, gx)


def ccd_cmd(results, star, gx):
    fig, ax = plt.subplots(1, 2, figsize=(15, 8))

    plt.sca(ax[0])  # set the first axis as current

    plt.plot(
        results["mag_g_cModel"][gx] - results["mag_i_cModel"][gx],
        results["mag_g_cModel"][gx],
        "k.",
        alpha=0.2,
        label="galaxies",
    )
    plt.plot(
        results["mag_g_cModel"][star] - results["mag_i_cModel"][star],
        results["mag_g_cModel"][star],
        "ro",
        label="stars",
    )
    plt.legend(loc="upper left")
    plt.xlabel(r"$(g-i)$")
    plt.ylabel(r"$g$")
    plt.xlim(-1.8, 4.3)
    plt.ylim(29.3, 16.7)
    plt.minorticks_on()

    plt.sca(ax[1])  # set the first axis as current
    plt.plot(
        results["mag_g_cModel"][gx] - results["mag_r_cModel"][gx],
        results["mag_r_cModel"][gx] - results["mag_i_cModel"][gx],
        "k.",
        alpha=0.1,
        label="galaxies",
    )
    plt.plot(
        results["mag_g_cModel"][star] - results["mag_r_cModel"][star],
        results["mag_r_cModel"][star] - results["mag_i_cModel"][star],
        "ro",
        label="stars",
    )
    plt.legend(loc="upper left")
    plt.xlabel(r"$(g-r)$")
    plt.ylabel(r"$(r-i)$")
    plt.xlim(-1.3, 2.3)
    plt.ylim(-1.3, 2.8)
    plt.minorticks_on()

    plt.tight_layout()
    plt.show(block=False)


def compare_fluxes(results, star, gx):
    plt.rcParams.update({"figure.figsize": (11, 10)})

    plt.plot(
        results["truth_mag_r"][gx],
        results["cModelFlux_r"][gx] / results["flux_r"][gx],
        "k.",
        alpha=0.2,
        label="galaxies",
    )
    plt.plot(
        results["truth_mag_r"][star],
        results["cModelFlux_r"][star] / results["flux_r"][star],
        "ro",
        label="stars",
    )
    plt.legend(loc="upper left")
    plt.xlabel(r"$r$ magnitude (truth)")
    plt.ylabel(r"$f_{\rm meas}/f_{\rm truth}$")
    plt.ylim(0.15, 2.15)
    plt.xlim(17.6, 27.8)
    plt.minorticks_on()
    plt.show(block=False)


# --- Cone search
coord = SkyCoord(ra=62.0 * u.degree, dec=-37.0 * u.degree, frame="icrs")
radius = 0.1 * u.deg
query = (
    "SELECT ra, dec, mag_g, mag_i "
    "mag_i, mag_g_cModel, mag_r_cModel, mag_i_cModel, "
    "psFlux_g, psFlux_r, psFlux_i, "
    "cModelFlux_g, cModelFlux_r, cModelFlux_i, "
    "tract, patch, extendedness, good, clean "
    "FROM dp01_dc2_catalogs.object "
    "WHERE CONTAINS(POINT('ICRS', ra, dec),CIRCLE('ICRS', "
    + str(coord.ra.value)
    + ", "
    + str(coord.dec.value)
    + ", "
    + str(radius.value)
    + " )) = 1"
)

df = service.search(query).to_table().to_pandas()

# join with truth
query = (
    "SELECT obj.objectId, obj.ra, obj.dec, obj.mag_g, obj.mag_r, "
    " obj.mag_i, obj.mag_g_cModel, obj.mag_r_cModel, obj.mag_i_cModel,"
    "obj.psFlux_g, obj.psFlux_r, obj.psFlux_i, obj.cModelFlux_g, "
    "obj.cModelFlux_r, obj.cModelFlux_i, obj.tract, obj.patch, "
    "obj.extendedness, obj.good, obj.clean, "
    "truth.mag_r as truth_mag_r, truth.match_objectId, "
    "truth.flux_g, truth.flux_r, truth.flux_i, truth.truth_type, "
    "truth.match_sep, truth.is_variable "
    "FROM dp01_dc2_catalogs.object as obj "
    "JOIN dp01_dc2_catalogs.truth_match as truth "
    "ON truth.match_objectId = obj.objectId "
    "WHERE CONTAINS(POINT('ICRS', obj.ra, obj.dec),CIRCLE('ICRS', "
    + str(coord.ra.value)
    + ", "
    + str(coord.dec.value)
    + ", "
    + str(radius.value)
    + " )) = 1 "
    "AND truth.match_objectid >= 0 "
    "AND truth.is_good_match = 1"
)
df = service.search(query).to_table().to_pandas()
# How many of each type in the dataset
# The 'truth_type' in the truth_match table is 1= galaxies, 2=stars, 3=SNe
n_stars = df[df["truth_type"] == 2].shape[0]
print(f"There are {n_stars} stars out of a total of {len(df)}")
print(f'There are {df[df["truth_type"] == 1].shape[0]} galaxies')
print(f'There are {df[df["truth_type"] == 3].shape[0]} SNe')
```
