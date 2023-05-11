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
zone="${5:-us-central1-a}"

#--- GCP resources used in this script
store_bq_trigger_topic="${survey}-alerts"
store_bq_CF_name="${survey}-store_in_BigQuery"
ps_to_gcs_trigger_topic="${survey}-alerts_raw"
ps_to_gcs_CF_name="${survey}-upload_bytes_to_bucket"
check_cue_trigger_topic="${survey}-cue_night_conductor"
check_cue_CF_name="${survey}-check_cue_response"
lite_trigger_topic="${survey}-alerts"
lite_CF_name="${survey}-lite"
tag_trigger_topic="${survey}-lite"
tag_CF_name="${survey}-tag"
classify_snn_trigger_topic="${survey}-tagged"
classify_snn_CF_name="${survey}-classify_with_SuperNNova"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    store_bq_trigger_topic="${store_bq_trigger_topic}-${testid}"
    store_bq_CF_name="${store_bq_CF_name}-${testid}"
    ps_to_gcs_trigger_topic="${ps_to_gcs_trigger_topic}-${testid}"
    ps_to_gcs_CF_name="${ps_to_gcs_CF_name}-${testid}"
    check_cue_trigger_topic="${check_cue_trigger_topic}-${testid}"
    check_cue_CF_name="${check_cue_CF_name}-${testid}"
    lite_trigger_topic="${lite_trigger_topic}-${testid}"
    lite_CF_name="${lite_CF_name}-${testid}"
    tag_trigger_topic="${tag_trigger_topic}-${testid}"
    tag_CF_name="${tag_CF_name}-${testid}"
    classify_snn_trigger_topic="${classify_snn_trigger_topic}-${testid}"
    classify_snn_CF_name="${classify_snn_CF_name}-${testid}"
fi

if [ "$teardown" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "$testid" != "False" ]; then
        gcloud functions delete "$store_bq_CF_name"
        gcloud functions delete "$ps_to_gcs_CF_name"
        gcloud functions delete "$check_cue_CF_name"
        gcloud functions delete "$lite_CF_name"
        gcloud functions delete "$tag_CF_name"
        gcloud functions delete "$classify_snn_CF_name"
    fi

else # Deploy the Cloud Functions
    OGdir=$(pwd)

#--- BigQuery storage cloud function
    echo "Deploying Cloud Function: $store_bq_CF_name"
    store_bq_entry_point="run"

    cd .. && cd cloud_functions
    cd store_BigQuery

    gcloud functions deploy "$store_bq_CF_name" \
        --entry-point "$store_bq_entry_point" \
        --runtime python37 \
        --trigger-topic "$store_bq_trigger_topic" \
        --set-env-vars TESTID="${testid}",SURVEY="${survey}",VERSIONTAG="${versiontag}"

    cd $OGdir

#--- Pub/Sub -> Cloud Storage Avro cloud function
    echo "Deploying Cloud Function: $ps_to_gcs_CF_name"
    ps_to_gcs_entry_point="run"
    memory=512MB  # standard 256MB is too small here (it was always on the edge)

    cd .. && cd cloud_functions
    cd ps_to_gcs

    gcloud functions deploy "$ps_to_gcs_CF_name" \
        --entry-point "$ps_to_gcs_entry_point" \
        --runtime python37 \
        --memory "${memory}" \
        --trigger-topic "$ps_to_gcs_trigger_topic" \
        --set-env-vars TESTID="${testid}",SURVEY="${survey}",VERSIONTAG="${versiontag}"

    cd $OGdir

#--- Check cue response cloud function
    echo "Deploying Cloud Function: $check_cue_CF_name"
    check_cue_entry_point="run"

    cd .. && cd cloud_functions
    cd check_cue_response

    gcloud functions deploy "$check_cue_CF_name" \
        --entry-point "$check_cue_entry_point" \
        --runtime python37 \
        --trigger-topic "$check_cue_trigger_topic" \
        --set-env-vars TESTID="${testid}",SURVEY="${survey}",VERSIONTAG="${versiontag}"

    cd $OGdir

#--- alerts-lite cloud function
    echo "Deploying Cloud Function: $lite_CF_name"
    lite_entry_point="run"

    cd ../cloud_functions/lite || exit

    gcloud functions deploy "$lite_CF_name" \
        --entry-point "$lite_entry_point" \
        --runtime python37 \
        --trigger-topic "$lite_trigger_topic" \
        --set-env-vars TESTID="${testid}",SURVEY="${survey}",VERSIONTAG="${versiontag}"

    cd $OGdir

#--- tag alerts cloud function
    echo "Deploying Cloud Function: $tag_CF_name"
    tag_entry_point="run"
    memory=512MB  # standard 256MB is too small here

    cd ../cloud_functions/tag || exit

    gcloud functions deploy "$tag_CF_name" \
        --entry-point "$tag_entry_point" \
        --runtime python37 \
        --memory "$memory" \
        --trigger-topic "$tag_trigger_topic" \
        --set-env-vars TESTID="${testid}",SURVEY="${survey}",VERSIONTAG="${versiontag}"

    cd $OGdir

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
