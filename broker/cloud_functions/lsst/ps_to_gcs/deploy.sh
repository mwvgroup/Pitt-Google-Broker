#! /bin/bash
# Deploys or deletes broker Cloud Functions
# This script will not delete Cloud Functions that are in production

# "False" uses production resources
# any other string will be appended to the names of all resources
testid="${1:-test}"
# "True" tearsdown/deletes resources, else setup
teardown="${2:-False}"
# name of the survey this broker instance will ingest
survey="${3:-lsst}"
# schema version
versiontag="${4:-v7_3}"
region="${5:-us-central1}"
PROJECT_ID=$GOOGLE_CLOUD_PROJECT # get the environment variable

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
avro_bucket=$(define_GCP_resources "${PROJECT_ID}-${survey}_alerts_${versiontag}")
avro_topic=$(define_GCP_resources "projects/${PROJECT_ID}/topics/${survey}-alert_avros")
avro_subscription=$(define_GCP_resources "${survey}-alert_avros-counter")
ps_to_gcs_trigger_topic=$(define_GCP_resources "${survey}-alerts_raw")
ps_to_gcs_CF_name=$(define_GCP_resources "${survey}-upload_bytes_to_bucket")

if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        gsutil rm -r "gs://${avro_bucket}"
        gcloud pubsub topics delete "${avro_topic}"
        gcloud pubsub subscriptions delete "${avro_subscription}"
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
    gcloud pubsub subscriptions create "${avro_subscription}" --topic="${avro_topic}"


#--- Pub/Sub -> Cloud Storage Avro cloud function
    echo "Deploying Cloud Function: ${ps_to_gcs_CF_name}"
    ps_to_gcs_entry_point="run"
    memory=512MB  # standard 256MB is too small here (it was always on the edge)

    gcloud functions deploy "${ps_to_gcs_CF_name}" \
        --entry-point "${ps_to_gcs_entry_point}" \
        --runtime python312 \
        --memory "${memory}" \
        --trigger-topic "${ps_to_gcs_trigger_topic}" \
        --set-env-vars TESTID="${testid}",SURVEY="${survey}",VERSIONTAG="${versiontag}",GCP_PROJECT="${PROJECT_ID}"
fi
