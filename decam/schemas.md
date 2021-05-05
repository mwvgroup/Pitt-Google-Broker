# Schemas

Table of Contents:
- [Create Schema Maps](#create-schema-maps)
- [BigQuery schema json](#bigquery-schema-json)
- [Test the changes](#test-the-changes)
- [Download and look at an Avro](#download-and-look-at-an-avro)

---

## Create Schema Maps
<!-- fs -->
```python
from google.cloud import storage
import os
import yaml

fztf = 'broker_utils/schema_maps/ztf.yaml'
fdecat = 'broker_utils/schema_maps/decat.yaml'

ztf = {
    # include some extra info
    'SURVEY':           'ztf',
    'FILTER_MAP':       {1: 'g', 2: 'r', 3: 'i'},
    # primary fields, alphabetical
    'objectId':         'objectId',
    'prvSources':       'prv_candidates',
    'source':           'candidate',
    'sourceId':         'candid',
    # other fields, alphabetical
    'cutoutDifference': 'cutoutDifference',
    'cutoutScience':    'cutoutScience',
    'cutoutTemplate':   'cutoutTemplate',
    'filter':           'fid',
    'mag':              'magpsf',
    'magerr':           'sigmapsf',
    'magzp':            'magzpsci',
}
decat = {
    # include some extra info
    'SURVEY':           'decat',
    'FILTER_MAP':       {'g DECam SDSS c0001 4720.0 1520.0': 'g',
                         'r DECam SDSS c0002 6415.0 1480.0': 'r'
                        },
    # primary fields, alphabetical
    'objectId':         'objectid',
    'prvSources':       'sources',
    'source':           'triggersource',
    'sourceId':         'sourceid',
    # other fields, alphabetical
    'cutoutDifference': 'diffcutout',
    'cutoutScience':    'scicutout',
    'cutoutTemplate':   'refcutout',
    'filter':           'filter',
    'mag':              'mag',
    'magerr':           'magerr',
    'magzp':            'magzp',
}

# write the files
for smap, fname in zip([ztf, decat], [fztf, fdecat]):
    with open(f'../broker/{fname}', "w") as f:
        yaml.dump(smap, f, sort_keys=False)

# upload the files to GCS
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
SURVEY = 'decat'
TESTID = 'testschema'
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
KAFKA_TOPIC="decat_20210414_2021A-0113"
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
survey="decat"
testid="testschema"
teardown="True"
./setup_broker.sh "$testid" "$teardown" "$survey"
```

<!-- fe Test the changes -->
---


## Download and look at an Avro
<!-- fs -->
(Requires that we have already ingested an alert to the `alert_avros` bucket.)

```python
from broker_utils import gcp_utils as bgu
from broker_utils import data_utils as bdu

# download a file
filename = 'DC21baaa.570349.decat_20210414_2021A-0113.avro'
survey, testid = 'decat', 'testschema'
bucket_id = f'{survey}-alert_avros-{testid}'
localdir = '/Users/troyraen/Documents/PGB/repotest/decam'
bgu.cs_download_file(localdir, bucket_id, filename)

# load the file to a dict
alertDict = bdu.alert_avro_to_dict(f'{localdir}/{filename}')

# load the dict to BigQuery
table_id = f'{survey}_alerts_{testid}.alerts'
bgu.bq_insert_rows(table_id, [alertDict])
```
<!-- fe Download and look at an Avro -->
