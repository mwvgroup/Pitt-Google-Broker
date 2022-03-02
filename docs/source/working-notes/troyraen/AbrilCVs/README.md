# AbrilCVs: CV Catalog from Abril 2020<a name="abrilcvs-cv-catalog-from-abril-2020"></a>

<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=1 -->

- [AbrilCVs: CV Catalog from Abril 2020](#abrilcvs-cv-catalog-from-abril-2020)
  - [Intro](#intro)
  - [Catalog](#catalog)
  - [Calculate HEALPix indexes of CV catalog and use to xmatch](#calculate-healpix-indexes-of-cv-catalog-and-use-to-xmatch)
  - [Try TNS CVs](#try-tns-cvs)
  - [Try some ASAS-SN data](#try-some-asas-sn-data)
  - [Test Cloud Run module](#test-cloud-run-module)

<!-- mdformat-toc end -->

## Intro<a name="intro"></a>

Links

- [Abril 2020](https://ui.adsabs.harvard.edu/abs/2020MNRAS.492L..40A/abstract)
- [CV catalog on CDS](https://cdsarc.cds.unistra.fr/viz-bin/cat?J/MNRAS/492/L40)
  (downloaded to this dir)

Notes

- Michael:
  - number of dimensions to parameters. maybe dataset of only 2000 is ok. make the model
    smarter (vs data augmentation)
- Brett:
  - get ~2000 Gaia stars, combine with these CVs
  - mags, etc.
  - random forest
- Abril20
  - CMD
    - trends with subtypes and periods
    - population density distributions
- Questions:
  - Periods of hours. could you predict the magnitude based on different periods, and
    then check whether alert is consistent? or are the uncertainties too big? mags,
    period.

## Catalog<a name="catalog"></a>

```python
import os
import pandas as pd
from astropy.coordinates import SkyCoord

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
dir = "/Users/troyraen/Documents/broker/troy/troy/AbrilCVs"
fcat = f"{dir}/J_MNRAS_492_L40/catalog.dat"
ftns = f"{dir}/tns_search_cvs.csv"
fasn = f"{dir}/ASAS-SN/cvs.csv"

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
```

## Calculate HEALPix indexes of CV catalog and use to xmatch<a name="calculate-healpix-indexes-of-cv-catalog-and-use-to-xmatch"></a>

Calculate indexes

```python
import os
import pandas as pd
from astropy.coordinates import ICRS, SkyCoord
from astropy_healpix import HEALPix
from astropy import units as u

dir = "/Users/troyraen/Documents/broker/troy/troy/AbrilCVs"
fcat = f"{dir}/J_MNRAS_492_L40/catalog.dat"
fcat_condensed = f"{dir}/J_MNRAS_492_L40/catalog_condensed.dat"


def radec_to_skycoord(row):
    return SkyCoord(row["RAdeg"], row["DEdeg"], frame="icrs", unit="deg")


def skycoord_to_healpix(row):
    return hp.skycoord_to_healpix(row["SkyCoord"])


# load Abril CV catalog
abrildf = pd.read_fwf(fcat, names=names, header=None, index=None)
coords = SkyCoord(cv["RAdeg"], cv["DEdeg"], frame="icrs", unit="deg")
# instantiate pixelization
n = 17
nside = 2**n
frame = ICRS()
order = "nested"
hp = HEALPix(nside=nside, order=order, frame=frame)

# calculate indexes
abrildf["SkyCoord"] = abrildf.apply(radec_to_skycoord, axis=1)
abrildf[f"hp_{n}_index"] = abrildf.apply(skycoord_to_healpix, axis=1)

# save csv
keep_cols = ["Name", "RAdeg", "DEdeg", "hp_17_index"]
abrildf[keep_cols].to_csv(fcat_condensed, index=False)
```

Xmatch

```python
import timeit

adf = pd.read_csv(fcat_condensed)

max_sep = 5.0 * u.arcsec
alert = {"ra": 313.2196851961664, "dec": -2.6646887231578, "Name": "J2052-0239"}
alertcoords = SkyCoord(alert["ra"], alert["dec"], frame="icrs", unit="deg")

# time without HEALPix
start = timeit.default_timer()
adf["SkyCoord"] = adf.apply(radec_to_skycoord, axis=1)
matches_wo = {}
for _, cv in adf.iterrows():
    if alertcoords.separation(cv["SkyCoord"]) <= max_sep:
        matches_wo[alert["Name"]] = (alert, cv)
stop = timeit.default_timer()
print("Time: ", stop - start)

# time with HEALPix
start = timeit.default_timer()
idxs = hp.cone_search_skycoord(alertcoords, radius=max_sep)  # all pixels within max_sep
matches_w = {}
for _, cv in adf.iterrows():
    if cv["hp_17_index"] in idxs:
        if alertcoords.separation(radec_to_skycoord(cv)) <= max_sep:
            matches_w[alert["Name"]] = (alert, cv)
stop = timeit.default_timer()
print("Time: ", stop - start)
```

## Try TNS CVs<a name="try-tns-cvs"></a>

```python
# get positions of TNS CVs
df = pd.read_csv(ftns)
ztfdf = df.loc[df["Disc. Internal Name"].fillna("").str.startswith("ZTF")]
objectIds = list(ztfdf["Disc. Internal Name"].unique())
dataset = "ztf_alerts"
table = "DIASource"
query = f"""
    SELECT objectId, candid, ra, dec
    FROM `{project_id}.{dataset}.{table}`
    WHERE objectId IN ('{"','".join(objectIds)}')
"""
bqdf = gcp_utils.query_bigquery(query).to_dataframe()
cleandf = bqdf.sort_values("candid", ascending=False).drop_duplicates(
    subset="objectId", keep="first"
)

# xmatch
max_sep = 50.0 * u.arcsec
matches = {}
for _, cv in abrildf.iterrows():
    cvcoords = SkyCoord(cv["RAdeg"], cv["DEdeg"], frame="icrs", unit="deg")
    for _, alert in cleandf.iterrows():
        alertcoords = SkyCoord(alert["ra"], alert["dec"], frame="icrs", unit="deg")
        if alertcoords.separation(cvcoords) <= max_sep:
            matches[alert["objectId"]] = (alert, cv)
```

## Try some ASAS-SN data<a name="try-some-asas-sn-data"></a>

```python
# load asassn
asndf = pd.read_csv(fasn)
max_sep = 1.0 * u.arcsec
matches = {}
for _, cv in abrildf.iterrows():
    cvcoords = SkyCoord(cv["RAdeg"], cv["DEdeg"], frame="icrs", unit="deg")
    for _, asn in asndf.iterrows():
        alertcoords = SkyCoord(asn["raj2000"], asn["dej2000"], frame="icrs", unit="deg")
        if alertcoords.separation(cvcoords) <= max_sep:
            matches[asn["source_id"]] = (asn, cv)
            break
```

## Test Cloud Run module<a name="test-cloud-run-module"></a>

```python
from broker_utils import gcp_utils

msgs = gcp_utils.pull_pubsub("ztf-loop", msg_only=False)
msg = msgs[0]
alert_dict = data_utils.decode_alert(msg.message.data)
```
