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
region="${5:-us-central1}"
PROJECT_ID=$GOOGLE_CLOUD_PROJECT # get the environment variable

#--- GCP resources used in this script
avro_bucket="${PROJECT_ID}-${survey}_alerts_${versiontag}"
avro_topic="projects/${PROJECT_ID}/topics/${survey}-alert_avros"
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
        gsutil rm -r "gs://${avro_bucket}"
        gcloud pubsub topics delete "${avro_topic}"
        gcloud pubsub topics delete "${ps_to_gcs_trigger_topic}"
        gcloud functions delete "${ps_to_gcs_CF_name}"
    fi

else # Deploy the Cloud Functions

    #--- Create the bucket that will store the alerts
    gsutil mb -l "${region}" "gs://${avro_bucket}"
    gsutil uniformbucketlevelaccess set on "gs://${avro_bucket}"
    gsutil requesterpays set on "gs://${avro_bucket}"
    gcloud storage buckets add-iam-policy-binding "gs://${avro_bucket}" \
        --member="allUsers" \
        --role="roles/storage.objectViewer"

    #--- Setup the Pub/Sub notifications on ZTF Avro storage bucket
    echo
    echo "Configuring Pub/Sub notifications on GCS bucket..."
    trigger_event=OBJECT_FINALIZE
    format=json  # json or none; if json, file metadata sent in message body
    gsutil notification create \
        -t "$avro_topic" \
        -e "$trigger_event" \
        -f "$format" \
        "gs://${avro_bucket}"

#--- Pub/Sub -> Cloud Storage Avro cloud function
    echo "Deploying Cloud Function: ${ps_to_gcs_CF_name}"
    ps_to_gcs_entry_point="run"
    memory=512MB  # standard 256MB is too small here (it was always on the edge)

    gcloud functions deploy "${ps_to_gcs_CF_name}" \
        --entry-point "${ps_to_gcs_entry_point}" \
        --runtime python37 \
        --memory "${memory}" \
        --trigger-topic "${ps_to_gcs_trigger_topic}" \
        --set-env-vars TESTID="${testid}",SURVEY="${survey}",VERSIONTAG="${versiontag}"
fi