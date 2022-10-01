#! /bin/bash
# Deploys or deletes broker Cloud Functions
# This script will not delete Cloud Functions that are in production
testid="${1:-test}"
teardown="${2:-False}"
survey="${3:-elasticc}"
max_instances="{$4:-500}"
zone="${CE_ZONE:-us-central1-a}"

#--- GCP resources used in this script
# store_bq_trigger_topic="${survey}-alerts"
# store_bq_CF_name="${survey}-store_in_BigQuery"
ps_to_gcs_trigger_topic="${survey}-alerts"
ps_to_gcs_CF_name="${survey}-upload_bytes_to_bucket"

# use test resources, if requested
if [ "${testid}" != "False" ]; then
    # store_bq_trigger_topic="${store_bq_trigger_topic}-${testid}"
    # store_bq_CF_name="${store_bq_CF_name}-${testid}"
    ps_to_gcs_trigger_topic="${ps_to_gcs_trigger_topic}-${testid}"
    ps_to_gcs_CF_name="${ps_to_gcs_CF_name}-${testid}"

fi

if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        # gcloud functions delete "$store_bq_CF_name"
        gcloud functions delete "${ps_to_gcs_CF_name}"
    fi

else # Deploy the Cloud Functions

    # #--- BigQuery storage cloud function
    # echo "Deploying Cloud Function: ${store_bq_CF_name}"
    # gcloud functions deploy "${store_bq_CF_name}" \
    #     --entry-point "run" \
    #     --source "../broker/cloud_functions/store_BigQuery" \
    #     --runtime "python37" \
    #     --trigger-topic "${store_bq_trigger_topic}" \
    #     --set-env-vars "TESTID=${testid},SURVEY=${survey}"

    #--- Pub/Sub -> Cloud Storage Avro cloud function
    echo "Deploying Cloud Function: ${ps_to_gcs_CF_name}"
    gcloud functions deploy "${ps_to_gcs_CF_name}" \
        --entry-point "run" \
        --source "../broker/cloud_functions/ps_to_gcs" \
        --memory "512MB" \
        --max-instances "${max_instances}" \
        --runtime "python37" \
        --trigger-topic "${ps_to_gcs_trigger_topic}" \
        --set-env-vars "TESTID=${testid},SURVEY=${survey}"

fi
