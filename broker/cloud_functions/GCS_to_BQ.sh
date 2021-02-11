#!/bin/sh

###
# This script deploys the ``stream_GCS_to_BQ`` function in
# ``broker/alert_ingestion/GCS_to_BQ/main.py`` as a Google Cloud Function
# so that it listens for new Avro files added to a Google Cloud Storage bucket
# and uploads them to a BigQuery table.
#
# Note that the `GOOGLE_CLOUD_PROJECT` environment variable must be set
# explicitly within the `gcloud` command.
###

# NOT SURE OF THE RIGHT WAY TO GET INTO THIS DIRECTORY:
cd broker/cloud_functions/GCS_to_BQ

# deploy stream_GCS_to_BQ() to listen to the ztf_alert_avro_bucket
bucket="${GOOGLE_CLOUD_PROJECT}_ztf_alert_avro_bucket"
gcloud functions deploy stream_GCS_to_BQ --runtime python37 --set-env-vars GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT} --trigger-resource ${bucket} --trigger-event google.storage.object.finalize
