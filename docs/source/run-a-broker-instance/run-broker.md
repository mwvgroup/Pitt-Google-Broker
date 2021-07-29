# Run the Broker

- [Start the Broker](#start-the-broker) the easy way
- [Stop the Broker](#stop-the-broker) the easy way
- [Start/Stop Components Individually](#starting-and-stopping-components-individually)
- [Options for Ingesting Alerts](#options-for-ingesting-alerts)
    - [Kafka Topic Syntax](#kafka-topic-syntax)

Use this document to run a broker instance manually (typically a Testing instance).

See also:
- [__Workflow__: Testing a Broker Instance](test-an-instance.md)
- [Auto-scheduler](../broker-design/auto-scheduler.md) to schedule a (typically Production) instance to run automatically each night.
- [What Does Night Conductor Do?](../broker-design/night-conductor.md)

---

## Start the Broker

The easiest way to start the broker is to hijack the [auto-scheduler](../broker-design/auto-scheduler.md) by sending a `START` message to its Pub/Sub topic and attaching an attribute that indicates the topic to be ingested (or none). In addition to cueing up all broker components, the cue-response checker will run and log* the status of each component. (*See [View and Access Resources: Cloud Scheduler](view-resources.md#csched), and note that the checks are on a time delay of up to several minutes.)

__Prerequisite__: Make sure the VMs are stopped (see [View and Access Resources: Compute Engine VMs](view-resources.md#ce), includes a code sample).

Command line:
```bash
# replace with your broker instance's keywords:
survey=ztf
testid=mytest

topic="${survey}-cue_night_conductor-${testid}"
cue=START
attr=KAFKA_TOPIC=NONE  # leave consumer VM off; e.g., when using consumer simulator
# attr=topic_date=yyyymmdd  # start the consumer and ingest the topic with date yyyymmdd

gcloud pubsub topics publish "$topic" --message="$cue" --attribute="$attr"
```

Python:
```python
from pgb_utils import pubsub as pgbps

# replace with your broker instance's keywords:
survey='ztf'
testid='mytest'

topic = f'{survey}-cue_night_conductor-{testid}'
cue = b'START'
attr = {'KAFKA_TOPIC': 'NONE'}  # leave consumer VM off; e.g., when using consumer simulator
# attr={'topic_date': 'yyyymmdd'}  # start the consumer and ingest the topic with date yyyymmdd

pgbps.publish(topic, cue, attrs=attr)
```

## Stop the Broker

The easiest way to stop the broker is to hijack the [auto-scheduler](../broker-design/auto-scheduler.md) by sending an `END` message to its Pub/Sub topic. In addition to stopping all broker components, the cue-response checker will run and log* the status of each component. (*See [View and Access Resources: Cloud Scheduler](view-resources.md#csched), and note that the checks are on a time delay of up to several minutes.)

Command line:
```bash
# replace with your broker instance's keywords:
survey=ztf
testid=mytest

topic="${survey}-cue_night_conductor-${testid}"
cue=END

gcloud pubsub topics publish "$topic" --message="$cue"
```

Python:
```python
from pgb_utils import pubsub as pgbps

# replace with your broker instance's keywords:
survey='ztf'
testid='mytest'

topic = f'{survey}-cue_night_conductor-{testid}'
cue = b'END'

pgbps.publish(topic, cue)
```


## Start/Stop Components Individually

Here are some options:

__Generally__: Use night conductor's scripts. In most cases, you can simply call a shell script and pass in a few variables. See especially those called by
- vm_startup.sh at the code path broker/night_conductor/vm_startup.sh
    - start_night.sh at the code path broker/night_conductor/start_night/start_night.sh
    - end_night.sh at the code path broker/night_conductor/end_night/end_night.sh

__Night Conductor__ - Instead of hijacking the auto-scheduler, you can start/stop the broker by controling night-conductor directly.
See [Example: Use night-conductor to start/end the night](view-resources.md#startendnight)

__Cloud Functions__ - update/redeploy: run the `deploy_cloud_fncs.sh` script, see [here](view-resources.md#cf)

__Dataflow__ - start/update/stop jobs: see [View and Access Resources: Dataflow jobs](view-resources.md#dataflow)

__VMs__ - start/stop: see [View and Access Resources: Compute Engine VMs](view-resources.md#ce)

---

## Options for Ingesting Alerts

You have three options to get alerts into the broker.
Production instances typically use #1; __testing instances typically use #3__.

1. Connect to a __live stream__. Obviously, this can only be done at night when there is a live stream to connect to. If there are no alerts in the topic, the consumer will poll repeatedly for available topics and begin ingesting when its assigned topic becomes active. See [Kafka Topic Syntax](#kafka-topic-syntax) below.

2. Connect to a __stream from a previous night__ (within the last 7 days). This is not recommended since alerts will *flood* into the broker as the consumer ingests as fast as it can. For ZTF, you can check [ztf.uw.edu/alerts/public/](https://ztf.uw.edu/alerts/public/); `tar` files larger than 74 (presumably in bytes) indicate dates with >0 alerts. See also: [Kafka Topic Syntax](#kafka-topic-syntax).

3. Use the __consumer simulator__ to *control the flow* of alerts into the broker. See [Consumer Simulator](consumer-simulator.md) for details. When starting the broker, use metadata attribute `KAFKA_TOPIC=NONE` to leave the consumer VM off.

### Kafka Topic Syntax

Topic name syntax:

- ZTF: `ztf_yyyymmdd_programid1` where `yyyymmdd` is replaced with the date.
- DECAT: `decat_yyyymmdd_2021A-0113` where `yyyymmdd` is replaced with the date.
