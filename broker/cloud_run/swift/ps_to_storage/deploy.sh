#! /bin/bash
# Deploys or deletes broker Cloud Run service
# This script will not delete Cloud Run services that are in production

# "False" uses production resources
# any other string will be appended to the names of all resources
testid="${1:-test}"
# "True" tearsdown/deletes resources, else setup
teardown="${2:-False}"
# name of the survey this broker instance will ingest
survey="${3:-swift}"
region="${4:-us-central1}"
versiontag="${5:-v4_5_0}"
# get the environment variable
PROJECT_ID=$GOOGLE_CLOUD_PROJECT

MODULE_NAME="alerts-to-storage"  # lower case required by cloud run
ROUTE_RUN="/"  # url route that will trigger main.run()

define_GCP_resources() {
    local base_name="$1"
    local testid_suffix=""

    if [ "$testid" != "False" ]; then
        testid_suffix="-${testid}"
    fi
    echo "${base_name}${testid_suffix}"
}

#--- GCP resources used in this script
artifact_registry_repo=$(define_GCP_resources "${survey}-cloud-run-services")
cr_module_name=$(define_GCP_resources "${survey}-${MODULE_NAME}")  # lower case required by cloud run
gcs_json_bucket=$(define_GCP_resources "${PROJECT_ID}-${survey}_alerts")
ps_input_subscrip=$(define_GCP_resources "${survey}-alerts_raw") # pub/sub subscription used to trigger cloud run module
ps_topic_alert_in_bucket=$(define_GCP_resources "projects/${PROJECT_ID}/topics/${survey}-alert_in_bucket")
ps_trigger_topic=$(define_GCP_resources "${survey}-alerts_raw")
runinvoker_svcact="cloud-run-invoker@${PROJECT_ID}.iam.gserviceaccount.com"

if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        echo
        echo "Deleting resources for ${MODULE_NAME} module..."
        gsutil rm -r "gs://${gcs_json_bucket}"
        gcloud pubsub topics delete "${ps_topic_alert_in_bucket}"
        gcloud pubsub subscriptions delete "${ps_input_subscrip}"
        gcloud run services delete "${cr_module_name}" --region "${region}"
    fi
else
    echo
    echo "Creating json_bucket..."
    if ! gsutil ls -b "gs://${gcs_json_bucket}" >/dev/null 2>&1; then
        #--- Create the bucket that will store the alerts
        gsutil mb -l "${region}" "gs://${gcs_json_bucket}"
        gsutil uniformbucketlevelaccess set on "gs://${gcs_json_bucket}"
        gsutil requesterpays set on "gs://${gcs_json_bucket}"
        # set IAM policies on public GCP resources
        if [ "$testid" = "False" ]; then
            gcloud storage buckets add-iam-policy-binding "gs://${gcs_json_bucket}" \
                --member="allUsers" \
                --role="roles/storage.objectViewer"
        fi
    else
        echo "${gcs_json_bucket} already exists."
    fi

    #--- Setup the Pub/Sub notifications on the JSON storage bucket
    echo
    echo "Configuring Pub/Sub notifications on GCS bucket..."
    trigger_event=OBJECT_FINALIZE
    format=json  # json or none; if json, file metadata sent in message body
    gsutil notification create \
        -t "$ps_topic_alert_in_bucket" \
        -e "$trigger_event" \
        -f "$format" \
        "gs://${gcs_json_bucket}"

    #--- Deploy the Cloud Run service
    echo
    echo "Creating container image for ${MODULE_NAME} module and deploying to Cloud Run..."
    moduledir="."  # assumes deploying what's in our current directory
    config="${moduledir}/cloudbuild.yaml"
    url=$(gcloud builds submit --config="${config}" \
        --substitutions="_SURVEY=${survey},_TESTID=${testid},_MODULE_NAME=${cr_module_name},_REPOSITORY=${artifact_registry_repo},_VERSIONTAG=${versiontag}" \
        "${moduledir}" | sed -n 's/^Step #2: Service URL: \(.*\)$/\1/p')
    echo
    echo "Creating trigger subscription for ${MODULE_NAME} Cloud Run service..."
    # WARNING:  This is set to retry failed deliveries. If there is a bug in main.py this will
    # retry indefinitely, until the message is delete manually.
    gcloud pubsub subscriptions create "${ps_input_subscrip}" \
        --topic "${ps_trigger_topic}" \
        --topic-project "${PROJECT_ID}" \
        --ack-deadline=600 \
        --push-endpoint="${url}${ROUTE_RUN}" \
        --push-auth-service-account="${runinvoker_svcact}"
fi
