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
zone="${5:-us-central1-a}"

#--- GCP resources used in this script
check_cue_trigger_topic="${survey}-cue_night_conductor"
check_cue_CF_name="${survey}-check_cue_response"

# use test resources, if requested
if [ "${testid}" != "False" ]; then
    check_cue_trigger_topic="${check_cue_trigger_topic}-${testid}"
    check_cue_CF_name="${check_cue_CF_name}-${testid}"
fi

if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        gcloud functions delete "${check_cue_CF_name}"
    fi

else # Deploy the Cloud Function

#--- Check cue response cloud function
    echo "Deploying Cloud Function: ${check_cue_CF_name}"
    check_cue_entry_point="run"

    gcloud functions deploy "${check_cue_CF_name}" \
        --entry-point "${check_cue_entry_point}" \
        --runtime python312 \
        --trigger-topic "${check_cue_trigger_topic}" \
        --set-env-vars TESTID="${testid}",SURVEY="${survey}",VERSIONTAG="${versiontag}",ZONE="${zone}"
fi
