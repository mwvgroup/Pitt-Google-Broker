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
region="${4:-us-central1}"
PROJECT_ID=$GOOGLE_CLOUD_PROJECT # get the environment variable

MODULE_NAME="to-storage"  # lower case required by cloud run
ROUTE_RUN="/"  # url route that will trigger main.run()

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
avro_bucket=$(define_GCP_resources "${PROJECT_ID}-${survey}_alerts")
avro_topic=$(define_GCP_resources "projects/${PROJECT_ID}/topics/${survey}-alert_avros")
avro_subscription=$(define_GCP_resources "${survey}-alert_avros-counter")
cr_module_name=$(define_GCP_resources "${survey}-${MODULE_NAME}")  # lower case required by cloud run
module_image_name="gcr.io/${PROJECT_ID}/${cr_module_name}"
ps_input_subscrip=$(define_GCP_resources "${survey}-alerts_raw") # pub/sub subscription used to trigger cloud run module
runinvoker_svcact="cloud-run-invoker@${PROJECT_ID}.iam.gserviceaccount.com"
trigger_topic=$(define_GCP_resources "${survey}-alerts_raw")


if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        gsutil rm -r "gs://${avro_bucket}"
        gcloud pubsub topics delete "${avro_topic}"
        gcloud pubsub subscriptions delete "${avro_subscription}"
        gcloud run services delete "${cr_module_name}" --region "${region}"
        gcloud artifacts repositories delete cloud-run-services/"${module_image_name}" --location="${region}"
    fi

else # Deploy the Cloud Run service

    #--- Create the bucket that will store the alerts
    gsutil mb -l "${region}" "gs://${avro_bucket}"
    gsutil uniformbucketlevelaccess set on "gs://${avro_bucket}"
    gsutil requesterpays set on "gs://${avro_bucket}"
    gcloud storage buckets add-iam-policy-binding "gs://${avro_bucket}" \
        --member="allUsers" \
        --role="roles/storage.objectViewer"

    #--- Setup the Pub/Sub notifications on the Avro storage bucket
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


#--- Deploy Cloud Run
    echo "Creating container image and deploying to Cloud Run..."
    moduledir="."  # assumes deploying what's in our current directory
    config="${moduledir}/cloudbuild.yaml"
    url=$(gcloud builds submit --config="${config}" \
        --substitutions="_SURVEY=${survey},_TESTID=${testid},_MODULE_NAME=${cr_module_name}" \
        "${moduledir}" | sed -n 's/^Step #2: Service URL: \(.*\)$/\1/p')

    echo "Creating trigger subscription for Cloud Run..."
    # WARNING:  This is set to retry failed deliveries. If there is a bug in main.py this will
    # retry indefinitely, until the message is delete manually.
    gcloud pubsub subscriptions create "${ps_input_subscrip}" \
        --topic "${trigger_topic}" \
        --topic-project "${PROJECT_ID}" \
        --ack-deadline=600 \
        --push-endpoint="${url}${ROUTE_RUN}" \
        --push-auth-service-account="${runinvoker_svcact}"
fi
