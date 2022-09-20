View and Access Resources
=========================

-  `Dashboards`_
-  `BigQuery`_
-  `Cloud Functions`_
-  `Cloud Scheduler`_
-  `Cloud Storage buckets`_
-  `Compute Engine VMs`_
-  `Dataflow jobs`_
-  `Logs Explorer`_
-  `Pub/Sub topics and subscriptions`_

--------------

A broker instance has many resources associated with it. See also:

- :doc:`../broker-instance-keywords` to understand
  some naming conventions
- :doc:`../broker-overview` to view the name stubs

The following sections contain links to the GCP Console where you can
view resources, plus descriptions of what you can view/do there, and
some useful shell and Python commands. (Dashboards first, then
alphabetical.)

--------------


Dashboards
-----------

`GCP Console <https://console.cloud.google.com/monitoring/dashboards>`__

Go directly to the dashboard for a specific broker instance by replacing
"<survey>" and "<testid>" with appropriate values in the following url:

``https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-<survey>-<testid>``

This has charts related to:

- VM network and CPU usage
- Pub/Sub streams: rates and nightly cumulative totals
- Dataflow jobs: lag metrics and number of vCPUs in use

--------------

BigQuery
-----------

`GCP Console <https://console.cloud.google.com/bigquery>`__

Expand the list under your project name, then expand a dataset, then
click on a table name to view details and options.

See also:

- API docs:

    - `Python Client for Google BigQuery
      <https://googleapis.dev/python/bigquery/latest/index.html>`__
    - `Command-line tool bq
      <https://cloud.google.com/bigquery/docs/reference/bq-cli-reference>`__

- Load a row into a table: use ``broker_utils.gcp_utils.insert_rows_bigquery`` (Python)
- Query the database instructions in the tutorial
  :doc:`../../access-data/bigquery` (Python and command line)

--------------

Cloud Functions
----------------

`GCP Console <https://console.cloud.google.com/functions/list>`__

Click on a function name. From here you can:

- view live\* *monitoring charts*
- view and edit job details
- view the source code
- view the logs
- test the function

See also:

- The script at broker/setup\_broker/deploy\_cloud\_fncs.sh.
  You can re-run this script to update the broker's Cloud Function(s).
- `Create and deploy a Cloud Function using the gcloud command-line
  tool <https://cloud.google.com/functions/docs/quickstart>`__

--------------

Cloud Scheduler
-----------------

`GCP Console <https://console.cloud.google.com/cloudscheduler>`__

From here you can - view job details and logs - create, edit,
pause/resume, and delete jobs

--------------

Cloud Storage buckets
------------------------

`GCP Console <https://console.cloud.google.com/storage/browser>`__

Click on the name of a bucket to view files and options.

See also:

- API docs:

    - `Python Client for Google Cloud Storage
      <https://googleapis.dev/python/storage/latest/index.html>`__
    - `Command-line tool gsutil
      <https://cloud.google.com/storage/docs/quickstart-gsutil>`__

- Upload and download files: use ``broker_utils.gcp_utils.cs_download_file``
  and ``broker_utils.gcp_utils.cs_upload_file`` (Python)
- Tutorial :doc:`../../access-data/cloud-storage`
  (Python and command line)

--------------

Compute Engine VMs
-------------------

`GCP Console <https://console.cloud.google.com/compute/instances>`__

Click on the name of one of your VMs
({survey}-night-conductor-{testid} or
{survey}-consumer-{testid}). From here you can:

- *start/stop* the instance
- access the *logs*
- view and edit the *metadata attributes*
- view and edit *other configs*
- click a button to ``ssh`` into the instance
- view performance stats and live\* *monitoring charts*

Here are some useful shell commands:

General access:

.. code:: bash

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


Example: Set the consumer's startup script

.. code:: bash

    survey=ztf
    testid=mytestid
    vmname="${survey}-consumer-${testid}"
    broker_bucket="${GOOGLE_CLOUD_PROJECT}-${survey}-broker_files-${testid}"
    startupscript="gs://${broker_bucket}/night_conductor/vm_startup.sh"
    # set the startup script
    gcloud compute instances add-metadata "$vmname" --zone "$zone" \
            --metadata startup-script-url="$startupscript"
    # unset the startup script
    gcloud compute instances add-metadata "$vmname" --zone "$zone" \
            --metadata startup-script-url=""

--------------

Dataflow jobs
---------------

`GCP Console <https://console.cloud.google.com/dataflow/jobs>`__

Click on a job name. From here you can:

- view details about the job
- *stop/cancel/drain* the job
- view and interact with the *graph that represents the pipeline*
  PCollections and Transforms. Click on a node to
  view details about that step, including live *throughput charts*.
- view a page of live\* *monitoring charts* (click "JOB METRICS" tab at the
  top)
- access the *logs*. Click "LOGS" at the top, you will see tabs for
  "JOB LOGS", "WORKER LOGS", and "DIAGNOSTICS". Note that if you select a
  step in the graph you will only see logs related to that step (unselect
  the step to view logs for the full job). It's easiest to view the logs
  if you open them in the Logs Viewer by clicking the icon.

Command-line access:

- To start or update a job from the command line,
  see the README at broker/beam/README.md
- Job IDs: To update or stop a Dataflow job from the command line, you would
  need to look up the job ID assigned by Dataflow at runtime.
  If the night conductor VM started the
  job, the job ID has been set as a metadata attribute
  (see `Compute Engine VMs`_).

--------------

Logs Explorer
----------------

`GCP Console <https://console.cloud.google.com/logs>`__

View/query all (most?) logs for the project.

--------------

Pub/Sub topics and subscriptions
------------------------------------

`GCP Console (topics) <https://console.cloud.google.com/cloudpubsub/topic/list>`__
|
`GCP Console (subscriptions) <https://console.cloud.google.com/cloudpubsub/subscription/list>`__

Click on a topic/subscription. From here you can:

- view and edit topic/subscription details
- view live\* *monitoring charts*

--------------

\* Live monitoring charts have some lag time.
