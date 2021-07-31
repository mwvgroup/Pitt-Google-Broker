Consumer Simulator
==================

The consumer simulator is a Python module that pulls
alerts\ `\* <#notes>`__ from a Pub/Sub subscription and republishes them
to a topic. By publishing to your broker instance's ``alerts`` topic you
can bypass the consumer and feed alerts into your instance at a
controlled rate. This is the only way to control the flow of incoming
alerts and is especially useful in testing.

-  `Install <#install>`__
-  `Code Examples <#code-examples>`__
-  `Arguments and Options <#arguments-and-options>`__
-  `How Does the Consumer Simulator
   Work? <#how-does-the-consumer-simulator-work>`__

   -  `Reservoir Subscriptions <#reservoir-subscriptions>`__

See also: - `**Workflow**: Testing a Broker
Instance <test-an-instance.md>`__

--------------

Install
-------

The consumer simulator is part of the ``pgb-broker-utils`` Python
package. Install it with:

.. code:: bash

    pip install pgb-broker-utils

--------------

Code Examples
-------------

See also: `Arguments and Options <#arguments-and-options>`__

.. code:: python

    from broker_utils import consumer_sim as bcs

    survey, testid = 'ztf', 'mytest'  # replace with the keywords for your instance
    instance = (survey, testid)


    # Publish 10 alerts simultaneously, 1 time
    alert_rate = (10, 'once')
    bcs.publish_stream(alert_rate, instance)

    # Publish alerts at the average rate of an active ZTF night for 30 minutes
    alert_rate = 'ztf-active-avg'
    runtime = (30, 'min')
    bcs.publish_stream(alert_rate, instance, runtime=runtime)

    # Publish alerts at the average rate of 30 alerts/sec for 15 minutes,
    # at a publish rate of 1 batch/min
    alert_rate = (30, 'perSec')
    runtime = (15, 'min')
    publish_batch_every = (60, 'sec')
    bcs.publish_stream(alert_rate, instance, runtime=runtime, publish_batch_every=publish_batch_every)

    # Connect to the instance's own reservoir, creating a closed loop of alerts
    sub_id = f'{survey}-alerts-reservoir-{testid}'
    alert_rate = (10, 'once')
    bcs.publish_stream(alert_rate, instance, sub_id=sub_id)

    # Pull from an arbitrary subscription and publish to an arbitrary topic
    sub_id = 'your-subscription-id'  # replace with a valid subscription
    topic_id = 'your-topic-id'  # replace with a valid topic
    alert_rate = (10, 'once')
    bcs.publish_stream(alert_rate, sub_id=sub_id, topic_id=topic_id)

--------------

Arguments and Options
---------------------

-  **``alert_rate``**: ``(int, str)`` or ``str``. Required. Desired rate
   at which to publish alerts.

   -  if ``(int, str)``:

      -  ``int`` (1st arg). Number of alerts to be published per unit
         time.
      -  ``str`` (2nd arg). Rate unit. One of:

         -  ``once``
         -  ``perSec``
         -  ``perMin``
         -  ``perHr``
         -  ``perNight`` = per 10 hrs

   -  if ``str``: One of:

      -  ``ztf-active-avg`` = (300000, 'perNight'). The approximate
         average rate of an active night from ZTF.
      -  ``ztf-live-max`` = (200, 'perSec'). The approximate maximum
         incoming rate seen in the live ZTF stream.

-  **``instance``**: ``(str, str)`` = ``(survey, testid)``. Optional,
   default ``None``. Keywords of the broker instance. Used to determine
   the subscription and topic. If ``None``, both ``sub_id`` and
   ``topic_id`` must be valid names. If both ``instance`` and
   ``sub_id``/``topic_id`` are passed, ``sub_id``/``topic_id`` will
   prevail.

-  **``runtime``**: ``(int, str)``. Required unless ``alert_rate`` unit
   is ``once``. Desired length of time the simulator runs for.

   -  ``int`` (1st arg). Number of units of time the simulator runs.
   -  ``str`` (2nd arg). Run time unit. One of:

      -  ``sec``
      -  ``min``
      -  ``hr``
      -  ``night`` = 10 hrs

-  **``publish_batch_every``**: ``(int, str)``. Optional. Default
   ``(5,'sec')``. The simulator will sleep for this amount of time
   between batches.

   -  ``int`` (1st arg). Number of units of time the simulator sleeps
      for.
   -  ``str`` (2nd arg). Sleep time unit. One of:

      -  ``sec``

-  **``sub_id``**: ``str``. Optional. Name of the Pub/Sub subscription
   from which to pull alerts. If ``None``, ``instance`` must contain
   valid keywords, and then the production instance reservoir
   ``{survey}-alerts-reservoir`` will be used.

-  **``topic_id``**: ``str``. Optional. Name of the Pub/Sub topic to
   which alerts will be published. If ``None``, ``instance`` must
   contain valid keywords, and then the topic
   ``{survey}-alerts-{testid}`` will be used.

-  **``nack``**: ``bool``. Optional. Default ``False``. Whether to
   "nack" (not acknowledge) the messages. If ``True``, messages are
   published to the topic, but they are not dropped from the
   subscription and so will be delivered again at an arbitrary time in
   the future.

Note: The actual publish rate and total number of alerts published may
not be exactly as requested since alerts are published in batches with a
(1) fixed number of alerts per batch, and (2) fixed batch publish rate.
Both numbers are determined by the input arguments, but some rounding
occurs.

--------------

How Does the Consumer Simulator Work?
-------------------------------------

The consumer simulator simply pulls messages from a Pub/Sub subscription
and republishes them to a Pub/Sub topic at given rate for a given length
of time. By connecting to a `"reservoir"
subscription <#reservoir-subscriptions>`__ that contains suitable
alerts, and publishing to your instance's ``alerts`` Pub/Sub topic, you
can bypass your instance's consumer and control the flow of alerts
entering your broker.

Many options are available; see `Arguments and
Options <#arguments-and-options>`__.

The simulator publishes alerts in batches, so the input arguments get
converted to appropriate values. Therefore, the *actual* total number of
alerts published, publish rate, and length of run time may not be
exactly equal to what the user requests. Rounding occurs so that an
integer number of batches are published, each containing the same
integer number of alerts. If you want one or both to be exact, choose an
appropriate combination of variables.

Reservoir Subscriptions
~~~~~~~~~~~~~~~~~~~~~~~

Every broker instance has a Pub/Sub subscription with the name stub
``alerts-reservoir`` that is a subscription to its ``alerts`` topic.
Every alert entering the instance ends up in this reservoir where it is
held until pulled (and acknowledged) or for 7 days, whichever comes
first.

You can pull alerts from the reservoir of any instance to which you have
access. By default, the consumer simulator pulls from the `production
instance <broker-instance-keywords.md#production-vs-testing-instances>`__
of the survey associated with the topic to which it is publishing, since
it is assumed to contain the largest number of suitable alerts. You can
check the number of alerts in a reservoir ("unacked message count") by
viewing the subscription in the GCP Console (see
`here <view-resources.md#ps>`__).

If you pull from the reservoir of the same instance to which you are
publishing, you create a *closed loop*. In this way, you can access an
**infinite** source of non-unique alerts. Of course, this requires that
you have previously fed alerts into your broker instance by some other
method so that your reservoir is not empty.

Another way to access an infinite source is by "nack"-ing messages,
which tells the subscriber "n"ot to "ack"nowledge the messages, meaning
they do not get dropped from the reservoir.

--------------

\* The consumer simulator actually does not care what the contents of
the Pub/Sub messages are. It can be used to pull messages from any
subscription and publish them to any topic.
