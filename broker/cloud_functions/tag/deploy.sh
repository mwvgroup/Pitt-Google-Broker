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
tag_trigger_topic="${survey}-lite"
tag_CF_name="${survey}-tag"

# use test resources, if requested
if [ "$testid" != "False" ]; then
    tag_trigger_topic="${tag_trigger_topic}-${testid}"
    tag_CF_name="${tag_CF_name}-${testid}"
fi

if [ "$teardown" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "$testid" != "False" ]; then
        gcloud functions delete "$tag_CF_name"
    fi

else # Deploy the Cloud Functions
#--- tag alerts cloud function
    echo "Deploying Cloud Function: $tag_CF_name"
    tag_entry_point="run"
    memory=512MB  # standard 256MB is too small here

    gcloud functions deploy "$tag_CF_name" \
        --entry-point "$tag_entry_point" \
        --runtime python312 \
        --memory "$memory" \
        --trigger-topic "$tag_trigger_topic" \
        --set-env-vars TESTID="${testid}",SURVEY="${survey}",VERSIONTAG="${versiontag}",GCP_PROJECT="${GOOGLE_CLOUD_PROJECT}"
fi
