# Pub/Sub Streams

- [Prerequisites](#prerequisites)
- [Create a subscription](#create-a-subscription)  
- [Pull Messages](#pull-messages)

This tutorial covers subscribing to our Pub/Sub streams and pulling messages via two methods: the pgb-utils Python package, and the gcloud CLI.

You can view and manage the subscriptions in your GCP project at any time from the [Console Subscriptions page](https://console.cloud.google.com/cloudpubsub/subscription) (you may need to select your project from the dropdown at the top).

For more information, see:
- [What is Pub/Sub?](https://cloud.google.com/pubsub/docs/overview)
- [Google Cloud Pub/Sub Python client documentation](https://googleapis.dev/python/pubsub/latest/index.html) (the pgb-utils functions used below are thin wrappers for this API)
- [gcloud CLI reference](https://cloud.google.com/sdk/gcloud/reference)

## Prerequisites

1. Complete the [Initial Setup](initial-setup.md). Be sure to:
    - enable the Pub/Sub API
    - install the pgb-utils package if you want to use Python
    - install the CLI if you want to use the command line

## Create a subscription

Here you will create a Pub/Sub subscription in your GCP project that is attached to a topic in our project. This only needs to be done once per desired topic.

After your subscription is created, messages we publish to the topic are immediately available in your subscription. They will remain there until they are either pulled and acknowledged or until they expire (7 days, max).

__Method A: Python__
```python
import pgb_utils as pgb

topic_name = 'ztf-loop'
subscription_name = 'ztf-loop'  # you can call this whatever you want
subscription = pgb.pubsub.subscribe(topic)
```

__Method B: Command line__
```bash
# create the subscription
TOPIC="ztf-loop"
SUBSCRIPTION="ztf-loop"  # choose a name for your subscription
gcloud pubsub subscriptions create $SUBSCRIPTION --topic=$TOPIC --topic-project="ardent-cycling-243415"
```


## Pull Messages

__Method A: Python__
```python
# from google.cloud import pubsub_v1
# import os
from pgb_utils import pubsub as pgbps

subscription = 'ztf-loop'

# pull messages
msgs = pgbps.pull(subscription)
df = pgbps.decode_ztf_alert(msgs[0], return_format='df')


# streaming pull messages
def callback(message):
    # process here
    df = pgbps.decode_ztf_alert(message.data, return_format='df')
    print(df.head(1))
    message.ack()

pgbps.streamingPull(subscription, callback, timeout=4)
```

__Method B: Command line__
```bash
SUBSCRIPTION="ztf-loop"
limit=1  # default=1
gcloud pubsub subscriptions pull $SUBSCRIPTION --auto-ack --limit=$limit
```


<!--

## Process messages using Dataflow

```python

with beam.Pipeline() as pipeline:
    (
        pipeline
        | 'Read BigQuery' >> beam.io.ReadFromBigQuery(**read_args)
        | 'Type cast to DataFrame' >> beam.ParDo(pgb.beam.ExtractHistoryDf())
        | 'Is nearby known SS object' >> beam.Filter(nearby_ssobject)
        | 'Calculate mean magnitudes' >> beam.ParDo(calc_mean_mags())
        | 'Write results' >> beam.io.WriteToText(beam_outputs_prefix)
    )
``` -->
