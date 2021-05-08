# Run the Broker

- [Prerequisites](#prerequisites)
- [Run the Broker](#run-the-broker)
    - [Start the Broker](#start-the-broker)
    - [Stop the Broker](#stop-the-broker)
    - [Starting and Stopping Components Individually](#starting-and-stopping-components-individually)
- [Options for Ingesting Alerts](#options-for-ingesting-alerts)
    - [Kafka Topic Syntax](#kafka-topic-syntax)
- [What Does Night Conductor Do?](#what-does-night-conductor-do)
    - [Start Night](#start-night)
    - [End Night](#end-night)
    - [Where to look if there's a problem](#where-to-look-if-theres-a-problem)

---

## Prerequisites

Complete [Setup a Broker Instance](setup-broker.md), and take note of the associated survey and testid keywords.

Make sure the VMs are stopped.
See [Shutdown the VMs](setup-broker.md#shutdown-the-vms) in Setup a Broker Instance.

---

## Run the Broker

### Start the Broker

See also:
- [Options for Ingesting Alerts](#options-for-ingesting-alerts)
- [What Does Night Conductor Do?](#what-does-night-conductor-do)

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
- [What Does Night Conductor Do?](#what-does-night-conductor-do)

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

Generally: Use night conductor's scripts. In most cases, you can simply call a shell script and pass in a few variables. See especially those called by [vm_startup.sh](../../../broker/night_conductor/vm_startup.sh):
- [start_night.sh](../../../broker/night_conductor/start_night/start_night.sh)
- [end_night.sh](../../../broker/night_conductor/end_night/end_night.sh)

Dataflow:
- start/update jobs: see [beam/README.md](../../../broker/beam/README.md).
- stop jobs: see [shutdown-broker.md](shutdown-broker.md)

VMs - start/stop: see [View and Access Resources](view-resources.md)

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

---

## What Does Night Conductor Do?

The night conductor VM starts and stops the resources associated with its broker instance.
It gets the appropriate survey and testid [keywords](broker-instance-keywords.md) by parsing its own name.
Upon startup, it runs the set of scripts in the `night_conductor` directory of the instance's `broker_files` bucket, beginning with `vm_startup.sh`.

To control the behavior, we pass arguments by setting __metadata attributes__ on the VM, prior to starting it up.
These attributes include:
- `NIGHT`: `START` or `END`. See the following sections for details.
- `KAFKA_TOPIC`: a [valid topic](#kafka-topic-syntax) or `NONE`.
If `NONE`, night conductor will not start the consumer VM; use this if (e.g.,) you want to use the [consumer simulator](consumer-simulator.md).
Otherwise, night conductor will set `KAFKA_TOPIC` as a metadata attribute on the consumer VM and start it.
This attribute has no effect if `NIGHT=END`.

After completing its scripts, night conductor clears the metadata attributes (so no unexpected behavior occurs on the next startup) and shuts itself down.

Note that Cloud Functions are always "on"; night conductor does not manage them.

### Start Night

If the metadata attribute `NIGHT=START`, night conductor runs the script `start_night.sh`. It does the following:

1. Starts the Dataflow jobs and waits for their status to change to "Running".
2. If the attribute `KAFKA_TOPIC` does not equal `NONE`, sets the same attribute on the consumer VM and starts it. The consumer will run its startup script, and try to connect to the topic and begin ingesting.

### End Night

If the metadata attribute `NIGHT=END`, night conductor runs the script `end_night.sh`. It does the following:

1. Stops the consumer VM.
2. Stops the Dataflow jobs. The jobs will stop accepting new alerts and finish processing those already in the pipeline. Night conductor waits for their status to change to "Drained" or "Cancelled".
3. Resets the Pub/Sub counters. These are subscriptions that the broker uses to count the number of elements received and processed each night (see the instance [Dashboard](view-resources.md#dashboards)). They have name stubs like `<topic_name>-counter`.


### Where to look if there's a problem

See [View and Access Resources](view-resources.md) for details like where to view logs, how to ssh into a VM, and where to view Dataflow jobs on the GCP Console.

__Logs__

Compare night conductor's logs with the scripts it runs. You probably want to start with:
- [`vm_startup.sh`](broker/night_conductor/vm_startup.sh),
- [`start_night.sh`](broker/night_conductor/start_night/start_night.sh)
- [`end_night.sh`](broker/night_conductor/end_night/end_night.sh)

Remember that the actual scripts used by night conductor are stored in its `broker_files` bucket. Fresh copies are downloaded to the VM prior to execution.

You can also look at the logs from other resources.

__Dataflow jobs__

You can see many details of the Dataflow job on the GCP Console (see link above).

If there was a problem with the job's start up, look at the terminal output from the call to start the job. It is written to a file called `runjob.out` in that job's directory on the night conductor VM. So for example, look for `/home/broker/beam/value_added/runjob.out`.
