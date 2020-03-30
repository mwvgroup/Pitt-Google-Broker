#!/bin/sh

###
# This script deploys the ``stream_GCS_to_BQ`` function in
# ``broker/alert_ingestion/GCS_to_BQ/main.py`` as a Google Cloud Function
# so that it listens for new Avro files added to a Google Cloud Storage bucket
# and uploads them to a BigQuery table.
###

cd alert_ingestion/GCS_to_BQ

# deploy stream_GCS_to_BQ() to listen to the alert avro bucket
bucket="${GOOGLE_CLOUD_PROJECT}_alert_avro_bucket"
gcloud functions deploy stream_GCS_to_BQ --runtime python37 --trigger-resource ${bucket} --trigger-event google.storage.object.finalize
