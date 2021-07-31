Run the Broker
==============

-  `Start the Broker <#start-the-broker>`__ the easy way
-  `Stop the Broker <#stop-the-broker>`__ the easy way
-  `Start/Stop Components
   Individually <#starting-and-stopping-components-individually>`__
-  `Options for Ingesting Alerts <#options-for-ingesting-alerts>`__

   -  `Kafka Topic Syntax <#kafka-topic-syntax>`__

Use this document to run a broker instance manually (typically a Testing
instance).

See also: - `**Workflow**: Testing a Broker
Instance <test-an-instance.md>`__ -
`Auto-scheduler <../broker-design/auto-scheduler.md>`__ to schedule a
(typically Production) instance to run automatically each night. - `What
Does Night Conductor Do? <../broker-design/night-conductor.md>`__

--------------

Start the Broker
----------------

The easiest way to start the broker is to hijack the
`auto-scheduler <../broker-design/auto-scheduler.md>`__ by sending a
``START`` message to its Pub/Sub topic and attaching an attribute that
indicates the topic to be ingested (or none). In addition to cueing up
all broker components, the cue-response checker will run and log\* the
status of each component. (\*See `View and Access Resources: Cloud
Scheduler <view-resources.md#csched>`__, and note that the checks are on
a time delay of up to several minutes.)

**Prerequisite**: Make sure the VMs are stopped (see `View and Access
Resources: Compute Engine VMs <view-resources.md#ce>`__, includes a code
sample).

Command line:

.. code:: bash

    # replace with your broker instance's keywords:
    survey=ztf
    testid=mytest

    topic="${survey}-cue_night_conductor-${testid}"
    cue=START
    attr=KAFKA_TOPIC=NONE  # leave consumer VM off; e.g., when using consumer simulator
    # attr=topic_date=yyyymmdd  # start the consumer and ingest the topic with date yyyymmdd

    gcloud pubsub topics publish "$topic" --message="$cue" --attribute="$attr"

Python:

.. code:: python

    from pgb_utils import pubsub as pgbps

    # replace with your broker instance's keywords:
    survey='ztf'
    testid='mytest'

    topic = f'{survey}-cue_night_conductor-{testid}'
    cue = b'START'
    attr = {'KAFKA_TOPIC': 'NONE'}  # leave consumer VM off; e.g., when using consumer simulator
    # attr={'topic_date': 'yyyymmdd'}  # start the consumer and ingest the topic with date yyyymmdd

    pgbps.publish(topic, cue, attrs=attr)

Stop the Broker
---------------

The easiest way to stop the broker is to hijack the
`auto-scheduler <../broker-design/auto-scheduler.md>`__ by sending an
``END`` message to its Pub/Sub topic. In addition to stopping all broker
components, the cue-response checker will run and log\* the status of
each component. (\*See `View and Access Resources: Cloud
Scheduler <view-resources.md#csched>`__, and note that the checks are on
a time delay of up to several minutes.)

Command line:

.. code:: bash

    # replace with your broker instance's keywords:
    survey=ztf
    testid=mytest

    topic="${survey}-cue_night_conductor-${testid}"
    cue=END

    gcloud pubsub topics publish "$topic" --message="$cue"

Python:

.. code:: python

    from pgb_utils import pubsub as pgbps

    # replace with your broker instance's keywords:
    survey='ztf'
    testid='mytest'

    topic = f'{survey}-cue_night_conductor-{testid}'
    cue = b'END'

    pgbps.publish(topic, cue)

Start/Stop Components Individually
----------------------------------

Here are some options:

**Generally**: Use night conductor's scripts. In most cases, you can
simply call a shell script and pass in a few variables. See especially
those called by - vm\_startup.sh at the code path
broker/night\_conductor/vm\_startup.sh - start\_night.sh at the code
path broker/night\_conductor/start\_night/start\_night.sh -
end\_night.sh at the code path
broker/night\_conductor/end\_night/end\_night.sh

**Night Conductor** - Instead of hijacking the auto-scheduler, you can
start/stop the broker by controling night-conductor directly. See
`Example: Use night-conductor to start/end the
night <view-resources.md#startendnight>`__

**Cloud Functions** - update/redeploy: run the ``deploy_cloud_fncs.sh``
script, see `here <view-resources.md#cf>`__

**Dataflow** - start/update/stop jobs: see `View and Access Resources:
Dataflow jobs <view-resources.md#dataflow>`__

**VMs** - start/stop: see `View and Access Resources: Compute Engine
VMs <view-resources.md#ce>`__

--------------

Options for Ingesting Alerts
----------------------------

You have three options to get alerts into the broker. Production
instances typically use #1; **testing instances typically use #3**.

1. Connect to a **live stream**. Obviously, this can only be done at
   night when there is a live stream to connect to. If there are no
   alerts in the topic, the consumer will poll repeatedly for available
   topics and begin ingesting when its assigned topic becomes active.
   See `Kafka Topic Syntax <#kafka-topic-syntax>`__ below.

2. Connect to a **stream from a previous night** (within the last 7
   days). This is not recommended since alerts will *flood* into the
   broker as the consumer ingests as fast as it can. For ZTF, you can
   check
   `ztf.uw.edu/alerts/public/ <https://ztf.uw.edu/alerts/public/>`__;
   ``tar`` files larger than 74 (presumably in bytes) indicate dates
   with >0 alerts. See also: `Kafka Topic
   Syntax <#kafka-topic-syntax>`__.

3. Use the **consumer simulator** to *control the flow* of alerts into
   the broker. See `Consumer Simulator <consumer-simulator.md>`__ for
   details. When starting the broker, use metadata attribute
   ``KAFKA_TOPIC=NONE`` to leave the consumer VM off.

Kafka Topic Syntax
~~~~~~~~~~~~~~~~~~

Topic name syntax:

-  ZTF: ``ztf_yyyymmdd_programid1`` where ``yyyymmdd`` is replaced with
   the date.
-  DECAT: ``decat_yyyymmdd_2021A-0113`` where ``yyyymmdd`` is replaced
   with the date.

