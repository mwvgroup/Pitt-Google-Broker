Pub/Sub Streams
===============

-  `Prerequisites <#prerequisites>`__
-  `Create a subscription <#create-a-subscription>`__
-  `Pull Messages <#pull-messages>`__

This tutorial covers subscribing to our Pub/Sub streams and pulling
messages. It demonstrates two methods: 1) Python, using the pgb-utils
package; and 2) the command line, using Google's gcloud CLI.

For more information, see: - `What is
Pub/Sub? <https://cloud.google.com/pubsub/docs/overview>`__ - `All
Google APIs and
references <https://cloud.google.com/pubsub/docs/apis>`__ (there are
many access methods beyond the two presented in this tutorial) - `Python
client
documentation <https://googleapis.dev/python/pubsub/latest/index.html>`__
(the pgb-utils functions used below are thin wrappers for this API) -
`gcloud CLI reference <https://cloud.google.com/sdk/gcloud/reference>`__

Prerequisites
-------------

1. Complete the `Initial Setup <initial-setup.md>`__. Be sure to:

   -  set your environment variables
   -  enable the Pub/Sub API
   -  install the pgb-utils package if you want to use Python
   -  install the CLI if you want to use the command line

Create a subscription
---------------------

The code below will create a Pub/Sub subscription in your GCP project
that is attached to a topic in our project. This only needs to be done
once per desired topic.

After your subscription is created, messages we publish to the topic are
immediately available in your subscription. They will remain there until
they are either pulled and acknowledged or until they expire (7 days,
max).

You can also view and manage the subscriptions in your GCP project at
any time from the web `Console Subscriptions
page <https://console.cloud.google.com/cloudpubsub/subscription>`__ (you
may need to select your project from the dropdown at the top).

**Method A: Python**

.. code:: python

    import pgb_utils as pgb

    topic_name = 'ztf-loop'
    subscription_name = 'ztf-loop'  # you can call this whatever you want
    subscription = pgb.pubsub.subscribe(topic)

**Method B: Command line**

.. code:: bash

    # create the subscription
    TOPIC="ztf-loop"
    SUBSCRIPTION="ztf-loop"  # choose a name for your subscription
    gcloud pubsub subscriptions create $SUBSCRIPTION --topic=$TOPIC --topic-project="ardent-cycling-243415"

Pull Messages
-------------

**Method A: Python**

.. code:: python

    # from google.cloud import pubsub_v1
    # import os
    import pgb_utils as pgb

    subscription = 'ztf-loop'

    # pull messages
    msgs = pgb.pubsub.pull(subscription)
    df = pgb.pubsub.decode_ztf_alert(msgs[0], return_format='df')


    # streaming pull messages
    def callback(message):
        # process here
        df = pgbps.decode_ztf_alert(message.data, return_format='df')
        print(df.head(1))
        message.ack()

    pgb.pubsub.streamingPull(subscription, callback, timeout=4)

**Method B: Command line**

.. code:: bash

    SUBSCRIPTION="ztf-loop"
    limit=1  # default=1
    gcloud pubsub subscriptions pull $SUBSCRIPTION --auto-ack --limit=$limit

.. raw:: html

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


