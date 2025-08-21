# docs/source/working-notes/troyraen/AllWISE/README.md

## AllWISE: Cross match with the AllWISE catalog in BigQuery public datasets

Outline:
- [Create resources and deploy to Cloud Run](#create-resources-and-deploy-to-cloud-run)
- [Work out the cross match](#work-out-the-cross-match)
    - [Article: Querying the Stars with BigQuery GIS](#article-querying-the-stars-with-bigquery-gis)
    - [How long does a query take?](#how-long-does-a-query-take)

External links:
- [AllWISE](https://wise2.ipac.caltech.edu/docs/release/allwise/) (web)
    - [column names and descriptions](https://wise2.ipac.caltech.edu/docs/release/allwise/expsup/sec2_1a.html)
    - BigQuery table: `bigquery-public-data:wise_all_sky_data_release.all_wise` contains additional columns:
        - `point` ([GEOGRAPHY](https://cloud.google.com/bigquery/docs/reference/standard-sql/data-types#geography_type)) - useful for cross-matching
        - `single_date` - used to partition the table
- [Querying the Stars with BigQuery GIS](https://cloud.google.com/blog/products/data-analytics/querying-the-stars-with-bigquery-gis)
- [BigQuery query optimization](https://cloud.google.com/architecture/bigquery-data-warehouse#query_optimization)
- [Instructions to create resources with pubsub trigger](https://cloud.google.com/run/docs/triggering/pubsub-push#command-line_1)


### Create resources and deploy to Cloud Run

Allow Pub/Sub to create authentication tokens in the project:

```bash
project_number=591409139500
gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} \
     --member=serviceAccount:service-${project_number}@gcp-sa-pubsub.iam.gserviceaccount.com \
     --role=roles/iam.serviceAccountTokenCreator
```

Create service account and give it permission to invoke cloud run

```bash
SERVICE_ACCOUNT_NAME="cloud-run-invoker"
DISPLAYED_SERVICE_ACCOUNT_NAME="Cloud Run Invoker Service Account"

gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
   --display-name "$DISPLAYED_SERVICE_ACCOUNT_NAME"

SERVICE="xmatch-allwise"

gcloud run services add-iam-policy-binding "$SERVICE" \
   --member=serviceAccount:"${SERVICE_ACCOUNT_NAME}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" \
   --role=roles/run.invoker
```

Create the subscription with the service account attached

```bash
endpoint="https://xmatch-allwise-3tp3qztwza-uc.a.run.app/"  # get from Run deployment
survey="ztf"
topic = "${survey}-alerts"
subscription="${topic}-xmatch_allwise"
ack_deadline=300

gcloud pubsub subscriptions create "$subscription" --topic "$topic" \
   --push-endpoint="$endpoint" \
   --push-auth-service-account="${SERVICE_ACCOUNT_NAME}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" \
   --ack-deadline="$ack_deadline"
```

Create bigquery table

```bash
cd /Users/troyraen/Documents/broker/wise/broker/setup_broker
survey=ztf
testid=allwise
dataset=${survey}_alerts
table=xmatch
bq mk --table ${PROJECT_ID}:${dataset}.${table} templates/bq_${survey}_${table}_schema.json
```

Deploy cloud run

```bash
cd /Users/troyraen/Documents/broker/wise/broker/cloud_run/wise
survey=ztf
testid=False
image_name="${survey}-xmatch_allwise"
run_name=xmatch-allwise
IMAGE_URL="gcr.io/${GOOGLE_CLOUD_PROJECT}/${image_name}:latest"
# create and upload container
gcloud builds submit --tag "$IMAGE_URL"
# deploy to cloud run
gcloud run deploy "$run_name" --image "$IMAGE_URL"  --no-allow-unauthenticated \
    --set-env-vars TESTID="$testid",SURVEY="$survey"
# returned
# Service URL: https://xmatch-allwise-3tp3qztwza-uc.a.run.app

```

Create AllWISE topic

```python
from google.cloud import pubsub_v1
import os
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
survey = 'ztf'
testid = 'allwise'
publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

# create topic and counter subscription
topic = f'{survey}-AllWISE'
topic_path = publisher.topic_path(PROJECT_ID, topic)
publisher.create_topic(topic_path)
subscription = f'{topic}-counter'
sub_path = subscriber.subscription_path(PROJECT_ID, subscription)
subscriber.create_subscription(name=sub_path, topic=topic_path)
```

### Work out the cross match

```python
from google.cloud import bigquery
import data_utils, gcp_utils
import troy_fncs as tfncs

alert_dict = tfncs.load_alert_file({'drop_cutouts': True})
# f = '/Users/troyraen/Documents/broker/troy/troy/alerts-for-testing/ZTF18aazyhkf.1704216964315015009.ztf_20210901_programid1.avro'
# alert_dict = data_utils.decode_alert(f)

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

#### Article: Querying the Stars with BigQuery GIS

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


#### How long does a query take?

Trying to see whether the AllWISE table indexes by some ID.
There are (at least) 3 ID columns

```python
import os
import timeit
from broker_utils import gcp_utils

# map allwise/xmatch table column names
coldict = {
    'designation': 'allwise0_designation',
    'cntr': 'allwise0_cntr',
    'source_id': 'allwise0_source_id',
}

# get some AllWISE IDs from our xmatch table
project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
dataset = 'ztf_alerts'
table = 'xmatch'
query = f"""
    SELECT {','.join(coldict.values())}
    FROM `{project_id}.{dataset}.{table}`
    WHERE allwise0_designation!='J235808.26-202256.6'
    LIMIT 1
"""
df = gcp_utils.query_bigquery(query).to_dataframe()

# use the IDs to query AllWISE table
project_id = 'bigquery-public-data'
dataset = 'wise_all_sky_data_release'
table = 'all_wise'
resultdict = {}
for awcol, xmcol in coldict.items():
    if awcol == 'cntr':
        query = f"""
            SELECT {awcol}
            FROM `{project_id}.{dataset}.{table}`
            WHERE {awcol}={df.loc[0,xmcol]}
        """
    else:
        query = f"""
            SELECT {awcol}
            FROM `{project_id}.{dataset}.{table}`
            WHERE {awcol}='{df.loc[0,xmcol]}'
        """
    start = timeit.default_timer()
    resultdict[f'{awcol} (all cols)'] = query_job = gcp_utils.query_bigquery(query).to_dataframe()
    stop = timeit.default_timer()
    resultdict[f'{awcol} (all cols) time'] = stop - start
    print('Time: ', stop - start)

# now add a filter on the spt_ind column by which the table is clustered
for awcol, xmcol in coldict.items():
    if awcol == 'cntr':
        query = f"""
            SELECT {awcol}
            FROM `{project_id}.{dataset}.{table}`
            WHERE spt_ind=200102013 AND {awcol}={df.loc[0,xmcol]}
        """
    else:
        query = f"""
            SELECT {awcol}
            FROM `{project_id}.{dataset}.{table}`
            WHERE spt_ind=200102013 AND {awcol}='{df.loc[0,xmcol]}'
        """
    start = timeit.default_timer()
    resultdict[f'{awcol} (spt_ind)'] = query_job = gcp_utils.query_bigquery(query).to_dataframe()
    stop = timeit.default_timer()
    resultdict[f'{awcol} (spt_ind) time'] = stop - start
    print('Time: ', stop - start)
```

### Copy AllWISE table and add HEALPix column

- [x] copy table
- [ ] add HEALPix
    - query ra, dec, id -> pandas dataframe
    - calc and add HEALPix
    - load dataframe -> new bigquery table
    - update the allwise table using a join
- [ ] partition table by HEALPix
- [ ] cluster table by HEALPix
- [ ] update run

__Using the test project `avid-heading-329016`__

```bash
project_id="avid-heading-329016"

export GOOGLE_CLOUD_PROJECT="$project_id"
export GOOGLE_APPLICATION_CREDENTIALS="<your/path/to/servicecredentialsauthkey.json"

gcloud config set project "$project_id"
```

#### Copy table

Uses the BigQuery transfer service.

```bash
# enable the API (only needs to be done once for the project)
gcloud services enable bigquerydatatransfer.googleapis.com

# create a dataset in our project to hold the allwise tables
new_dataset="wise_all_sky_data_release"
bq --location=US mk -d --description "Copy of AllWISE, BigQuery public dataset." $new_dataset

# copy the public dataset to our project's new dataset
bq mk --transfer_config \
    --display_name="copy allwise dataset" \
    --project_id=$GOOGLE_CLOUD_PROJECT \
    --target_dataset="$new_dataset" \
    --data_source="cross_region_copy" \
    --params='{"source_dataset_id":"wise_all_sky_data_release","source_project_id":"bigquery-public-data"}'
# follow instructions to complete OAuth
# recieved the following output:
# Transfer configuration 'projects/591409139500/locations/us/transferConfigs/61b6e8c3-0000-24ad-8cae-14c14ef90d6c' successfully created.

# copy using a query and create new table partitioned by htm 7 (spt_ind)
table="all_wise_htm"
bq query \
  --use_legacy_sql=false \
  --destination_table "${GOOGLE_CLOUD_PROJECT}:${new_dataset}.${table}" \
  --range_partitioning spt_ind,START,END,INTERVAL \
  'QUERY_STATEMENT'
```

#### Add HEALPix

Setup

```python
import os

from astropy import units as u
from astropy.coordinates import ICRS, SkyCoord
from astropy_healpix import HEALPix
import pandas as pd

from broker_utils import gcp_utils

project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
dataset = "wise_all_sky_data_release"
table = "all_wise"

def radec_to_skycoord(row):
    return SkyCoord(row["RAdeg"], row["DEdeg"], frame='icrs', unit='deg')
def skycoord_to_healpix(row):
    return hp.skycoord_to_healpix(row['SkyCoord'])
def radec_to_healpix(row):
    sc = {"SkyCoord": radec_to_skycoord(row)}
    healpix = skycoord_to_healpix(sc)
    return healpix
```

```python
# query the data
query = (
    "SELECT designation, ra, dec "
    f"FROM {project_id}.{dataset}.{table}"
)
awdf = gcp_utils.query_bigquery(query).to_dataframe()

# add the HEALPix
n = 16  # gives pixel area ~10.4 arcsec^2
nside = 2**n  # must be a power of 2. the power of 2 = HTM depth
frame = ICRS()
order = 'nested'  # efficient for nearest neighbor searches
hp = HEALPix(nside=nside, order=order, frame=frame)
# hp.pixel_area.to(u.arcsec*u.arcsec)
awdf[f'HEALPix_n{n}'] = awdf.apply(radec_to_healpix, axis=1)
```
