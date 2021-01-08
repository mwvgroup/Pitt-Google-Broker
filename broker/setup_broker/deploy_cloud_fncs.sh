#! /bin/bash
# Deploys broker Cloud Functions

OGdir=$(pwd)
cd .. && cd cloud_functions

# Pub/Sub -> Cloud Storage Avro
cd ps_to_gcs
topic=ztf_alert_data
gcloud functions deploy upload_ztf_bytes_to_bucket \
    --runtime python37 \
    --trigger-topic ${topic}

cd $OGdir  # not sure if this is necessary
