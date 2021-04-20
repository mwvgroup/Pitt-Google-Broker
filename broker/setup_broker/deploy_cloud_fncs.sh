#! /bin/bash
# Deploys or deletes broker Cloud Functions
# This script will not delete Cloud Functions that are in production

testid="${1:-test}"
# "False" uses production resources
# any other string will be appended to the names of all resources
teardown="${2:-False}"
# "True" tearsdown/deletes resources, else setup
survey="${3:-ztf}"
# name of the survey this broker instance will ingest
# 'ztf' or 'decat'

#--- GCP resources used in this script
trigger_topic="ztf_alerts"
ps_to_gcs_CF_name="upload_bytes_to_bucket"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    trigger_topic="${trigger_topic}-${testid}"
    ps_to_gcs_CF_name="${ps_to_gcs_CF_name}_${testid}"
fi

#--- Pub/Sub -> Cloud Storage Avro cloud function
ps_to_gcs_entry_point="run"

if [ "$teardown" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "$testid" != "False" ]; then
        gcloud functions delete "$ps_to_gcs_CF_name"
    fi

else # Deploy
    OGdir=$(pwd)
    cd .. && cd cloud_functions
    cd ps_to_gcs

    gcloud functions deploy "$ps_to_gcs_CF_name" \
        --entry-point "$ps_to_gcs_entry_point" \
        --runtime python37 \
        --trigger-topic "$trigger_topic" \
        --set-env-vars TESTID="$testid",SURVEY="$survey"

    cd $OGdir  # not sure if this is necessary
fi
