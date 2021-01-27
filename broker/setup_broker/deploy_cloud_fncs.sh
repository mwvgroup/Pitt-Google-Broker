#! /bin/bash
# Deploys or deletes broker Cloud Functions
# This script will not (is not configured to) delete Cloud Functions that are in production

testrun="${1:-True}" # "True" uses test resources, else production resources
teardown="${2:-False}" # "True" tearsdown/deletes resources, else setup

#--- GCP resources used in this script
trigger_topic="ztf_alert_data"
PS_to_GCS_fnc="upload_ztf_bytes_to_bucket"
if [ "$testrun" = "True" ]; then
    trigger_topic="${trigger_topic}-test"
    PS_to_GCS_fnc="${PS_to_GCS_fnc}_test"
fi

#--- Pub/Sub -> Cloud Storage Avro cloud function
if [ "$teardown" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "$testrun" = "True" ]; then
        gcloud functions delete "$PS_to_GCS_fnc"
    fi
else # Deploy
    OGdir=$(pwd)
    cd .. && cd cloud_functions
    cd ps_to_gcs
    gcloud functions deploy "$PS_to_GCS_fnc" \
        --runtime python37 \
        --trigger-topic "$trigger_topic"
    cd $OGdir  # not sure if this is necessary
fi
