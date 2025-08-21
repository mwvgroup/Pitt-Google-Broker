# docs/source/working-notes/troyraen/ztf-v4.02/readme.md

## Update to ZTF Avro Schema v4.02

### Download the schema files

```bash
baseurl="https://raw.githubusercontent.com/ZwickyTransientFacility/ztf-avro-alert/master/schema/"
format="avsc"
schemas=(alert candidate cutout fp_hist prv_candidate)

for schema in ${schemas[@]}; do
    fname="${schema}.${format}"
    curl -L -o "schema/${fname}" "${baseurl}${fname}"
done

# alert.avsc expects the other files to have "ztf.alert." prepended to their names
for schema in ${schemas[@]}; do
    fname="${schema}.${format}"
    mv "schema/${fname}" "schema/ztf.alert.${fname}"
done
```

### Load schema

```python
import fastavro

schema = fastavro.schema.load_schema("schema/ztf.alert.alert.avsc")
```

### Create the BigQuery schema file and then create the table

```python
import numpy as np
import os
import sys
from pathlib import Path

# need to use some functions from the dir ingest-ztf-archive
sys.path.append('../ingest-ztf-archive')
import ingest_tarballs
import schemas


PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
# tarball has v4.01 but real version will be v4.02
VERSION = "4.01"  # use this to create the table using a downloaded alert
# VERSION = "4.02"  # use this later to fill in the production table
VERSIONTAG = f"v{VERSION.replace('.', '_')}"

DATASET = "ztf_raenztf402"  # manually created this dataset
TABLE = f"{PROJECT_ID}.{DATASET}.alerts_{VERSIONTAG}"

# easiest way to create the bigquery schema file is to create a table using an alert then download the json
# manually downloaded the tarball of alerts and extracted
# https://caltech.box.com/s/jxm00q0jufcnshnluktle8wk05lam73c
alert_dir = "../ingest-ztf-archive/alerts/apfp_20231012"
alert_path = f"{alert_dir}/2475433850015010009.avro"

# fix the schema
ingest_tarballs.touch_schema(VERSION, alert_path)
schema = schemas.loadavsc(VERSION, nocutouts=True)
ingest_tarballs.fix_alert_on_disk((Path(alert_path), schema, VERSION))
alert_path = f"{alert_dir}/apfp_20231012/ZTF17aadcvhq/2475433850015010009.avro"

# create the table using the downloaded alert
ingest_tarballs.touch_table(TABLE, alert_path, schema, VERSION)

# --------- skip down to "download the bigquery schema to a json file" ---------

# there were already alerts in the kafka topic when i turned the consumer on. ran into bigquery rate limit.
# no errors with alerts getting into the bucket, so use it fill in the table.
VERSION = "4.02"
VERSIONTAG = f"v{VERSION.replace('.', '_')}"
DATASET = "ztf"
TABLE = f"{PROJECT_ID}.{DATASET}.alerts_{VERSIONTAG}"
bucket = f"{PROJECT_ID}-{DATASET}_alerts_{VERSIONTAG}"
BUCKET = ingest_tarballs.STORAGE_CLIENT.get_bucket(
    ingest_tarballs.STORAGE_CLIENT.bucket(bucket, user_project=PROJECT_ID)
)

# get list of candid in bucket
blobs = list(BUCKET.list_blobs())
bucket_candids = sorted(int(Path(blob.name).stem) for blob in blobs)

# get series of candid in table
sql = (f"SELECT candid FROM `{TABLE}`")
query_job = ingest_tarballs.BQ_CLIENT.query(sql)
table_candids = query_job.result().to_dataframe().squeeze().sort_values()

# upload what's missing to the table
missing_candids = set(bucket_candids) - set(table_candids)
source_uris = [
    "gs://" + blob.bucket.name + "/" + blob.name for blob in blobs
    if int(Path(blob.name).stem) in missing_candids
]
jobs = []  # can only send 10_000 alerts sat a time
for uri_chunk in np.array_split(source_uris, (len(source_uris) // 10_000) + 1):
    jobs.append(ingest_tarballs.load_table_from_bucket(TABLE, list(uri_chunk), reportid=f"len{len(uri_chunk)}"))

```

```bash
# download the bigquery schema to a json file
schema_file="../../../../../broker/setup_broker/templates/bq_ztf_alerts_v4_02_schema.json"
bq show --schema --format=prettyjson \
    ardent-cycling-243415:ztf_raenztf402.alerts_v4_02 \
    > ${schema_file}
# we created this with a v4.01 alert but nothing needs to be changed in the json for v4.02

# make the production table
bq mk --table ardent-cycling-243415:ztf.alerts_v4_02 ${schema_file}
```

### Create the bucket

```bash
# copied from broker/cloud_functions/ps_to_gcs/deploy.sh
PROJECT_ID=$GOOGLE_CLOUD_PROJECT
region=us-central1
survey=ztf
versiontag=v4_02

avro_bucket="${PROJECT_ID}-${survey}_alerts_${versiontag}"
gsutil mb -l "${region}" "gs://${avro_bucket}"
gsutil uniformbucketlevelaccess set on "gs://${avro_bucket}"
gsutil requesterpays set on "gs://${avro_bucket}"
gcloud storage buckets add-iam-policy-binding "gs://${avro_bucket}" \
    --member="allUsers" \
    --role="roles/storage.objectViewer"
```

### Update VERSIONTAG for all cloud functions

```bash
survey=ztf
region=us-central1
versiontag=v4_02
cloudfncs=(\
    "${survey}-check_cue_response" \
    "${survey}-classify_with_SuperNNova" \
    "${survey}-lite" \
    "${survey}-store_in_BigQuery" \
    "${survey}-tag"\
    "${survey}-upload_bytes_to_bucket" \
)

for cloudfnc in ${cloudfncs[@]}; do
    # this gives me the error
    # ERROR: (gcloud.functions.deploy) Uncompressed deployment is 2237421867B, bigger than maximum allowed size of 536870912B.
    # so i just updated them manually from the console
    gcloud functions deploy "${cloudfnc}" --region="${region}" --update-env-vars=VERSIONTAG="${versiontag}"
done
```
