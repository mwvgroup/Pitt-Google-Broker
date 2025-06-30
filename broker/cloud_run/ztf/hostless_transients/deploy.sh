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
# get the environment variable
PROJECT_ID=$GOOGLE_CLOUD_PROJECT

MODULE_NAME="hostless-transients"  # lower case required by cloud run
ROUTE_RUN="/"  # url route that will trigger main.run()

define_GCP_resources() {
    local base_name="$1"
    local separator="$2"
    local testid_suffix=""

    if [ "$testid" != "False" ] && [ -n "$testid" ]; then
        testid_suffix="${separator}${testid}"
    fi
    echo "${base_name}${testid_suffix}"
}

#--- GCP resources used in this script
artifact_registry_repo=$(define_GCP_resources "${survey}-cloud-run-services" "-")
bq_dataset=$(define_GCP_resources "${survey}" "_")
bq_table="hostless_transients"
cr_module_name=$(define_GCP_resources "${survey}-${MODULE_NAME}" "-")  # lower case required by cloud run
ps_input_subscrip=$(define_GCP_resources "${survey}-${MODULE_NAME}" "-") # pub/sub subscription used to trigger cloud run module
ps_output_topic=$(define_GCP_resources "${survey}-${MODULE_NAME}" "-")
ps_trigger_topic=$(define_GCP_resources "${survey}-alerts" "-")
runinvoker_svcact="cloud-run-invoker@${PROJECT_ID}.iam.gserviceaccount.com"
# topics and subscriptions involved in writing data to BigQuery
ps_bigquery_subscription=$(define_GCP_resources "${survey}-${MODULE_NAME}-bigquery-import" "-")
ps_deadletter_subscription=$(define_GCP_resources "${survey}-${MODULE_NAME}-bigquery-import-deadletter" "-")
ps_deadletter_topic="${ps_deadletter_subscription}"

if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        echo
        echo "Deleting resources for ${MODULE_NAME} module..."
        gcloud pubsub topics delete "${ps_deadletter_topic}"
        gcloud pubsub topics delete "${ps_output_topic}"
        gcloud pubsub subscriptions delete "${ps_bigquery_subscription}"
        gcloud pubsub subscriptions delete "${ps_deadletter_subscription}"
        gcloud pubsub subscriptions delete "${ps_input_subscrip}"
        gcloud run services delete "${cr_module_name}" --region "${region}"
    fi
else
    echo "Configuring Pub/Sub resources..."
    gcloud pubsub topics create "${ps_deadletter_topic}"
    gcloud pubsub topics create "${ps_output_topic}"
    gcloud pubsub subscriptions create "${ps_deadletter_subscription}" --topic="${ps_deadletter_topic}"
    gcloud pubsub subscriptions create "${ps_bigquery_subscription}" \
        --topic="${ps_output_topic}" \
        --bigquery-table="${PROJECT_ID}:${bq_dataset}.${bq_table}" \
        --use-table-schema \
        --drop-unknown-fields \
        --dead-letter-topic="${ps_deadletter_topic}" \
        --max-delivery-attempts=5 \
        --dead-letter-topic-project="${PROJECT_ID}"
    # set IAM policies on public Pub/Sub resources
    if [ "$testid" = "False" ]; then
        user="allUsers"
        roleid="projects/${GOOGLE_CLOUD_PROJECT}/roles/userPublic"
        gcloud pubsub topics add-iam-policy-binding "${ps_output_topic}" --member="${user}" --role="${roleid}"
    fi

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
    # WARNING:  This is set to retry failed deliveries. If there is a bug in main.py this will
    # retry indefinitely, until the message is delete manually.
    gcloud pubsub subscriptions create "${ps_input_subscrip}" \
        --topic "${ps_trigger_topic}" \
        --topic-project "${PROJECT_ID}" \
        --message-filter='attributes.is_extragalactic_transient = "1"' \
        --ack-deadline=600 \
        --push-endpoint="${url}${ROUTE_RUN}" \
        --push-auth-service-account="${runinvoker_svcact}"
fi
