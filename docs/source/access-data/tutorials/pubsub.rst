Pub/Sub Streams
===============

**Learning Objectives:**

1.  :ref:`Subscribe to a Pitt-Google Pub/Sub stream <create-subscription>`
2.  :ref:`Pull messages from your subscription <pull-messages>`

Pub/Sub is an asynchronous, publish–subscribe messaging service.
The Pitt-Google broker publishes alerts and value-added data to multiple topics
(see :ref:`here <access-data/data-overview:Pub/Sub>` for a list).
You can subscribe to one or more of these topics, and then pull and process the data
either in real-time or up to 7 days after a message was published.

This tutorial demonstrates two methods: Python and the command line.
The Python sections use the pgb-utils package, which contains example functions to
complete these tasks.
These example functions are thin wrappers for the Google API, which offers more
options than those presented here.
Interested users are encouraged to look at and extend the pgb-utils source code
(see :doc:`docs <../../api/pgb-utils/pubsub>`) to harness the full power
of the Google API.

For more information, see:

- `What is Pub/Sub? <https://cloud.google.com/pubsub/docs/overview>`__
- Python client documentation:

        - :doc:`pgb_utils.pubsub <../../api/pgb-utils/pubsub>`
        - `google.cloud.pubsub
          <https://googleapis.dev/python/pubsub/latest/index.html>`__
          (pgb-utils.pubsub contains thin wrappers for this API)

- `gcloud CLI reference <https://cloud.google.com/sdk/gcloud/reference>`__
- `All Google APIs for Pub/Sub
  <https://cloud.google.com/pubsub/docs/apis>`__
  (many languages are available)

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

The code below will create a subscription in your GCP project
that is attached to a topic in our project.
This only needs to be done once per topic.

See :ref:`Data Overview: Pub/Sub <access-data/data-overview:Pub/Sub>`
for a list of available topics.
The code below subscribes the user to "ztf-loop", a special stream intended for testing.
We publish recent ZTF alerts to this topic at a constant rate of 1 per second,
day and night.

After your subscription is created, messages we publish to the topic are
immediately available in your subscription. They will remain there until
they are either pulled and acknowledged or until they expire (7 days,
max). Messages published before your subscription was created are not available.

You can also view and manage the subscriptions in your GCP project at
any time from the web `Console Subscriptions
page <https://console.cloud.google.com/cloudpubsub/subscription>`__ (you
may need to select your project from the dropdown at the top).

Method A: Python
~~~~~~~~~~~~~~~~

.. code:: python

    import pgb_utils as pgb

    # choose an existing Pitt-Google topic
    topic_name = 'ztf-loop'

    # name your subscription whatever you'd like
    subscription_name = 'ztf-loop'

    # create the subscription
    subscription = pgb.pubsub.create_subscription(
        topic_name, subscription_name=subscription_name
    )
    # you can look at the subscription object, but you don't need to do anything with it

Method B: Command line
~~~~~~~~~~~~~~~~~~~~~~

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

The code below pulls and acknowledges messages from a subscription.
Once the subscription is created, messages published to the topic will be available
in the subscription until they are either pulled and acknowledged,
or until they expire (7 days max).

Method A: Python
~~~~~~~~~~~~~~~~

In Python you have the option to either pull a fixed number of messages
or to pull and process messages continuously in streaming mode.

Option 1: Pull a fixed number of messages. Useful for testing.

.. code:: python

    import pgb_utils as pgb

    # setup
    subscription_name = 'ztf-loop'
    max_messages = 5

    # pull and acknowledge messages
    msgs = pgb.pubsub.pull(subscription_name, max_messages=max_messages)

    # msgs is a list containing alerts as bytes
    # you can now process them however you'd like
    # here we simply convert the first alert to a pandas dataframe
    df = pgb.utils.decode_alert(msgs[0], return_format='df')

Option 2: Pull messages in streaming mode.
This method pulls, processes, and acknowledges messages continuously in a
background thread.
To use this method, we must first create a "callback" function that accepts
a single message, processes the data, and then acknowledges the message.

By default, the ``streamingPull`` function below does not return until the background thread either times out or encounters an error,
but this blocking behavior can be controlled using a keyword.

.. code:: python

    import pgb_utils as pgb

    # create the callback function
    def callback(message):
        # extract the message data
        alert = message.data  # bytes

        # process the message
        # in this example we simply convert it to a dataframe and print the 1st row
        df = pgb.utils.decode_alert(alert, return_format='df')
        print(df.head(1))

        # acknowledge the message so it is not delivered again
        message.ack()

    # open the connection and process the streaming messages
    subscription_name = 'ztf-loop'
    timeout = 5  # maximum number of seconds to wait for a message before exiting
    pgb.pubsub.streamingPull(subscription_name, callback, timeout=timeout)


Method B: Command line
~~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

    SUBSCRIPTION="ztf-loop"
    limit=1  # default=1
    gcloud pubsub subscriptions pull $SUBSCRIPTION --auto-ack --limit=$limit


.. _delete-subscription:

Cleanup: Delete a subscription
--------------------------------

If you are not using a subscription you should delete it so that messages do not
continue to accrue and count against your quota.

Method A: Python
~~~~~~~~~~~~~~~~

.. code:: python

    import pgb_utils as pgb

    subscription_name = 'ztf-loop'
    pgb.pubsub.delete_subscription(subscription_name)

Method B: Command line
~~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

    SUBSCRIPTION_NAME="ztf-loop"
    gcloud pubsub subscriptions delete $SUBSCRIPTION_NAME

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
