#! /bin/bash
# Deploys or deletes broker Cloud Functions
# This script will not delete Cloud Functions that are in production

testid="${1:-test}"
# "False" uses production resources
# any other string will be appended to the names of all resources
teardown="${2:-False}"
# "True" tearsdown/deletes resources, else setup
survey="${3:-elasticc}"
# name of the survey this broker instance will ingest
max_instances="${4:-500}"
BROKER_VERSION="${5:-0.1.0e}"
PROJECT_ID="${PROJECT_ID:-avid-heading-329016}"

#--- GCP resources used in this script
avro_bucket="${PROJECT_ID}-${survey}-alert_avros"
avro_topic="${survey}-alert_avros"
ps_to_gcs_trigger_topic="${survey}-alerts_raw"
ps_to_gcs_CF_name="${survey}-upload_bytes_to_bucket"

# use test resources, if requested
if [ "${testid}" != "False" ]; then
    avro_bucket="${avro_bucket}-${testid}"
    avro_topic="${avro_topic}-${testid}"
    ps_to_gcs_trigger_topic="${ps_to_gcs_trigger_topic}-${testid}"
    ps_to_gcs_CF_name="${ps_to_gcs_CF_name}-${testid}"
fi

if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        gcloud functions delete "${ps_to_gcs_CF_name}"
        o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
        gsutil -m -o "${o}" rm -r "gs://${avro_bucket}"
    fi

else # Deploy the Cloud Functions

    #--- Create buckets if they do not exist
    if ! gsutil ls -b "gs://${avro_bucket}/" >/dev/null 2>&1; then
        gsutil mb "gs://${avro_bucket}"
        user="allUsers"
        roleid="projects/${GOOGLE_CLOUD_PROJECT}/roles/userPublic"
        gsutil iam ch "${user}:${roleid}" "gs://${avro_bucket}"
    fi

#--- Pub/Sub -> Cloud Storage Avro cloud function
    echo "Deploying Cloud Function: ${ps_to_gcs_CF_name}"
    ps_to_gcs_entry_point="run"
    memory=512MB  # standard 256MB is too small here (it was always on the edge)

    gcloud functions deploy "${ps_to_gcs_CF_name}" \
        --entry-point "${ps_to_gcs_entry_point}" \
        --runtime python37 \
        --memory "${memory}" \
        --max-instances "${max_instances}" \
        --trigger-topic "${ps_to_gcs_trigger_topic}" \
        --set-env-vars TESTID="${testid}",SURVEY="${survey}",BROKER_VERSION="${BROKER_VERSION}"
fi