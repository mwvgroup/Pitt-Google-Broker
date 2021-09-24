# Cross match with the AllWISE catalog in BigQuery public datasets

- [AllWISE](https://wise2.ipac.caltech.edu/docs/release/allwise/) (web)
    - [column names and descriptions](https://wise2.ipac.caltech.edu/docs/release/allwise/expsup/sec2_1a.html)
- BigQuery table: `bigquery-public-data:wise_all_sky_data_release.all_wise` contains additional columns:
    - `point` ([GEOGRAPHY](https://cloud.google.com/bigquery/docs/reference/standard-sql/data-types#geography_type)) - useful for cross-matching
    - `single_date` - used to partition the table


```python
from google.cloud import bigquery
import data_utils, gcp_utils

f = '/Users/troyraen/Documents/broker/troy/troy/alerts-for-testing/ZTF18aazyhkf.1704216964315015009.ztf_20210901_programid1.avro'
alert_dict = data_utils.decode_alert(f)

# all_wise_table = 'bigquery-public-data:wise_all_sky_data_release.all_wise'
all_wise_col_list = [
    # Sexagesimal, equatorial position-based source name in the form: hhmmss.ss+ddmmss.s
    'designation',
    'ra',  # J2000 right ascension w.r.t. 2MASS PSC ref frame, non-moving src extraction
    'dec',  # J2000 declination w.r.t. 2MASS PSC ref frame, non-moving src extraction
    'sigra',  # One-sigma uncertainty in ra from the non-moving source extraction
    'sigdec',  # One-sigma uncertainty in dec from the non-moving source extraction
    'cntr',  # Unique ID number for this object in the AllWISE Catalog/Reject Table
    'source_id',  # Unique source ID
    # W1 magnitude measured with profile-fitting photometry, or the magnitude of the
    # 95% confidence brightness upper limit if the W4 flux measurement has SNR<2
    'w1mpro',
    'w1sigmpro',  # W1 profile-fit photometric measurement uncertainty in mag units
    'w1snr',  # W1 profile-fit measurement signal-to-noise ratio
    'w1rchi2',  # Reduced χ2 of the W1 profile-fit photometry
    # W2 magnitude measured with profile-fitting photometry, or the magnitude of the
    # 95% confidence brightness upper limit if the W4 flux measurement has SNR<2
    'w2mpro',
    'w2sigmpro',  # W2 profile-fit photometric measurement uncertainty in mag units
    'w2snr',  # W2 profile-fit measurement signal-to-noise ratio
    'w2rchi2',  # Reduced χ2 of the W2 profile-fit photometry
    # W3 magnitude measured with profile-fitting photometry, or the magnitude of the
    # 95% confidence brightness upper limit if the W4 flux measurement has SNR<2
    'w3mpro',
    'w3sigmpro',  # W3 profile-fit photometric measurement uncertainty in mag units
    'w3snr',  # W3 profile-fit measurement signal-to-noise ratio
    'w3rchi2',  # Reduced χ2 of the W3 profile-fit photometry
    # W4 magnitude measured with profile-fitting photometry, or the magnitude of the
    # 95% confidence brightness upper limit if the W4 flux measurement has SNR<2
    'w4mpro',
    'w4sigmpro',  # W4 profile-fit photometric measurement uncertainty in mag units
    'w4snr',  # W4 profile-fit measurement signal-to-noise ratio
    'w4rchi2',  # Reduced χ2 of the W4 profile-fit photometry
    'nb',  # Number of PSF components used simultaneously in profile-fitting this source
    'na',  # Active deblending flag.
    'pmra',  # The apparent (not proper!) motion in right ascension estimated for source
    'sigpmra',  # Uncertainty in the RA motion estimation.
    'pmdec',  # The apparent (not proper!) motion in declination estimated for source
    'sigpmdec',  # Uncertainty in the Dec motion estimated for this source
    'ext_flg',  # Extended source flag
    'var_flg',  # Variability flag
    # Unique ID of closest source in 2MASS Point Source Catalog (PSC)
    # that falls within 3" of the non-motion fit position
    'tmass_key',
    'r_2mass',  # Distance between WISE source and associated 2MASS PSC source
    'n_2mass',  # num 2MASS PSC entries within a 3" radius of the WISE source position
    'j_m_2mass',  # 2MASS J-band magnitude or magnitude upper limit
    'j_msig_2mass',  # 2MASS J-band corrected photometric uncertainty
    'h_m_2mass',  # 2MASS H-band magnitude or magnitude upper limit
    'h_msig_2mass',  # 2MASS H-band corrected photometric uncertainty
    'k_m_2mass',  # 2MASS K_s-band magnitude or magnitude upper limit
    'k_msig_2mass',  # 2MASS K_s-band corrected photometric uncertainty

]
all_wise_cols = ','.join(all_wise_col_list)

ra = alert_dict['candidate']['ra']
dec = alert_dict['candidate']['dec']
# ra, dec = 201.5, -2.6
d_sep = 60  # units?

# pad = 0.5
pad = 0.00138889  # 5 arcsec converted to degrees
polygon = f"Polygon(({ra-pad} {dec-pad},{ra-pad} {dec+pad},{ra+pad} {dec+pad},{ra+pad} {dec-pad}, {ra-pad} {dec-pad}))"

job_config = bigquery.QueryJobConfig(
    query_parameters=[
        bigquery.ScalarQueryParameter("all_wise_cols", "STRING", all_wise_cols),
        bigquery.ArrayQueryParameter("all_wise_col_list", "STRING", all_wise_col_list),
        # bigquery.ScalarQueryParameter("all_wise_table", "STRING", all_wise_table),
        bigquery.ScalarQueryParameter("ra", "FLOAT64", ra),
        bigquery.ScalarQueryParameter("dec", "FLOAT64", dec),
        bigquery.ScalarQueryParameter("d_sep", "FLOAT64", d_sep),
        bigquery.ScalarQueryParameter("polygon", "STRING", polygon),
    ]
)

# what are the units of d?
# how to convert alert ra, dec to POINT geometry type?
# how to choose Polygon boundaries?
# Polygon verticies backwards?
# how to parameterize SELECT?
# is this a projected distance, or along the 3d curve?
query = """
    CREATE TEMP FUNCTION
      ArcSecondDistance(p1 GEOGRAPHY, p2 GEOGRAPHY,
        d FLOAT64) AS (ST_DISTANCE(p1,p2) < d * 30.8874796235);
    SELECT source_id, ra, dec, point
    FROM `bigquery-public-data.wise_all_sky_data_release.all_wise`
    WHERE
      ArcSecondDistance(point, ST_GEOGPOINT(@ra, @dec), @d_sep)
      AND ST_CONTAINS(ST_GEOGFROMTEXT(@polygon), point)
    LIMIT 10;
"""

query_job = gcp_utils.query_bigquery(query, job_config=job_config)
df = query_job.to_dataframe()
aw_dict = df.to_dict(orient='records')

```

## Article: Querying the Stars with BigQuery GIS
https://cloud.google.com/blog/products/data-analytics/querying-the-stars-with-bigquery-gis

```python
query = """
CREATE TEMP FUNCTION
  ArcSecondDistance(p1 GEOGRAPHY, p2 GEOGRAPHY,
    d FLOAT64) AS (ST_DISTANCE(p1,p2) < d * 30.8874796235);
SELECT
  source_id_mf,
  point
FROM
  `bigquery-public-data.wise_all_sky_data_release.mep_wise`
WHERE
  ArcSecondDistance(point,
    ST_GEOGPOINT(201.5, -2.6),60)
  AND ST_CONTAINS(
   ST_GEOGFROMTEXT('Polygon((201.00 -3.10,201.00 -2.10,202.00 -2.10,202.00 -3.10, 201.00 -3.10))'),point)
"""

query_job = gcp_utils.query_bigquery(query)
df = query_job.to_dataframe()

```

ArcSecondDistance(p1 GEOGRAPHY, p2 GEOGRAPHY, d FLOAT64)
    AS (ST_DISTANCE(p1, p2) < d * 30.8874796235);

ArcSecondDistance(point, ST_GEOGPOINT(201.5, -2.6), 60)
