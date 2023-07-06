#! /bin/bash
# Deploys or deletes broker Cloud Function
# This script will not delete Cloud Functions that are in production

testid="${1:-test}"
# "False" uses production resources
# any other string will be appended to the names of all resources
teardown="${2:-False}"
# "True" tearsdown/deletes resources, else setup
survey="${3:-ztf}"
# name of the survey this broker instance will ingest
versiontag="${4:-v3_3}"

#--- GCP resources used in this script
store_bq_trigger_topic="${survey}-alerts"
store_bq_CF_name="${survey}-store_in_BigQuery"

# use test resources, if requested
if [ "${testid}" != "False" ]; then
    store_bq_trigger_topic="${store_bq_trigger_topic}-${testid}"
    store_bq_CF_name="${store_bq_CF_name}-${testid}"
fi

if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        gcloud functions delete "${store_bq_CF_name}"
    fi

else # Deploy the Cloud Functions
#--- BigQuery storage cloud function
    echo "Deploying Cloud Function: ${store_bq_CF_name}"
    store_bq_entry_point="run"

    gcloud functions deploy "${store_bq_CF_name}" \
        --entry-point "${store_bq_entry_point}" \
        --runtime python37 \
        --trigger-topic "${store_bq_trigger_topic}" \
        --set-env-vars TESTID="${testid}",SURVEY="${survey}",VERSIONTAG="${versiontag}"
fi