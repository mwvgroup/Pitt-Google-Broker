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
zone="${CE_ZONE:-us-central1-a}" # use env variable CE_ZONE if it exists

#--- GCP resources used in this script
store_bq_trigger_topic="${survey}-alerts"
store_bq_CF_name="${survey}-store_in_BigQuery"
ps_to_gcs_trigger_topic="${survey}-alerts"
ps_to_gcs_CF_name="${survey}-upload_bytes_to_bucket"
cue_nc_trigger_topic="${survey}-cue_night_conductor"
cue_nc_CF_name="${survey}-cue_night_conductor"
check_cue_trigger_topic="${cue_nc_trigger_topic}"
check_cue_CF_name="${survey}-check_cue_response"
classify_snn_CF_name="${survey}-classify_with_SuperNNova"
classify_snn_trigger_topic="${survey}-exgalac_trans"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    store_bq_trigger_topic="${store_bq_trigger_topic}-${testid}"
    store_bq_CF_name="${store_bq_CF_name}-${testid}"
    ps_to_gcs_trigger_topic="${ps_to_gcs_trigger_topic}-${testid}"
    ps_to_gcs_CF_name="${ps_to_gcs_CF_name}-${testid}"
    cue_nc_trigger_topic="${cue_nc_trigger_topic}-${testid}"
    cue_nc_CF_name="${cue_nc_CF_name}-${testid}"
    check_cue_trigger_topic="${check_cue_trigger_topic}-${testid}"
    check_cue_CF_name="${check_cue_CF_name}-${testid}"
    classify_snn_CF_name="${classify_snn_CF_name}-${testid}"
    classify_snn_trigger_topic="${classify_snn_trigger_topic}-${testid}"
fi

if [ "$teardown" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "$testid" != "False" ]; then
        gcloud functions delete "$store_bq_CF_name"
        gcloud functions delete "$ps_to_gcs_CF_name"
        gcloud functions delete "$cue_nc_CF_name"
        gcloud functions delete "$check_cue_CF_name"
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
        --set-env-vars TESTID="$testid",SURVEY="$survey"

    cd $OGdir

#--- Pub/Sub -> Cloud Storage Avro cloud function
    echo "Deploying Cloud Function: $ps_to_gcs_CF_name"
    ps_to_gcs_entry_point="run"

    cd .. && cd cloud_functions
    cd ps_to_gcs

    gcloud functions deploy "$ps_to_gcs_CF_name" \
        --entry-point "$ps_to_gcs_entry_point" \
        --runtime python37 \
        --trigger-topic "$ps_to_gcs_trigger_topic" \
        --set-env-vars TESTID="$testid",SURVEY="$survey"

    cd $OGdir

#--- Cue night-conductor cloud function
    echo "Deploying Cloud Function: $cue_nc_CF_name"
    cue_nc_entry_point="run"

    cd .. && cd cloud_functions
    cd cue_night_conductor

    gcloud functions deploy "$cue_nc_CF_name" \
        --entry-point "$cue_nc_entry_point" \
        --runtime python37 \
        --trigger-topic "$cue_nc_trigger_topic" \
        --set-env-vars TESTID="$testid",SURVEY="$survey",ZONE="$zone"

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
        --set-env-vars TESTID="$testid",SURVEY="$survey",ZONE="$zone" \
        --timeout 540s  # allow the CF to sleep without timing out

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
        --set-env-vars TESTID="$testid",SURVEY="$survey"

    cd $OGdir

fi
