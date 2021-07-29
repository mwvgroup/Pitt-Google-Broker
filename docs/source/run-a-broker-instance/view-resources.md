# View and Access Resources

- [Dashboards](#dashboards)
- [BigQuery](#bq)
- [Cloud Functions](#cf)
- [Cloud Scheduler](#csched)
- [Cloud Storage Buckets](#cs)
- [Compute Engine VMs](#ce)
- [Dataflow jobs](#dataflow)
- [Logs Explorer](#le)
- [Pub/Sub topics and subscriptions](#ps)

---

A broker instance has many resources associated with it.
See also:
- [Broker Instance Keywords](../broker-design/broker-instance-keywords.md) to understand some naming conventions
- [Broker Overview](../broker-design/broker-overview.md) to view the name stubs

The following sections contain links to the GCP Console where you can view resources, plus descriptions of what you can view/do there, and some useful shell and Python commands.
(Dashboards first, then alphabetical.)

---

<a name="dashboards"></a>
[__Dashboards__](https://console.cloud.google.com/monitoring/dashboards)

Go directly to the dashboard for a specific broker instance by replacing "\<survey\>" and "\<testid\>" with appropriate values in the following url:
- `https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-<survey>-<testid>`

This has charts related to:
- VM network and CPU usage
- Pub/Sub streams: rates and nightly cumulative totals
- Dataflow jobs: lag metrics and number of vCPUs in use

---

<a name="bq"></a>
[__BigQuery__](https://console.cloud.google.com/bigquery?project=ardent-cycling-243415)

Expand the list under your project name, then expand a dataset, then click on a table name to view details and options.

See also:
- API docs:
    - [Python Client for Google BigQuery](https://googleapis.dev/python/bigquery/latest/index.html)
    - [Command-line tool `bq`](https://cloud.google.com/bigquery/docs/reference/bq-cli-reference)  
- Load a row into a table: `broker_utils.gcp_utils` (Python)
- Query the database instructions in the Pitt-Google-Tutorial.ipynb at pgb_utils/tutorials/Pitt-Google-Tutorial.ipynb
    - using `pgb-utils` (Python; see source code for the Google Cloud SDK commands)
    - using the Google Cloud command-line tool `bq`

---

<a name="cf"></a>
[__Cloud Functions__](https://console.cloud.google.com/functions/list?project=ardent-cycling-243415)

Click on a function name. From here you can:
- view live* _monitoring charts_
- view and edit job details
- view the source code
- view the logs
- test the function

See also:
- The script at broker/setup_broker/deploy_cloud_fncs.sh. You can re-run this script to update the broker's Cloud Function(s).
- [Create and deploy a Cloud Function using the `gcloud` command-line tool](https://cloud.google.com/functions/docs/quickstart)

---

<a name="csched"></a>
[__Cloud Scheduler__](https://console.cloud.google.com/cloudscheduler?project=ardent-cycling-243415)

From here you can
- view job details and logs
- create, edit, pause/resume, and delete jobs

See also: The __auto-schedulers__ of all broker instances share the following logs:
- [`check-cue-response-cloudfnc`](https://cloudlogging.app.goo.gl/525hswivBiZfZQEUA)
- [`cue-night-conductor-cloudfnc`](https://cloudlogging.app.goo.gl/7Uz92PiZLFF5zfNd8)


---

<a name="cs"></a>
[__Cloud Storage Buckets__](https://console.cloud.google.com/storage/browser?project=ardent-cycling-243415)

Click on the name of a bucket to view files and options.

See also:
- API docs:
    - [Python Client for Google Cloud Storage](https://googleapis.dev/python/storage/latest/index.html)
    - [Command-line tool `gsutil`](https://cloud.google.com/storage/docs/quickstart-gsutil)  
- Upload and download files: `broker_utils.gcp_utils` (Python)
- Tutorial: pgb_utils/tutorials/Pitt-Google-Tutorial.ipynb
    - using the Google Cloud SDK (Python and command line)

---

<a name="ce"></a>
[__Compute Engine VMs__](https://console.cloud.google.com/compute/instances?project=ardent-cycling-243415&instancessize=50)

Click on the name of one of your VMs (`{survey}-night-conductor-{testid}` or `{survey}-consumer-{testid}`). From here you can:
- _start/stop_ the instance
- access the _logs_
- view and edit the _metadata attributes_
- view and edit _other configs_
- click a button to `ssh` into the instance
- view performance stats and live* _monitoring charts_

Here are some useful shell commands:

General access:
```bash
vm_name=  # fill this in
zone=us-central1-a

# start it
gcloud compute instances start --zone="$zone" "$vm_name"
# stop it
gcloud compute instances stop --zone="$zone" "$vm_name"
# ssh in
gcloud compute ssh --zone="$zone" "$vm_name"

# set metadata attributes
ATTRIBUTE1=value1
ATTRIBUTE2=value2
gcloud compute instances add-metadata --zone="$zone" "$vm_name" \
      --metadata "ATTRIBUTE1=${ATTRIBUTE1},ATTRIBUTE2=${ATTRIBUTE2}"
# unset attributes
gcloud compute instances add-metadata --zone="$zone" "$vm_name" \
      --metadata "ATTRIBUTE1=,ATTRIBUTE2="
```

<a name="#startendnight"></a>
Example: Use night-conductor to start/end the night (see also [auto-scheduler](../broker-design/auto-scheduler.md))
```bash
survey=ztf
testid=mytest

#--- Start the broker
NIGHT=START
KAFKA_TOPIC=NONE  # leave consumer VM off; e.g., when using consumer simulator
# KAFKA_TOPIC=ztf_yyyymmdd_programid1  # replace with a current topic to ingest
# set metadata attributes and start night-conductor
instancename="${survey}-night-conductor-${testid}"
zone=us-central1-a
gcloud compute instances add-metadata "$instancename" --zone="$zone" \
        --metadata NIGHT="$NIGHT",KAFKA_TOPIC="$KAFKA_TOPIC"
gcloud compute instances start "$instancename" --zone "$zone"
# this triggers night conductor's startup script

#--- Stop the broker
NIGHT=END
# set metadata attributes and start night-conductor
instancename="${survey}-night-conductor-${testid}"
zone=us-central1-a
gcloud compute instances add-metadata "$instancename" --zone="$zone" \
      --metadata NIGHT="$NIGHT"
gcloud compute instances start "$instancename" --zone "$zone"
# this triggers night conductor's startup script
```

Example: Set night-conductor's startup script
```bash
survey=ztf
testid=mytestid
nconductVM="${survey}-night-conductor-${testid}"
broker_bucket="${GOOGLE_CLOUD_PROJECT}-${survey}-broker_files-${testid}"
startupscript="gs://${broker_bucket}/night_conductor/vm_startup.sh"
# set the startup script
gcloud compute instances add-metadata "$nconductVM" --zone "$zone" \
        --metadata startup-script-url="$startupscript"
# unset the startup script
gcloud compute instances add-metadata "$nconductVM" --zone "$zone" \
        --metadata startup-script-url=""
```

---

<a name="dataflow"></a>
[__Dataflow jobs__](https://console.cloud.google.com/dataflow/jobs)

Click on a job name. From here you can:
- view details about the job
- _stop/cancel/drain_ the job
- view and interact with the _graph that represents the pipeline_ PCollections and Transforms. Click on a node to view details about that step, including live _throughput charts_.
- view a page of live* _monitoring charts_ (click "JOB METRICS" tab at the top)
- access the _logs_. Click "LOGS" at the top, you will see tabs for "JOB LOGS", "WORKER LOGS", and "DIAGNOSTICS". Note that if you select a step in the graph you will only see logs related to that step (unselect the step to view logs for the full job). It's easiest to view the logs if you open them in the Logs Viewer by clicking the icon.

Command-line access:
- To start or update a job from the command line, see the README at broker/beam/README.md
- Job IDs: To update or stop a Dataflow job from the command line, you would need to look up the job ID assigned by Dataflow at runtime. If the night conductor VM started the job, the job ID has been set as a metadata attribute ([how to view it](view-resources.md#ce)).

---

<a name="le"></a>
[__Logs Explorer__](https://console.cloud.google.com/logs)

View/query all (most?) logs for the project.

---

<a name="ps"></a>
[__Pub/Sub topics__](https://console.cloud.google.com/cloudpubsub/topic/list?project=ardent-cycling-243415) and [__Pub/Sub subscriptions__](https://console.cloud.google.com/cloudpubsub/subscription/list?project=ardent-cycling-243415)

Click on a topic/subscription. From here you can:
- view and edit topic/subscription details
- view live* _monitoring charts_

---

\* Live monitoring charts have some lag time.
