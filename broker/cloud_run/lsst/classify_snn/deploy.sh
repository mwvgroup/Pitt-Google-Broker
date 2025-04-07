#! /bin/bash
# Deploys or deletes broker Cloud Run service
# This script will not delete a Cloud Run service that is in production

# "False" uses production resources
# any other string will be appended to the names of all resources
testid="${1:-test}"
# "True" tearsdown/deletes resources, else setup
teardown="${2:-False}"
# name of the survey this broker instance will ingest
survey="${3:-lsst}"
region="${4:-us-central1}"
# get environment variables
PROJECT_ID=$GOOGLE_CLOUD_PROJECT
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")

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
artifact_registry_repo=$(define_GCP_resources "${survey}-cloud-run-services")
deadletter_topic_bigquery_import_snn=$(define_GCP_resources "${survey}-bigquery-import-SuperNNova-deadletter")
deadletter_topic_bigquery_import_classifications=$(define_GCP_resources "${survey}-bigquery-import-classifications-deadletter")
deadletter_subscription_bigquery_import_snn="${deadletter_topic_bigquery_import_snn}"
deadletter_subscription_bigquery_import_classifications="${deadletter_topic_bigquery_import_classifications}"
topic_bigquery_import_snn=$(define_GCP_resources "${survey}-bigquery-import-SuperNNova")
topic_bigquery_import_classifications=$(define_GCP_resources "${survey}-bigquery-import-classifications")
subscription_bigquery_import_snn="${topic_bigquery_import_snn}" # BigQuery subscription
subscription_bigquery_import_classifications="${topic_bigquery_import_classifications}" # BigQuery subscription
trigger_topic=$(define_GCP_resources "${survey}-alerts")
ps_input_subscrip="${trigger_topic}" # pub/sub subscription used to trigger cloud run module
ps_output_topic=$(define_GCP_resources "${survey}-SuperNNova")

# additional GCP resources & variables used in this script
bq_dataset=$(define_GCP_resources "${survey}")
supernnova_table="SuperNNova"
classifications_table="classifications"
cr_module_name=$(define_GCP_resources "${survey}-${MODULE_NAME}")  # lower case required by Cloud Run
runinvoker_svcact="cloud-run-invoker@${PROJECT_ID}.iam.gserviceaccount.com"

if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        gcloud pubsub topics delete "${ps_output_topic}"
        gcloud pubsub topics delete "${topic_bigquery_import_snn}"
        gcloud pubsub topics delete "${topic_bigquery_import_classifications}"
        gcloud pubsub topics delete "${deadletter_topic_bigquery_import_snn}"
        gcloud pubsub topics delete "${deadletter_topic_bigquery_import_classifications}"
        gcloud pubsub subscriptions delete "${ps_input_subscrip}"
        gcloud pubsub subscriptions delete "${subscription_bigquery_import_snn}"
        gcloud pubsub subscriptions delete "${subscription_bigquery_import_classifications}"
        gcloud pubsub subscriptions delete "${deadletter_subscription_bigquery_import_snn}"
        gcloud pubsub subscriptions delete "${deadletter_subscription_bigquery_import_classifications}"
        gcloud run services delete "${cr_module_name}" --region "${region}"
    fi

else # Deploy the Cloud Run service

#--- Deploy Cloud Run service
    echo "Configuring Pub/Sub resources for classify_snn Cloud Run service..."
    gcloud pubsub topics create "${ps_output_topic}"
    gcloud pubsub topics create "${deadletter_topic_bigquery_import_snn}"
    gcloud pubsub topics create "${deadletter_topic_bigquery_import_classifications}"
    gcloud pubsub topics create "${topic_bigquery_import_snn}"
    gcloud pubsub topics create "${topic_bigquery_import_classifications}"
    gcloud pubsub subscriptions create "${deadletter_subscription_bigquery_import_snn}" --topic="${deadletter_topic_bigquery_import_snn}"
    gcloud pubsub subscriptions create "${deadletter_subscription_bigquery_import_classifications}" --topic="${deadletter_topic_bigquery_import_classifications}"

    # in order to create BigQuery subscriptions, ensure that the following service account:
    # service-<project number>@gcp-sa-pubsub.iam.gserviceaccount.com" has the
    # bigquery.dataEditor role for each table
    PUBSUB_SERVICE_ACCOUNT="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"
    roleid="roles/bigquery.dataEditor"
    bq add-iam-policy-binding \
        --member="serviceAccount:${PUBSUB_SERVICE_ACCOUNT}" \
        --role="${roleid}" \
        --table=true "${PROJECT_ID}:${bq_dataset}.${supernnova_table}"
    gcloud pubsub subscriptions create "${subscription_bigquery_import_snn}" \
        --topic="${topic_bigquery_import_snn}" \
        --bigquery-table="${PROJECT_ID}:${bq_dataset}.${supernnova_table}" \
        --use-table-schema \
        --dead-letter-topic="${deadletter_topic_bigquery_import_snn}" \
        --max-delivery-attempts=5 \
        --dead-letter-topic-project="${PROJECT_ID}"
    gcloud pubsub subscriptions create "${subscription_bigquery_import_classifications}" \
        --topic="${topic_bigquery_import_classifications}" \
        --bigquery-table="${PROJECT_ID}:${bq_dataset}.${classifications_table}" \
        --use-table-schema \
        --dead-letter-topic="${deadletter_topic_bigquery_import_classifications}" \
        --max-delivery-attempts=5 \
        --dead-letter-topic-project="${PROJECT_ID}"

    # this allows dead-lettered messages to be forwarded from the BigQuery subscription to the dead letter topic
    # and it allows dead-lettered messages to be published to the dead letter topic.
    gcloud pubsub topics add-iam-policy-binding "${deadletter_topic_bigquery_import_snn}" \
        --member="serviceAccount:$PUBSUB_SERVICE_ACCOUNT"\
        --role="roles/pubsub.publisher"
    gcloud pubsub subscriptions add-iam-policy-binding "${subscription_bigquery_import_snn}" \
        --member="serviceAccount:$PUBSUB_SERVICE_ACCOUNT"\
        --role="roles/pubsub.subscriber"
    gcloud pubsub topics add-iam-policy-binding "${deadletter_topic_bigquery_import_classifications}" \
        --member="serviceAccount:$PUBSUB_SERVICE_ACCOUNT"\
        --role="roles/pubsub.publisher"
    gcloud pubsub subscriptions add-iam-policy-binding "${subscription_bigquery_import_classifications}" \
        --member="serviceAccount:$PUBSUB_SERVICE_ACCOUNT"\
        --role="roles/pubsub.subscriber"

    echo "Creating container image and deploying to Cloud Run..."
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
