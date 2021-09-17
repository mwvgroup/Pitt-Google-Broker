# Cloud Function to load alerts to BigQuery tables

Skip to [Test the end result](#test-the-end-result)


## Test pieces of the cloud fnc

```bash
export GCP_PROJECT=$GOOGLE_CLOUD_PROJECT
export SURVEY=ztf
export TESTID=storebq
# cd /Users/troyraen/Documents/broker/storebq/broker/cloud_functions/store_BigQuery
```

```python
import troy_fncs as troy
from broker_utils import data_utils, gcp_utils, schema_maps
import main

schema_map = schema_maps.load_schema_map(SURVEY, TESTID)
kwargs = {'drop_cutouts': True, 'schema_map': schema_map}
alert_dict = troy.load_alert_file(kwargs)

gcp_utils.insert_rows_bigquery(table_id, [alert_dict])
```

## setup/run/stop/delete the testing instance

Create/delete a broker testing instance
```bash
# get the code
git clone https://github.com/mwvgroup/Pitt-Google-Broker
cd Pitt-Google-Broker
git checkout tjr/store_bigquery
cd broker/setup_broker

# create/delete the instance
survey="ztf"
testid="storebq"
teardown="False"
# teardown="True"
./setup_broker.sh "$testid" "$teardown" "$survey"

nconductVM="${survey}-night-conductor-${testid}"
gcloud compute instances set-machine-type $nconductVM --machine-type g1-small
```


<!-- Start the broker
```bash
topic="${survey}-cue_night_conductor-${testid}"
cue=START
attr=KAFKA_TOPIC=NONE
# attr=topic_date=20210820
gcloud pubsub topics publish "$topic" --message="$cue" --attribute="$attr"
``` -->

Push some alerts through
```python
from broker_utils import consumer_sim

testid = 'storebq'
survey = 'ztf'
instance = (survey, testid)

alert_rate = (100, 'once')
consumer_sim.publish_stream(alert_rate, instance)

# alert_rate = 'ztf-active-avg'
# runtime = (10, 'min')  # options: 'sec', 'min', 'hr', 'night'(=10 hrs)
# consumer_sim.publish_stream(alert_rate, instance, runtime)
```

Stop the broker, which triggers night conductor to shut everything down and process the streams.
```bash
topic="${survey}-cue_night_conductor-${testid}"
cue=END
gcloud pubsub topics publish "$topic" --message="$cue"
```
<!--

## Test the end result

```python
import os

project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
survey = 'ztf'
testid = 'storebq'
dataset = f'{survey}_alerts_{testid}'

table = 'alerts'
query = f'SELECT * FROM `{project_id}.{dataset}.{table}` LIMIT 100'
query_job = gcp_utils.query_bigquery(query)
alerts_df = query_job.to_dataframe()

table = 'DIASource'
query = f'SELECT * FROM `{project_id}.{dataset}.{table}` LIMIT 100'
dia_df = gcp_utils.query_bigquery(query)

for table in tables:
    query = (
            f'SELECT * '
            f'FROM `{project_id}.{dataset}.{table}` '
            f'WHERE objectId={objectId} '
        )
    df = gcp_utils.query_bigquery(query)
``` -->
