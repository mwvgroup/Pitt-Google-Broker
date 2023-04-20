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
zone="${CE_ZONE:-us-central1-a}" # use env variable CE_ZONE if it exists

#--- Make the user confirm the settings
echo
echo "deployment.sh will run with the following configs: "
echo
echo "testid = ${testid}"
echo "teardown = ${teardown}"
echo "survey = ${survey}"
echo "versiontag = ${versiontag}"
echo "zone = ${zone}"
echo
echo "Continue? [y/(n)]: "

read input
input="${input:-n}"
if [ "${input}" != "y" ]; then
    echo "Exiting setup."
    echo
    exit
fi

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
        --runtime python37 \
        --trigger-topic "${lite_trigger_topic}" \
        --set-env-vars TESTID="${testid}",SURVEY="${survey}",VERSIONTAG="${versiontag}"
fi