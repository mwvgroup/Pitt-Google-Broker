# Cloud Functions

This directory contains cloud functions used by the Pitt-Google Broker.
Source code for each function is stored in a dedicated directory
and is accompanied by a bash script that deploys the cloud function
to the Google Cloud Platform.

For more information on cloud functions, see:
- [Cloud Functions](https://cloud.google.com/functions)
- [Cloud Functions Execution Environment](https://cloud.google.com/functions/docs/concepts/exec)
- [Cloud Pub/Sub Tutorial](https://cloud.google.com/functions/docs/tutorials/pubsub)

| Function | Description |
|---|---|
| `ps_to_gcs` | Listens to the `ztf_alerts` Pub/Sub stream and stores each alert as an Avro file in Cloud Storage bucket `ztf_alert_avros`. |
<!-- | `GCS_to_BQ` | Load the contents of avro files from Google Cloud Storage (GCP) into Big Query (BQ) | -->
<!-- | `scheduleinstance` | Deploys and schedules the execution of functions for launching virtual machines that ingest ZTF data into BQ | -->
