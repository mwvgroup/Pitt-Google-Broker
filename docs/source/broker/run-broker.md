# Run the Broker

- [Prerequisites](#prerequisites)
- [Run the Broker](#run-the-broker)
    - [Start the Broker](#start-the-broker)
    - [Stop the Broker](#stop-the-broker)
    - [Starting and Stopping Components Individually](#starting-and-stopping-components-individually)
- [Options for Ingesting Alerts](#options-for-ingesting-alerts)
    - [Kafka Topic Syntax](#kafka-topic-syntax)

---

## Prerequisites

Complete [Setup a Broker Instance](setup-broker.md), and take note of the associated survey and testid keywords.

Make sure the VMs are stopped.
See [Shutdown the VMs](setup-broker.md#shutdown-the-vms) in Setup a Broker Instance.

---

## Run the Broker

See the following sections to run components manually and test the broker (mostly used for Testing instances).

See [Auto-schedule](auto-schedule.md) for information about running the broker on an auto-schedule to ingest live alert streams (mostly used for Production instances).

### Start the Broker

See also:
- [Options for Ingesting Alerts](#options-for-ingesting-alerts)
- [Consumer Simulator](consumer-simulator.md)
- [What Does Night Conductor Do?](night-conductor.md)

```bash
survey=ztf  # use the same survey used in broker setup
testid=mytest  # use the same testid used in broker setup

NIGHT=START
KAFKA_TOPIC=ztf_20210120_programid1  # replace with a current topic to ingest
# KAFKA_TOPIC=NONE  # leave consumer VM off; e.g., when using consumer simulator

# set metadata attributes and start night-conductor
instancename="${survey}-night-conductor-${testid}"
zone=us-central1-a
gcloud compute instances add-metadata "$instancename" --zone="$zone" \
        --metadata NIGHT="$NIGHT",KAFKA_TOPIC="$KAFKA_TOPIC"
gcloud compute instances start "$instancename" --zone "$zone"
# this triggers night conductor's startup script `vm_startup.sh`.
```

### Stop the Broker

See also:
- [What Does Night Conductor Do?](night-conductor.md)

```bash
survey=ztf  # use the same survey used in broker setup
testid=mytest  # use the same testid used in broker setup

NIGHT=END

# set metadata attributes and start night-conductor
instancename="${survey}-night-conductor-${testid}"
zone=us-central1-a
gcloud compute instances add-metadata "$instancename" --zone="$zone" \
      --metadata NIGHT="$NIGHT"
gcloud compute instances start "$instancename" --zone "$zone"
# this triggers night conductor's startup script `vm_startup.sh`.
```

### Starting and Stopping Components Individually

Here are some options:

__Generally__: Use night conductor's scripts. In most cases, you can simply call a shell script and pass in a few variables. See especially those called by [vm_startup.sh](../../../broker/night_conductor/vm_startup.sh):
- [start_night.sh](../../../broker/night_conductor/start_night/start_night.sh)
- [end_night.sh](../../../broker/night_conductor/end_night/end_night.sh)

__Cloud Functions__ - update/redeploy: run the `deploy_cloud_fncs.sh` script, see [here](view-resources.md#cf)

__Dataflow__:
- start/update jobs: see [beam/README.md](../../../broker/beam/README.md).
- stop jobs: see [shutdown-broker.md](shutdown-broker.md)

__VMs__ - start/stop: see [View and Access Resources](view-resources.md)

---

## Options for Ingesting Alerts

You have three options to get alerts into the broker.
Production instances typically use #1; testing instances typically use #3.

1. Connect to a __live stream__. Obviously, this can only be done at night when there is a live stream to connect to. If there are no alerts in the topic, the consumer will poll repeatedly for available topics and begin ingesting when its assigned topic becomes active. See [Kafka Topic Syntax](#kafka-topic-syntax) below.

2. Connect to a __stream from a previous night__ (within the last 7 days). This is not recommended since alerts will *flood* into the broker as the consumer ingests as fast as it can. For ZTF, you can check [ztf.uw.edu/alerts/public/](https://ztf.uw.edu/alerts/public/); `tar` files larger than 74 (presumably in bytes) indicate dates with >0 alerts. See also: [Kafka Topic Syntax](#kafka-topic-syntax).

3. Use the __consumer simulator__ to *control the flow* of alerts into the broker. See [Consumer Simulator](consumer-simulator.md) for details. When starting the broker, use metadata attribute `KAFKA_TOPIC=NONE` to leave the consumer VM off.

### Kafka Topic Syntax

Topic name syntax:

- ZTF: `ztf_yyyymmdd_programid1` where `yyyymmdd` is replaced with the date.
- DECAT: `decat_yyyymmdd_2021A-0113` where `yyyymmdd` is replaced with the date.
