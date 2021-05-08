# Shutdown the Broker

Shutting down the broker means stopping the VMs, which includes `night-conductor`, `consumer`, and VMs used by Dataflow jobs.
It saves energy and money.
Testing brokers should be shut down when not being actively used (if you are done with the instance permanently, [delete it](delete-broker.md)).
Production brokers should be shut down during the day.

## Use Night Conductor

If you started the broker using the night conductor VM, you can also use it to shut it down. See [Stop the Broker](run-broker.md#stop-the-broker).


## Stopping Broker Components Individually

Generally, see the equivalent section in [Run the Broker](run-broker.md#starting-and-stopping-components-individually).

### Dataflow Jobs

To stop/drain/cancel a Dataflow job from the commandline, you would need to look up the job ID assigned by Dataflow at runtime. If the night conductor VM started the job, the job ID has been set as a metadata attribute ([how to view it](view-resources.md#ce)).

It's usually easiest to stop the job manually from the [Console](https://console.cloud.google.com/dataflow/jobs)
- Select your job, then select "Stop"
- You will be given the option to "Drain" or "Cancel"
    - Drain: stop ingesting alerts, but finish processing the alerts that are already in the pipeline.
    - Cancel: stop the job immediately. Ingestion stops and alerts currently in the pipeline are dropped.
