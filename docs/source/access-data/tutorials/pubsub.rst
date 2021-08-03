Pub/Sub Streams
===============

**Learning Objectives:**

1.  :ref:`Subscribe to one of our Pub/Sub streams <create-subscription>`
2.  :ref:`Pull messages from your subscription <pull-messages>`

This tutorial covers subscribing to our Pub/Sub streams and pulling
messages. It demonstrates two methods: Python using the pgb-utils
package; and the command line using Google's gcloud CLI.

For more information, see:

- `What is Pub/Sub? <https://cloud.google.com/pubsub/docs/overview>`__
- `All Google APIs and references
  <https://cloud.google.com/pubsub/docs/apis>`__
  (many languages are available)
- Python client documentation:

        - `google.cloud.pubsub
          <https://googleapis.dev/python/pubsub/latest/index.html>`__
          (pgb-utils contains thin wrappers for this API)
        - :doc:`pgb_utils.pubsub <../../api/pgb-utils/pubsub>`

- `gcloud CLI reference <https://cloud.google.com/sdk/gcloud/reference>`__

Prerequisites
-------------

1. Complete the :doc:`initial-setup`. Be sure to:

   -  set your environment variables
   -  enable the Pub/Sub API
   -  install the pgb-utils package if you want to use Python
   -  install the CLI if you want to use the command line

.. _create-subscription:

Create a subscription
---------------------

The code below will create a Pub/Sub subscription in your GCP project
that is attached to a topic in our project. This only needs to be done
once per desired topic.

See :ref:`Data Overview: Pub/Sub <access-data/data-overview:Pub/Sub>`
for a list of available topics.

After your subscription is created, messages we publish to the topic are
immediately available in your subscription. They will remain there until
they are either pulled and acknowledged or until they expire (7 days,
max). Messages published before your subscription was created are not available.

You can also view and manage the subscriptions in your GCP project at
any time from the web `Console Subscriptions
page <https://console.cloud.google.com/cloudpubsub/subscription>`__ (you
may need to select your project from the dropdown at the top).

**Method A: Python**

.. code:: python

    import pgb_utils as pgb

    # choose an existing Pitt-Google topic
    topic_name = 'ztf-loop'

    # name your subscription whatever you'd like
    subscription_name = 'ztf-loop'

    # create the subscription
    subscription = pgb.pubsub.subscribe(topic)

**Method B: Command line**

.. code:: bash

    # choose an existing Pitt-Google topic
    TOPIC_NAME="ztf-loop"

    # name your subscription whatever you'd like
    SUBSCRIPTION_NAME="ztf-loop"

    # create the subscription
    gcloud pubsub subscriptions create $SUBSCRIPTION_NAME \
        --topic=$TOPIC_NAME \
        --topic-project="ardent-cycling-243415"  # Pitt-Google project ID

.. _pull-messages:

Pull Messages
-------------

**Method A: Python**

Two options:

1. Pull a fixed number of messages. Useful for testing.

.. code:: python

    import pgb_utils as pgb

    # pull messages
    subscription_name = 'ztf-loop'
    max_messages = 5
    msgs = pgb.pubsub.pull(subscription_name, max_messages=max_messages)  # list[bytes,]

    # now process the messages. for example:
    # convert the bytes to a pandas dataframe
    df = pgb.pubsub.decode_ztf_alert(msgs[0], return_format='df')

2. Pull messages continuously.

.. code:: python

    import pgb_utils as pgb

    # create a function that executes your processing logic
    # and then acknowledge the message
    def callback(message):
        # your processing logic here. for example:
        # convert the bytes to a pandas dataframe and print the 1st row
        df = pgbps.decode_ztf_alert(message.data, return_format='df')
        print(df.head(1))

        # acknowledge the message
        message.ack()

    # open the connection and process the streaming messages
    subscription_name = 'ztf-loop'
    timeout = 5
    pgb.pubsub.streamingPull(subscription_name, callback, timeout=timeout)


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
