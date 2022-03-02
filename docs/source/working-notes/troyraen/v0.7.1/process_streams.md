# Create and test process_pubsub_counters.py

- [broker/night_conductor/end_night/process_pubsub_counters.py](../../../broker/night_conductor/end_night/process_pubsub_counters.py)

## Make the BigQuery table

```bash
cd /Users/troyraen/Documents/broker/repo3/broker/setup_broker
PROJECT_ID=$GOOGLE_CLOUD_PROJECT
dataset=ztf_alerts_v071
table=metadata
survey=ztf
bq mk --table ${PROJECT_ID}:${dataset}.${table} templates/bq_${survey}_${table}_schema.json
```

## Timestamps exploration

```python
import time
from datetime import datetime
from broker_utils import gcp_utils

# test with current time
now = time.time()
secnow = int(now)
nanonow = int((now - secnow) * 10**9)
tmp = f"{nanonow*1e-9}".split(".")[1]

# convert pubsub publish_time to a datetime
psmsg = gcp_utils.pull_pubsub("ztf-alerts-reservoir", msg_only=False)[0]
seconds = psmsg.message.publish_time.seconds
nanoseconds = psmsg.message.publish_time.nanos
tmpnano = f"{nanoseconds*1e-9}".split(".")[1]
fseconds = float(f"{seconds}.{tmpnano}")
dt = datetime.utcfromtimestamp(fseconds)
```

## Test process_pubsub_counters.py on the SuperNNova cloud function

```bash
cd /Users/troyraen/Documents/broker/repo3/broker/night_conductor/end_night/
```

```python
from google.cloud import pubsub_v1
from broker_utils import data_utils, gcp_utils, schema_maps
import process_pubsub_counters as ppc

# pull some messages and publish them to the ztf-exgalac_trans topic
# so the SNN cloud fnc processes them
max_msgs = 2
msgs = gcp_utils.pull_pubsub("ztf-alerts-reservoir", max_messages=max_msgs)
publisher = pubsub_v1.PublisherClient()
for msg in msgs:
    alert_dict_tmp = data_utils.decode_alert(msg)
    dropcols = ["cutoutScience", "cutoutTemplate", "cutoutDifference"]
    alert_dict = {k: v for k, v in alert_dict_tmp.items() if k not in dropcols}
    gcp_utils.publish_pubsub("ztf-exgalac_trans", alert_dict, publisher=publisher)

# process metadata from the SNN subscription

# test the SubscriptionMetadataCollector
sub_name = "ztf-SuperNNova-counter"
schema_map = schema_maps.load_schema_map("ztf", "False")
sub_collector = ppc.SubscriptionMetadataCollector(sub_name, schema_map)
# sub_collector.pull_and_process_messages()
sub_collector._pull_messages_and_extract_metadata()  # sub_collector.metadata_dicts_list
sub_collector._package_metadata_into_df()  # sub_collector.metadata_df
sub_collector.metadata_df

# test the MetadataCollector
# publish more messages to process using code above
collector = ppc.MetadataCollector("ztf", False, 500)
collector._collect_all_metadata()  # collector.metadata_dfs_list
collector._group_metadata_by_candidate()
gcp_utils.insert_rows_bigquery(collector.bq_table, collector.metadata_dicts_list)
# collector.collect_and_store_all_metadata()
```

## Test process_pubsub_counters.py on the full pipeline

```bash
cd /Users/troyraen/Documents/broker/repo3/broker/night_conductor/end_night/
```

```python
# from google.cloud import pubsub_v1
from broker_utils import consumer_sim, schema_maps
import process_pubsub_counters as ppc

testid = "v071"
survey = "ztf"
instance = (survey, testid)
alert_rate = (25, "once")
# alert_rate = 'ztf-active-avg'
# runtime = (30, 'min')  # options: 'sec', 'min', 'hr', 'night'(=10 hrs)
consumer_sim.publish_stream(alert_rate, instance)

# process metadata

# test the SubscriptionMetadataCollector on each subscription
sub_names = ppc._resource_names(survey, testid)["subscriptions"]
schema_map = schema_maps.load_schema_map(survey, testid)
batch_size = 500

i = 1
sub_collector = ppc.SubscriptionMetadataCollector(sub_names[i], schema_map, batch_size)
sub_collector.pull_and_process_messages()
# sub_collector._pull_messages_and_extract_metadata()  # sub_collector.metadata_dicts_list
# sub_collector._package_metadata_into_df()  # sub_collector.metadata_df
sub_collector.metadata_df

# test the MetadataCollector
# publish more messages to process using code above
collector = ppc.MetadataCollector(survey, testid, batch_size)
# collector.collect_and_store_all_metadata()
collector._collect_all_metadata()  # collector.metadata_dfs_dict
collector._join_metadata()  # collector.metadata_df
collector._load_metadata_to_bigquery()
```

## Process last night's ZTF stream

In python:

```python
import process_pubsub_counters as ppc

survey = "ztf"
# testid = 'v070'
testid = False
batch_size = 2
single_batch = True
timeout = 5

# collector = ppc.MetadataCollector(survey, testid, batch_size, single_batch)
collector = ppc.MetadataCollector(survey, testid, timeout=timeout)
collector.collect_and_store_all_metadata()
```

Command-line:

```bash
survey='ztf'
b=2
sb=True
t=5
python3 process_pubsub_counters.py --survey=$survey --production --timeout=$t
# python3 process_pubsub_counters.py --survey=$survey --production --batch_size=$b --single_batch=$sb
```

### Streaming

```python
import process_pubsub_counters as ppc

survey = "ztf"
testid = False
timeout = 2
testrun = True

collector = ppc.MetadataCollector(survey, testid, timeout=timeout, testrun=testrun)
collector.collect_and_store_all_metadata()

sub_name = "ztf-alert_avros-counter"
topic_stub = "alert_avros"
sub_collector = ppc.SubscriptionMetadataCollector(
    (topic_stub, sub_name), timeout=timeout
)
# sub_collector.pull_and_process_messages()
sub_collector._pull_messages_and_extract_metadata()  # sub_collector.metadata_dicts_list
sub_collector._package_metadata_into_df()  # sub_collector.metadata_df
sub_collector.metadata_df
```

Command-line:

```bash
survey='ztf'
testid='False'
to=2
tr=True
python3 process_pubsub_counters.py --survey=$survey --production --timeout=$to --testrun=$tr
```
