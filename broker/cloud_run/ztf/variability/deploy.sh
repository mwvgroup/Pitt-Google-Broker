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
PROJECT_ID=$GOOGLE_CLOUD_PROJECT # get the environment variable

MODULE_NAME="variability"  # lower case required by cloud run
ROUTE_RUN="/"  # url route that will trigger main.run()

# function used to define GCP resources; appends testid if needed
define_GCP_resources() {
    local base_name="$1"
    local testid_suffix=""

    if [ "$testid" != "False" ]; then
        if [ "$base_name" = "${survey}" ] || [ "$base_name" = "${survey}_value_added" ]; then
            testid_suffix="_${testid}"  # complies with BigQuery naming conventions
        else
            testid_suffix="-${testid}"
        fi
    fi

    echo "${base_name}${testid_suffix}"
}

#--- GCP resources used in this script
artifact_registry_repo=$(define_GCP_resources "${survey}-cloud-run-services")
bq_dataset=$(define_GCP_resources "${survey}_value_added")
bq_table="variability"
cr_module_name=$(define_GCP_resources "${survey}-${MODULE_NAME}")  # lower case required by cloud run
ps_input_subscrip=$(define_GCP_resources "${survey}-${MODULE_NAME}") # pub/sub subscription used to trigger cloud run module
ps_output_topic=$(define_GCP_resources "${survey}-${MODULE_NAME}")
runinvoker_svcact="cloud-run-invoker@${PROJECT_ID}.iam.gserviceaccount.com"
trigger_topic=$(define_GCP_resources "${survey}-tagged")
# topics and subscriptions involved in writing data to BigQuery
bq_subscription=$(define_GCP_resources "${survey}-${MODULE_NAME}-bigquery-import") # BigQuery subscription
ps_deadletter_topic=$(define_GCP_resources "${survey}-${MODULE_NAME}-bigquery-import-deadletter")
ps_deadletter_subscription="${ps_deadletter_topic}"


if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        gcloud pubsub topics delete "${ps_output_topic}"
        gcloud pubsub topics delete "${ps_deadletter_topic}"
        gcloud pubsub subscriptions delete "${bq_subscription}"
        gcloud pubsub subscriptions delete "${ps_deadletter_subscription}"
        gcloud pubsub subscriptions delete "${ps_input_subscrip}"
        gcloud run services delete "${cr_module_name}" --region "${region}"
    fi

else # Deploy the Cloud Run service

#--- Deploy Cloud Run
    gcloud pubsub topics create "${ps_output_topic}"
    gcloud pubsub topics create "${ps_deadletter_topic}"
    gcloud pubsub subscriptions create "${ps_deadletter_subscription}" --topic="${ps_deadletter_topic}"
    gcloud pubsub subscriptions create "${bq_subscription}" \
        --topic="${ps_output_topic}" \
        --bigquery-table="${PROJECT_ID}:${bq_dataset}.${bq_table}" \
        --use-table-schema \
        --drop-unknown-fields \
        --dead-letter-topic="${ps_deadletter_topic}" \
        --max-delivery-attempts=5 \
        --dead-letter-topic-project="${PROJECT_ID}"


    echo "Creating container image and deploying to Cloud Run..."
    moduledir="."  # assumes deploying what's in our current directory
    config="${moduledir}/cloudbuild.yaml"
    url=$(gcloud builds submit --config="${config}" \
        --substitutions="_SURVEY=${survey},_TESTID=${testid},_MODULE_NAME=${cr_module_name},_REPOSITORY=${artifact_registry_repo}" \
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
