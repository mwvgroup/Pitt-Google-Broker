Table of Contents:
- [Schema Maps](#schema-maps)
- [BigQuery schema json](#bigquery-schema-json)

# Schema Maps
<!-- fs -->
```python
from google.cloud import storage
import os
import yaml

fztf = 'schema_maps/ztf.yaml'
fdecat = 'schema_maps/decat.yaml'

ztf = {
    'objectId': 'objectId',
    'source': 'candidate',
    'sourceId': 'candid',
    'prvSources': 'prv_candidates',
}
decat = {
    'objectId': 'objectid',
    'source': 'triggersource',
    'sourceId': 'sourceid',
    'prvSources': 'sources',
}

# write the files
for smap, fname in zip([ztf, decat], [fztf, fdecat]):
    with open(f'../broker/{fname}', "w") as f:
        yaml.dump(smap, f, sort_keys=False)

# upload the files to GCS
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
SURVEY = 'ztf'
TESTID = 'testsurveyname'
bucket_name = f'{PROJECT_ID}-{SURVEY}-broker_files-{TESTID}'

storage_client = storage.Client()
for fname in [fztf, fdecat]:
    with open(f'../broker/{fname}', "rb") as f:
      # smap_in = yaml.safe_load(f)
      blob = storage_client.bucket(bucket_name).blob(fname)
      blob.upload_from_file(f)

    with open("my-file", "rb") as my_file:
      blob.upload_from_file(my_file)
```


<!-- fe # Schema Maps -->
---

# BigQuery schema json
<!-- fs -->
We need a:
- list of dictionaries, each with keys:
    - description - string
    - mode - one of [REQUIRED, REPEATED, NULLABLE]
    - name - string, no spaces
    - type - one of [INTEGER, FLOAT, STRING, RECORD]
    - fields (if type == RECORD) - list of dictionaries with the same keys as listed above

Download the decat schemas
```bash
git clone https://github.com/rknop/decat_schema.git
```

Create the json for BigQuery using the functions in `schema.py`
```python
#--- look at the ztf BQ schema to understand what's needed
fztfschema = '../broker/setup_broker/templates/bq_ztf_alerts_schema.json'
with open(fztfschema) as f:
    ztfschema = json.load(f)

#--- Create BigQuery schemas and dump to json
import schemas
__ = schemas.create_bq_table_schemas()
```

Make the tables (test what `setup_gcp.py` will do)
```
projectid=ardent-cycling-243415
dataset=ztf_alerts_decam

bq mk --table "${projectid}:${dataset}.alerts" templates/bq_decat_alerts_schema.json
bq mk --table "${projectid}:${dataset}.DIASource" templates/bq_decat_DIASource_schema.json
bq mk --table "${projectid}:${dataset}.salt2" templates/bq_decat_salt2_schema.json

bq rm --table "${projectid}:${dataset}.alerts"
bq rm --table "${projectid}:${dataset}.DIASource"
bq rm --table "${projectid}:${dataset}.salt2"
```

<!-- fe BigQuery schema json -->
