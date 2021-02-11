# Cloud Functions

This directory contains cloud functions used by the Pitt-Google Broker. 
Source code for each function is stored in a dedicated directory
and is accompanied by a bash script that deploys the cloud function
to the Google Cloud Platform.

For more information on cloud functions, see: https://cloud.google.com/functions

| Function | Description |
|---|---|
| `GCS_to_BQ` | Load the contents of avro files from Google Cloud Storage (GCP) into Big Query (BQ) |
| `scheduleinstance` | Deploys and schedules the execution of functions for launching virtual machines that ingest ZTF data into BQ |