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
lite_trigger_topic="${survey}-alerts"
lite_CF_name="${survey}-lite"

# use test resources, if requested
if [ "${testid}" != "False" ]; then
    lite_trigger_topic="${lite_trigger_topic}-${testid}"
    lite_CF_name="${lite_CF_name}-${testid}"
fi

if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        gcloud functions delete "${lite_CF_name}"
    fi

else # Deploy the Cloud Functions
#--- alerts-lite cloud function
    echo "Deploying Cloud Function: ${lite_CF_name}"
    lite_entry_point="run"

    gcloud functions deploy "${lite_CF_name}" \
        --entry-point "${lite_entry_point}" \
        --runtime python312 \
        --trigger-topic "${lite_trigger_topic}" \
        --set-env-vars TESTID="${testid}",SURVEY="${survey}",VERSIONTAG="${versiontag}"
fi
