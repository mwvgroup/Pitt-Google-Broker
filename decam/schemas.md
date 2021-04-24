# Schemas

Table of Contents:
- [Schema Maps](#schema-maps)
- [BigQuery schema json](#bigquery-schema-json)
- [Test the changes](#test-the-changes)

---

## Schema Maps
<!-- fs -->
```python
from google.cloud import storage
import os
import yaml

fztf = 'schema_maps/ztf.yaml'
fdecat = 'schema_maps/decat.yaml'

ztf = {
    'objectId':         'objectId',
    'source':           'candidate',
    'sourceId':         'candid',
    'prvSources':       'prv_candidates',
    'cutoutScience':    'cutoutScience',
    'cutoutTemplate':   'cutoutTemplate',
    'cutoutDifference': 'cutoutDifference',
}
decat = {
    'objectId':         'objectid',
    'source':           'triggersource',
    'sourceId':         'sourceid',
    'prvSources':       'sources',
    'cutoutScience':    'scicutout',
    'cutoutTemplate':   'refcutout',
    'cutoutDifference': 'diffcutout',
}

# write the files
for smap, fname in zip([ztf, decat], [fztf, fdecat]):
    with open(f'../broker/{fname}', "w") as f:
        yaml.dump(smap, f, sort_keys=False)

# upload the files to GCS
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
SURVEY = 'ztf'
TESTID = 'schema'
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

## BigQuery schema json
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
---

## Test the changes
<!-- fs -->
Dashboard snapshots:
- [Live](https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-decat-testschema)

Create a broker instance
```bash
# get the code
git clone https://github.com/mwvgroup/Pitt-Google-Broker
cd Pitt-Google-Broker
git checkout survey/tjr/decam
cd broker/setup_broker

# create the instance
survey="decat"
testid="testschema"
teardown="False"
./setup_broker.sh "$testid" "$teardown" "$survey"

# name some things
consumerVM="${survey}-consumer-${testid}"
nconductVM="${survey}-night-conductor-${testid}"
zone="us-central1-a"

# upload credentials
consumerDir="/home/broker/consumer"
localDir="/Users/troyraen/Documents/PGB/repo"
sudo gcloud compute scp "${localDir}/krb5.conf" "${consumerVM}:/etc/krb5.conf" --zone="$zone"
sudo gcloud compute ssh "$consumerVM" --zone="$zone"  --command="mkdir -p ${consumerDir}"
sudo gcloud compute scp "${localDir}/pitt-reader.user.keytab" "${consumerVM}:${consumerDir}/pitt-reader.user.keytab" --zone="$zone"

# stop the VMs after installs are done (this takes ~20 min.
# check the CPU usage on the Dashboard, it should fall below 1%)
gcloud compute instances stop "$consumerVM" "$nconductVM" --zone="$zone"
```

Run the broker, connected to a real DECAT topic
```bash
# start the night
NIGHT="START"
KAFKA_TOPIC="decat_test_only"
# KAFKA_TOPIC="decat_20210411_2021A-0113"
gcloud compute instances add-metadata "$nconductVM" --zone="$zone" \
        --metadata NIGHT="$NIGHT",KAFKA_TOPIC="$KAFKA_TOPIC"
gcloud compute instances start "$nconductVM" --zone "$zone"

# end the night
NIGHT="END"
gcloud compute instances add-metadata "$nconductVM" --zone="$zone" \
        --metadata NIGHT="$NIGHT"
gcloud compute instances start "$nconductVM" --zone "$zone"

```

Run the broker with the consumer simulator
```bash
# start the night
NIGHT="START"
KAFKA_TOPIC="NONE" # tell night-conductor to skip booting up consumer VM
gcloud compute instances add-metadata "$nconductVM" --zone="$zone" \
        --metadata NIGHT="$NIGHT",KAFKA_TOPIC="$KAFKA_TOPIC"
gcloud compute instances start "$nconductVM" --zone "$zone"
```
```python
import sys
path_to_dev_utils = '/Users/troyraen/Documents/PGB/repo/dev_utils'
sys.path.append(path_to_dev_utils)
from consumer_sims import ztf_consumer_sim as zcs

survey = 'decat'
testid = 'testschema'
topic_id = f'{survey}-alerts-{testid}'  # syntax not yet updated in consumer sim

alertRate = (60, 'perMin')
    # unit (str) options: 'perSec', 'perMin', 'perHr', 'perNight'(=per 10 hrs)
# alertRate = (N, 'once')
runTime = (2, 'min')  # (int, str)
    # unit (str) options: 'sec', 'min', 'hr', 'night'(=10 hrs)

zcs.publish_stream(testid, alertRate, runTime, topic_id=topic_id)
```
```bash
# end the night
NIGHT="END"
gcloud compute instances add-metadata "$nconductVM" --zone="$zone" \
        --metadata NIGHT="$NIGHT"
gcloud compute instances start "$nconductVM" --zone "$zone"
```

Delete the broker instance
```bash
survey="decat"  # make sure the original case still works properly
testid="testschema"
teardown="True"
./setup_broker.sh "$testid" "$teardown" "$survey"
```


<!-- fe Test the changes -->
