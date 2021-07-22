# Night Conductor: Orchestrating the broker's startup and shutdown

- [What Does Night Conductor Do?](night-conductor.md)
    - [Start Night](#start-night)
    - [End Night](#end-night)
- [Where to look if there's a problem](#where-to-look-if-theres-a-problem)
- [Night Conductor's schedule](#night-conductors-schedule)


## What Does Night Conductor Do?

The night conductor VM starts and ends the night by orchestrating the startup and shutdown of the resources associated with its broker instance.
It gets the appropriate survey and testid [keywords](broker-instance-keywords.md) by parsing its own name.
Upon startup, it runs the set of scripts in the `night_conductor` directory of the instance's `broker_files` bucket, beginning with `vm_startup.sh`.

To control the behavior, we pass arguments by setting __metadata attributes__ on the VM, prior to starting it up (see below for code sample).
These attributes include:
- `NIGHT`: `START` or `END`. See below.
- `KAFKA_TOPIC`: a [valid topic](run-broker.md#kafka-topic-syntax) or `NONE`.
If `NONE`, night conductor will not start the consumer VM; use this if (e.g.,) you want to use the [consumer simulator](consumer-simulator.md).
Otherwise, night conductor will set `KAFKA_TOPIC` as a metadata attribute on the consumer VM and start it.
This attribute has no effect if `NIGHT=END`.

After completing its scripts, night conductor clears the metadata attributes (so no unexpected behavior occurs on the next startup) and shuts itself down.

Note that Cloud Functions are always "on"; night conductor does not manage them.

Example: Manually set metadata attributes and start the VM.
```bash
survey=
testid=
instancename="${survey}-night-conductor-${testid}"
zone=us-central1-a
gcloud compute instances add-metadata "$instancename" --zone="$zone" \
        --metadata NIGHT="START",KAFKA_TOPIC="NONE"
gcloud compute instances start "$instancename" --zone "$zone"
```

### Start Night

See also:
- [run-broker.md#start-the-broker](run-broker.md#start-the-broker)

If the metadata attribute `NIGHT=START`, night conductor runs the script `start_night.sh`. It does the following:

1. Starts the Dataflow jobs and waits for their status to change to "Running".
2. If the attribute `KAFKA_TOPIC` does not equal `NONE`, sets the same attribute on the consumer VM and starts it. The consumer will run its startup script, and try to connect to the topic and begin ingesting.

### End Night

See also:
- [run-broker.md#stop-the-broker](run-broker.md#stop-the-broker)

If the metadata attribute `NIGHT=END`, night conductor runs the script `end_night.sh`. It does the following:

1. Stops the consumer VM.
2. Stops the Dataflow jobs. The jobs will stop accepting new alerts and finish processing those already in the pipeline. Night conductor waits for their status to change to "Drained" or "Cancelled".
3. Resets the Pub/Sub counters. These are subscriptions that the broker uses to count the number of elements received and processed each night (see the instance [Dashboard](view-resources.md#dashboards)). They have name stubs like `<topic_name>-counter`.


## Where to look if there's a problem

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

## Night Conductor's schedule

Broker ingestion of live topics is auto-scheduled with the following process:

Cloud Scheduler cron job -> Pub/Sub message -> Cloud Function -> VM startup

The cron job sends a Pub/Sub message that simply contains either `'START'` or `'END'`. The Cloud Function receives this message, sets appropriate metadata attributes on the night conductor VM and starts it. When the cue is `'START'`, the Cloud Function sets the `KAFKA_TOPIC` attribute to the topic for the __current date, UTC__.

Two cron jobs are scheduled, one each to start and end the night. Both processes use the same Pub/Sub topic and Cloud Function.

Example: Change the time the broker starts each night.
```bash
survey=
testid=
jobname="${survey}-cue_night_conductor_START-${testid}"
schedule='0 2 * * *'  # UTC. unix-cron format
# https://cloud.google.com/scheduler/docs/configuring/cron-job-schedules

gcloud scheduler jobs update pubsub $jobname --schedule "${schedule}"
```

Example: Pause/resume the broker's auto-schedule.
```bash
survey=
testid=
startjob="${survey}-cue_night_conductor_START-${testid}"
endjob="${survey}-cue_night_conductor_END-${testid}"

# pause the jobs
gcloud scheduler jobs pause $startjob
gcloud scheduler jobs pause $endjob

# resume the jobs
gcloud scheduler jobs resume $startjob
gcloud scheduler jobs resume $endjob
```

By default, the cron jobs of a Testing instance are paused immediately after creation so that the instance does not run automatically.
