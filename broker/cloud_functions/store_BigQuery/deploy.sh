#! /bin/bash
# Deploys or deletes broker Cloud Function
# This script will not delete Cloud Functions that are in production

# "False" uses production resources
# any other string will be appended to the names of all resources
testid="${1:-test}"
# "True" tearsdown/deletes resources, else setup
teardown="${2:-False}"
# name of the survey this broker instance will ingest
survey="${3:-ztf}"
# schema version
versiontag="${4:-v4_02}"

# function used to define GCP resources; appends testid if needed
define_GCP_resources() {
    local base_name="$1"
    local testid_suffix=""

    if [ "$testid" != "False" ]; then
        testid_suffix="-${testid}"
    fi

    echo "${base_name}${testid_suffix}"
}

#--- GCP resources used in this script
store_bq_trigger_topic=$(define_GCP_resources "${survey}-alerts")
store_bq_CF_name=$(define_GCP_resources "${survey}-store_in_BigQuery")

if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        gcloud functions delete "${store_bq_CF_name}"
    fi

else # Deploy the Cloud Functions
#--- BigQuery storage cloud function
    echo "Deploying Cloud Function: ${store_bq_CF_name}"
    store_bq_entry_point="run"
    memory=512MB

    gcloud functions deploy "${store_bq_CF_name}" \
        --entry-point "${store_bq_entry_point}" \
        --runtime python312 \
        --memory "${memory}" \
        --trigger-topic "${store_bq_trigger_topic}" \
        --set-env-vars TESTID="${testid}",SURVEY="${survey}",GCP_PROJECT="${GOOGLE_CLOUD_PROJECT}",VERSIONTAG="${versiontag}"
fi
