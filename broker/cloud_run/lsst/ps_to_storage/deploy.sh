#! /bin/bash
# Deploys or deletes broker Cloud Run service
# This script will not delete Cloud Run services that are in production

# "False" uses production resources
# any other string will be appended to the names of all resources
testid="${1:-test}"
# "True" tearsdown/deletes resources, else setup
teardown="${2:-False}"
# name of the survey this broker instance will ingest
survey="${3:-lsst}"
region="${4:-us-central1}"
# get the environment variable
PROJECT_ID=$GOOGLE_CLOUD_PROJECT
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")

MODULE_NAME="alerts-to-storage"  # lower case required by cloud run
ROUTE_RUN="/"  # url route that will trigger main.run()

define_GCP_resources() {
    local base_name="$1"
    local separator="${2:--}"
    local testid_suffix=""

    if [ "$testid" != "False" ] && [ -n "$testid" ]; then
        testid_suffix="${separator}${testid}"
    fi
    echo "${base_name}${testid_suffix}"
}

#--- GCP resources used in this script
artifact_registry_repo=$(define_GCP_resources "${survey}-cloud-run-services")
cr_module_name=$(define_GCP_resources "${survey}-${MODULE_NAME}")  # lower case required by cloud run
gcs_avro_bucket=$(define_GCP_resources "${PROJECT_ID}-${survey}_alerts")
ps_deadletter_topic=$(define_GCP_resources "${survey}-deadletter")
ps_input_subscrip=$(define_GCP_resources "${survey}-alerts_raw") # pub/sub subscription used to trigger cloud run module
ps_topic_avro=$(define_GCP_resources "projects/${PROJECT_ID}/topics/${survey}-alert_avros")
ps_trigger_topic=$(define_GCP_resources "${survey}-alerts_raw")
runinvoker_svcact="cloud-run-invoker@${PROJECT_ID}.iam.gserviceaccount.com"
service_account="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"
if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        echo
        echo "Deleting resources for ${MODULE_NAME} module..."
        gsutil rm -r "gs://${gcs_avro_bucket}"
        gcloud pubsub topics delete "${ps_topic_avro}"
        gcloud pubsub subscriptions delete "${ps_subscription_avro}"
        gcloud pubsub subscriptions delete "${ps_input_subscrip}"
        gcloud run services delete "${cr_module_name}" --region "${region}"
    fi
else
    echo
    echo "Creating gcs_avro_bucket and uploading files..."
    if ! gsutil ls -b "gs://${gcs_avro_bucket}" >/dev/null 2>&1; then
        gsutil mb -b on -l "${region}" "gs://${gcs_avro_bucket}"
        gsutil uniformbucketlevelaccess set on "gs://${gcs_avro_bucket}"
        gsutil requesterpays set on "gs://${gcs_avro_bucket}"
        gcloud storage buckets add-iam-policy-binding "gs://${gcs_avro_bucket}" \
            --member="allUsers" \
            --role="roles/storage.objectViewer"
    else
        echo "${gcs_avro_bucket} already exists."
    fi

    echo
    echo "Configuring Pub/Sub notifications on GCS bucket..."
    trigger_event=OBJECT_FINALIZE
    format=json  # json or none; if json, file metadata sent in message body
    gsutil notification create \
        -t "$ps_topic_avro" \
        -e "$trigger_event" \
        -f "$format" \
        "gs://${gcs_avro_bucket}"
    gcloud pubsub subscriptions create "${ps_subscription_avro}" --topic="${ps_topic_avro}"

    #--- Deploy Cloud Run service
    echo
    echo "Creating container image for ${MODULE_NAME} module and deploying to Cloud Run..."
    moduledir="."  # assumes deploying what's in our current directory
    config="${moduledir}/cloudbuild.yaml"
    url=$(gcloud builds submit --config="${config}" \
        --substitutions="_SURVEY=${survey},_TESTID=${testid},_MODULE_NAME=${cr_module_name},_REPOSITORY=${artifact_registry_repo}" \
        "${moduledir}" | sed -n 's/^Step #2: Service URL: \(.*\)$/\1/p')
    echo
    echo "Creating trigger subscription for ${MODULE_NAME} Cloud Run service..."
    gcloud pubsub subscriptions create "${ps_input_subscrip}" \
        --topic "${ps_trigger_topic}" \
        --topic-project "${PROJECT_ID}" \
        --ack-deadline=600 \
        --push-endpoint="${url}${ROUTE_RUN}" \
        --push-auth-service-account="${runinvoker_svcact}" \
        --dead-letter-topic="${ps_deadletter_topic}" \
        --max-delivery-attempts=5
    gcloud pubsub subscriptions add-iam-policy-binding "${ps_input_subscrip}" \
        --member="serviceAccount:${service_account}" \
        --role="roles/pubsub.subscriber"
fi
