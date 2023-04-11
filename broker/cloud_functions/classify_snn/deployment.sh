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
versiontag="${4:-v3_3}"
zone="${CE_ZONE:-us-central1-a}" # use env variable CE_ZONE if it exists

#--- GCP resources used in this script
classify_snn_trigger_topic="${survey}-tagged"
classify_snn_CF_name="${survey}-classify_with_SuperNNova"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    classify_snn_trigger_topic="${classify_snn_trigger_topic}-${testid}"
    classify_snn_CF_name="${classify_snn_CF_name}-${testid}"
fi

if [ "$teardown" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "$testid" != "False" ]; then
        gcloud functions delete "$classify_snn_CF_name"
    fi

else # Deploy the Cloud Functions
    OGdir=$(pwd)

#--- classify with SNN cloud function
    echo "Deploying Cloud Function: $classify_snn_CF_name"
    classify_snn_entry_point="run"
    memory=512MB  # standard 256MB is too small here

    cd .. && cd cloud_functions
    cd classify_snn

    gcloud functions deploy "$classify_snn_CF_name" \
        --entry-point "$classify_snn_entry_point" \
        --memory "$memory" \
        --runtime python37 \
        --trigger-topic "$classify_snn_trigger_topic" \
        --set-env-vars TESTID="${testid}",SURVEY="${survey}",VERSIONTAG="${versiontag}"

    cd $OGdir

fi
