#! /bin/bash
# Deploys or deletes broker Cloud Run service
# This script will not delete Cloud Run services that are in production

# "False" uses production resources
# any other string will be appended to the names of all resources
testid="${1:-test}"
# "True" tearsdown/deletes resources, else setup
teardown="${2:-False}"
# name of the survey this broker instance will ingest
survey="${3:-ztf}"
region="${4:-us-central1}"
# get environment variables
PROJECT_ID=$GOOGLE_CLOUD_PROJECT

MODULE_NAME="supernnova"  # lower case required by cloud run
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
ps_input_subscrip=$(define_GCP_resources "${survey}-SuperNNova") # Pub/Sub subscription used to trigger Cloud Run service
ps_trigger_topic=$(define_GCP_resources "${survey}-lite")

# additional GCP resources & variables used in this script
cr_module_name=$(define_GCP_resources "${survey}-${MODULE_NAME}")  # lower case required by Cloud Run
runinvoker_svcact="cloud-run-invoker@${PROJECT_ID}.iam.gserviceaccount.com"

if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        echo
        echo "Deleting resources for ${MODULE_NAME} module..."
        gcloud pubsub subscriptions delete "${ps_input_subscrip}"
        gcloud run services delete "${cr_module_name}" --region "${region}"
    fi

else
    #--- Deploy Cloud Run
    echo
    echo "Creating container image for ${MODULE_NAME} module and deploying to Cloud Run..."
    moduledir="."  # deploys what's in our current directory
    config="${moduledir}/cloudbuild.yaml"
    url=$(gcloud builds submit --config="${config}" \
        --substitutions="_SURVEY=${survey},_TESTID=${testid},_MODULE_NAME=${cr_module_name},_REPOSITORY=${artifact_registry_repo}" \
        --region="${region}" \
        "${moduledir}" | sed -n 's/^Step #2: Service URL: \(.*\)$/\1/p')

    # ensure the Cloud Run service has the necessary permisions
    role="roles/run.invoker"
    gcloud run services add-iam-policy-binding "${cr_module_name}" \
        --member="serviceAccount:${runinvoker_svcact}" \
        --role="${role}"
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
