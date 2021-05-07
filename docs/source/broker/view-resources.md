# View and Access Resources

- [Dashboards](#dashboards)
- [BigQuery](#bq)
- [Cloud Functions](#cf)
- [Cloud Storage Buckets](#cs)
- [Compute Engine VMs](#ce)
- [Dataflow jobs](#dataflow)
- [Pub/Sub topics and subscriptions](#ps)

---

A broker instance has many resources associated with it.
See also:
- [Broker Instance Keywords](broker-instance-keywords.md) to understand some naming conventions
- [Broker Overview](broker-overview.md) to view the name stubs

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
- Query the database instructions: [Pitt-Google-Tutorial.ipynb](../pgb_utils/tutorials/Pitt-Google-Tutorial.ipynb)
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
- [Create and deploy a Cloud Function using the `gcloud` command-line tool](https://cloud.google.com/functions/docs/quickstart)
- [`../broker/setup_broker/deploy_cloud_fncs.sh`](../broker/setup_broker/deploy_cloud_fncs.sh). You can re-run this script to update the broker's Cloud Function(s).

---

<a name="cs"></a>
[__Cloud Storage Buckets__](https://console.cloud.google.com/storage/browser?project=ardent-cycling-243415)

Click on the name of a bucket to view files and options.

See also:
- API docs:
    - [Python Client for Google Cloud Storage](https://googleapis.dev/python/storage/latest/index.html)
    - [Command-line tool `gsutil`](https://cloud.google.com/storage/docs/quickstart-gsutil)  
- Upload and download files: `broker_utils.gcp_utils` (Python)
- Tutorial: [Pitt-Google-Tutorial.ipynb](../pgb_utils/tutorials/Pitt-Google-Tutorial.ipynb)
    - using the Google Cloud SDK (Python and command line)

---

<a name="ce"></a>
[__Compute Engine VMs__](https://console.cloud.google.com/compute/instances?project=ardent-cycling-243415&instancessize=50)

Click on the name of one of your VMs (`night-conductor-{testid}` or `ztf-consumer-{testid}`). From here you can:
- _start/stop_ the instance
- access the _logs_
- view and edit the _metadata attributes_
- view and edit _other configs_
- click a button to `ssh` into the instance
- view performance stats and live* _monitoring charts_

Here are some useful shell commands:
```bash
vm_name=  # fill this in
zone=us-central1-a

# start it
gcloud compute instances start --zone="$zone" "$vm_name"
# stop it
gcloud compute instances stop --zone="$zone" "$vm_name"

# set metadata attributes
ATTRIBUTE1=value1
ATTRIBUTE2=value2
gcloud compute instances add-metadata --zone="$zone" "$vm_name" \
      --metadata "ATTRIBUTE1=${ATTRIBUTE1},ATTRIBUTE2=${ATTRIBUTE2}"
# unset attributes
gcloud compute instances add-metadata --zone="$zone" "$vm_name" \
      --metadata "ATTRIBUTE1=,ATTRIBUTE2="

# set startup script
# we'll do a specific example for night-conductor
survey=ztf
testid=mytestid
nconductVM="${survey}-night-conductor-${testid}"
broker_bucket="${GOOGLE_CLOUD_PROJECT}-${survey}-broker_files-${testid}"
startupscript="gs://${broker_bucket}/night_conductor/vm_startup.sh"
gcloud compute instances add-metadata "$nconductVM" --zone "$zone" \
        --metadata startup-script-url="$startupscript"
# unset startup script
gcloud compute instances add-metadata "$nconductVM" --zone "$zone" \
        --metadata startup-script-url=""

# ssh in
gcloud compute ssh --zone="$zone" "$vm_name"
```

---

<a name="dataflow"></a>
[__Dataflow jobs__](https://console.cloud.google.com/dataflow/jobs)

Click on a job name. From here you can:
- start/[stop](shutdown-broker.md#dataflow-jobs) the job
- view details about the job
- view and interact with the _graph that represents the pipeline_ PCollections and Transforms. Click on a node to view details about that step, including live _throughput charts_.
- view a page of live* _monitoring charts_ (click "JOB METRICS" tab at the top)
- access the _logs_. Click "LOGS" at the top, you will see tabs for "JOB LOGS", "WORKER LOGS", and "DIAGNOSTICS". Note that if you select a step in the graph you will only see logs related to that step (unselect the step to view logs for the full job). It's easiest to view the logs if you open them in the Logs Viewer by clicking the icon.

To start or update a job from the command line, see [../broker/beam/README.md](../broker/beam/README.md)

---

<a name="ps"></a>
[__Pub/Sub topics__](https://console.cloud.google.com/cloudpubsub/topic/list?project=ardent-cycling-243415) and [__Pub/Sub subscriptions__](https://console.cloud.google.com/cloudpubsub/subscription/list?project=ardent-cycling-243415)

Click on a topic/subscription. From here you can:
- view and edit topic/subscription details
- view live* _monitoring charts_

---

\* Live monitoring charts have some lag time.
