# Night Conductor

- [What Does Night Conductor Do?](night-conductor.md)
    - [Start Night](#start-night)
    - [End Night](#end-night)
- [Where to look if there's a problem](#where-to-look-if-theres-a-problem)

See also
- [Auto-scheduler](auto-scheduler.md)
- [__Workflow__: Testing a Broker Instance](../run-a-broker-instance/test-an-instance.md)


## What Does Night Conductor Do?

The night conductor VM starts and ends the night by orchestrating the startup and shutdown of the resources associated with its broker instance.
It gets the appropriate survey and testid [keywords](broker-instance-keywords.md) by parsing its own name.
Upon startup, it runs the set of scripts in the `night_conductor` directory of the instance's `broker_files` bucket, beginning with `vm_startup.sh`.

To control the behavior, we pass arguments by setting __metadata attributes__ on the VM, prior to starting it up (see below for code sample).
These attributes include:
- `NIGHT`: `START` or `END`. See below.
- `KAFKA_TOPIC`: a [valid topic](../run-a-broker-instance/run-broker.md#kafka-topic-syntax) or `NONE`.
If `NONE`, night conductor will not start the consumer VM; use this if (e.g.,) you want to use the [consumer simulator](../run-a-broker-instance/consumer-simulator.md).
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
- [Start the Broker](run-broker.md#start-the-broker)

If the metadata attribute `NIGHT=START`, night conductor runs the script `start_night.sh`. It does the following:

1. Starts the Dataflow jobs and waits for their status to change to "Running".
2. If the attribute `KAFKA_TOPIC` does not equal `NONE`, sets the same attribute on the consumer VM and starts it. The consumer will run its startup script, and try to connect to the topic and begin ingesting.

### End Night

See also:
- [Stop the Broker](run-broker.md#stop-the-broker)

If the metadata attribute `NIGHT=END`, night conductor runs the script `end_night.sh`. It does the following:

1. Stops the consumer VM.
2. Stops the Dataflow jobs. The jobs will stop accepting new alerts and finish processing those already in the pipeline. Night conductor waits for their status to change to "Drained" or "Cancelled".
3. Resets the Pub/Sub counters. These are subscriptions that the broker uses to count the number of elements received and processed each night (see the instance [Dashboard](view-resources.md#dashboards)). They have name stubs like `<topic_name>-counter`.


## Where to look if there's a problem

See [View and Access Resources](../run-a-broker-instance/view-resources.md) for details like where to view logs, how to ssh into a VM, and where to view Dataflow jobs on the GCP Console.

__Auto-scheduler's Logs__

All broker instances share the following logs, which are a good starting point:
- [check-cue-response-cloudfnc](https://cloudlogging.app.goo.gl/525hswivBiZfZQEUA)
- [cue-night-conductor-cloudfnc](https://cloudlogging.app.goo.gl/7Uz92PiZLFF5zfNd8)

(If you started/stopped the broker manually by sending a Pub/Sub message to the auto-scheduler's topic you have hijacked its process...
this is a good thing since it means the cue-response checks are run and logs are reported to the links above.)

__Night Conductor's Logs__

Compare night conductor's logs with the scripts it runs. You probably want to start with:
- vm_startup.sh at the code path broker/night_conductor/vm_startup.sh
- start_night.sh at the code path broker/night_conductor/start_night/start_night.sh
- end_night.sh at the code path broker/night_conductor/end_night/end_night.sh

Remember that the actual scripts used by night conductor are stored in its `broker_files` bucket. Fresh copies are downloaded to the VM prior to execution.

You can also look at the logs from other resources.

__Dataflow jobs__

You can see many details of the Dataflow job on the GCP Console (see link above).

If there was a problem with the job's start up, look at the terminal output from the call to start the job. It is written to a file called `runjob.out` in that job's directory on the night conductor VM. So for example, look for `/home/broker/beam/value_added/runjob.out`.
