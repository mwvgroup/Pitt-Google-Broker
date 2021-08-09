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
    subscription = pgb.pubsub.create_subscription(topic_name, subscription_name)
    # you can look at the subscription object, but you don't need to do anything with it

For more information, view the docstring and source code for
:meth:`pgb_utils.pgb_utils.pubsub.create_subscription`.


Method B: Command line
~~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

    # choose an existing Pitt-Google topic
    topic_name="ztf-loop"

    # name your subscription whatever you'd like
    subscription_name="ztf-loop"

    # create the subscription
    gcloud pubsub subscriptions create $subscription_name \
        --topic=$topic_name \
        --topic-project="ardent-cycling-243415"  # Pitt-Google project ID

.. _pull-messages:

Pull Messages
-------------

The code below pulls and acknowledges messages from a subscription.

Method A: Python
~~~~~~~~~~~~~~~~

In Python you have the option to either
(1) pull a fixed number of messages and then process them, or
(2) pull and process messages continuously in streaming mode.

Pull a fixed number of messages
*******************************

With this method, a fixed number (maximum) of messages are returned in a list.
You can then process them however you'd like.

.. code:: python

    import pgb_utils as pgb

    # pull and acknowledge messages
    subscription_name = 'ztf-loop'
    max_messages = 5
    msgs = pgb.pubsub.pull(subscription_name, max_messages=max_messages)

    # msgs is a list containing the alert data as bytes
    # you can now process them however you'd like

    # here we simply convert the first alert to an astropy table
    table = pgb.pubsub.decode_message(msgs[0], return_alert_as='table')

For more information, view the docstring and source code for
:meth:`pgb_utils.pgb_utils.pubsub.pull`.

Pull messages in streaming mode
********************************

This method pulls, processes, and acknowledges messages continuously.

To use this method, we must first create a "callback" function that accepts
a single message, processes the data according to the user's desires,
and then acknowledges the message.
The message object is described `here
<https://cloud.google.com/pubsub/docs/reference/rpc/google.pubsub.v1#google.pubsub.v1.PubsubMessage>`__.

.. code:: python

    import pgb_utils as pgb

    # create the callback function
    def callback(message):
        # extract the message data
        alert = message.data  # bytes

        # process the message however you'd like

        # here we simply convert it to a dataframe and print the 1st row
        df = pgb.pubsub.decode_message(alert, return_alert_as='df')
        print(df.head(1))

        # acknowledge the message so it is not delivered again
        message.ack()

    # start streaming messages
    subscription_name = 'ztf-loop'
    pgb.pubsub.streamingPull(subscription_name, callback)
    # use Control+C to cancel the streaming

For more information, view the docstring and source code for
:meth:`pgb_utils.pgb_utils.pubsub.streamingPull`.

Method B: Command line
~~~~~~~~~~~~~~~~~~~~~~

This method returns a fixed number (maximum) of messages.
See `gcloud pubsub subscriptions pull
<https://cloud.google.com/sdk/gcloud/reference/pubsub/subscriptions/pull>`__
(format options are listed
`here <https://cloud.google.com/sdk/gcloud/reference#--format>`__).

.. code:: bash

    # set these parameters as desired
    subscription_name="ztf-loop"
    max_messages=5
    format=json

    # pull messages
    gcloud pubsub subscriptions pull $subscription_name \
        --limit $max_messages \
        --format $format \
        --auto-ack

.. _delete-subscription:

Cleanup: Delete a subscription
--------------------------------

If you are done with a subscription you can delete it.

Method A: Python
~~~~~~~~~~~~~~~~

.. code:: python

    import pgb_utils as pgb

    subscription_name = 'ztf-loop'
    pgb.pubsub.delete_subscription(subscription_name)

For more information, view the docstring and source code for
:meth:`pgb_utils.pgb_utils.pubsub.delete_subscription`.

Method B: Command line
~~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

    subscription_name="ztf-loop"
    gcloud pubsub subscriptions delete $subscription_name
