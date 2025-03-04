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

MODULE_NAME="supernnova"  # lower case required by cloud run
ROUTE_RUN="/"  # url route that will trigger main.run()

# function used to define GCP resources; appends testid if needed
define_GCP_resources() {
    local base_name="$1"
    local testid_suffix=""

    if [ "$testid" != "False" ]; then
        if [ "$base_name" = "$survey" ]; then
            testid_suffix="_${testid}"  # complies with BigQuery naming conventions
        else
            testid_suffix="-${testid}"
        fi
    fi

    echo "${base_name}${testid_suffix}"
}

#--- GCP resources used in this script
artifact_registry_repo=$(define_GCP_resources "cloud-run-services")
ps_input_subscrip=$(define_GCP_resources "${survey}-alerts") # pub/sub subscription used to trigger cloud run module
# should we keep ps_output_topic?
ps_output_topic="${survey}-SuperNNova"  # desc is using this. leave camel case to avoid a breaking change
subscription_bigquery_import=$(define_GCP_resources "${survey}-bigquery-import-SuperNNova") # BigQuery subscription
topic_bigquery_import=$(define_GCP_resources "${survey}-bigquery-import-SuperNNova")
trigger_topic=$(define_GCP_resources "${survey}-alerts")
deadletter_topic_bigquery_import=$(define_GCP_resources "${survey}-bigquery-import-SuperNNova-deadletter")
deadletter_subscription_bigquery_import="${deadletter_topic_bigquery_import}"

# additional GCP resources & variables used in this script
bq_dataset=$(define_GCP_resources "${survey}")
supernnova_classifications_table="SuperNNova"
cr_module_name=$(define_GCP_resources "${survey}-${MODULE_NAME}")  # lower case required by cloud run
runinvoker_svcact="cloud-run-invoker@${PROJECT_ID}.iam.gserviceaccount.com"


if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        gcloud pubsub topics delete "${ps_output_topic}"
        gcloud pubsub topics delete "${topic_bigquery_import}"
        gcloud pubsub subscriptions delete "${ps_input_subscrip}"
        gcloud pubsub subscriptions delete "${subscription_bigquery_import}"
        gcloud run services delete "${cr_module_name}" --region "${region}"
    fi

else # Deploy the Cloud Run service

#--- Deploy Cloud Run service
    echo "Configuring Pub/Sub resources for classify_snn Cloud Run service..."
    gcloud pubsub topics create "${ps_output_topic}"
    gcloud pubsub topics create "${topic_bigquery_import}"
    gcloud pubsub topics create "${deadletter_topic_bigquery_import}"
    gcloud pubsub subscriptions create "${deadletter_subscription_bigquery_import}" --topic="${deadletter_topic_bigquery_import}"
    gcloud pubsub subscriptions create "${subscription_bigquery_import}" \
        --topic="${topic_bigquery_import}" \
        --bigquery-table="${PROJECT_ID}:${bq_dataset}.${supernnova_classifications_table}" \
        --use-table-schema \
        --dead-letter-topic="${deadletter_topic_bigquery_import}" \
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
