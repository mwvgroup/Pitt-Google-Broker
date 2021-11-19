## Make the BigQuery table

```bash
cd /Users/troyraen/Documents/broker/repo3/broker/setup_broker
PROJECT_ID=$GOOGLE_CLOUD_PROJECT
dataset=ztf_alerts
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
tmp = f'{nanonow*1e-9}'.split('.')[1]

# convert pubsub publish_time to a datetime
psmsg = gcp_utils.pull_pubsub('ztf-alerts-reservoir', msg_only=False)[0]
seconds = psmsg.message.publish_time.seconds
nanoseconds = psmsg.message.publish_time.nanos
tmpnano = f'{nanoseconds*1e-9}'.split('.')[1]
fseconds = float(f'{seconds}.{tmpnano}')
dt = datetime.utcfromtimestamp(fseconds)
```

<!-- ## Collect metadata from all messages in a subscription

```python
from broker_utils import gcp_utils
import pandas as pd
# import time

objectId = schema_map['objectId']  # survey-specific field name for the objectId
sourceId = schema_map['sourceId']  # survey-specific field name for the sourceId

metadata_list = []
metadata_dfs_list = []

def callback(received_message):
    global metadata_list

    # collect the metadata
    metadata = {**received_message.message.attributes}
    metadata['message_id'] = received_message.message.message_id
    # publish time is given as two ints: seconds and nanoseconds
    # package it into a single float
    pubtime = received_message.message.publish_time
    tmpnano = f'{pubtime.nanos*1e-9}'.split('.')[1]  # preserve zero padding for the decimal
    metadata['publish_time'] = float(f'{pubtime.seconds}.{tmpnano}')

    metadata_list.append(metadata)

    # for now, we assume everything went fine... update this if problems arise
    success = True
    return success


# subscription = 'ztf-SuperNNova'
subscription = 'ztf-alerts-reservoir'
max_msgs = 2
num_processed = 1  # >0 to start the loop
while num_processed > 0:
    num_processed = gcp_utils.pull_pubsub(
        subscription,
        max_messages=max_msgs,
        msg_only=False,
        callback=callback,
        return_count=True,
    )

    if num_processed == 0:
        # wait, then try one more time
        time.sleep(10)
        num_processed = gcp_utils.pull_pubsub(
            subscription,
            max_messages=max_msgs,
            msg_only=False,
            callback=callback,
            return_count=True,
        )

# cast the collected metadata to a df
df = pd.DataFrame(metadata_list)
df.set_index([objectId, sourceId], inplace=True)
df.rename(columns=lambda x: f'{x}.{subscription}', inplace=True)
metadata_dfs_list.append(df)
``` -->

## Test process_pubsub_counters.py

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
msgs = gcp_utils.pull_pubsub('ztf-alerts-reservoir', max_messages=max_msgs)
publisher = pubsub_v1.PublisherClient()
for msg in msgs:
    alert_dict_tmp = data_utils.decode_alert(msg)
    dropcols = ['cutoutScience', 'cutoutTemplate', 'cutoutDifference']
    alert_dict = {k: v for k, v in alert_dict_tmp.items() if k not in dropcols}
    gcp_utils.publish_pubsub('ztf-exgalac_trans', alert_dict, publisher=publisher)

# process metadata from the SNN subscription

# test the SubscriptionMetadataCollector
sub_name = 'ztf-SuperNNova-counter'
schema_map = schema_maps.load_schema_map('ztf', 'False')
sub_collector = ppc.SubscriptionMetadataCollector(sub_name, schema_map)
# sub_collector.pull_and_process_messages()
sub_collector._pull_messages_and_extract_metadata()  # sub_collector.metadata_dicts_list
sub_collector._package_metadata_into_df()  # sub_collector.metadata_df
sub_collector.metadata_df

# test the MetadataCollector
# publish more messages to process using code above
collector = ppc.MetadataCollector('ztf', False, 500)
collector._collect_all_metadata()  # collector.metadata_dfs_list
collector._group_metadata_by_candidate()
gcp_utils.insert_rows_bigquery(collector.bq_table, collector.metadata_dicts_list)
# collector.collect_and_store_all_metadata()
```

## Process last night's ZTF stream

```python
import process_pubsub_counters as ppc
survey = 'ztf'
# testid = 'v070'
testid = False
batch_size = 500

collector = ppc.MetadataCollector(survey, testid, batch_size)
collector.collect_and_store_all_metadata()
```
