#! /bin/bash
# Create and configure GCP resources needed to run the broker.

# "False" uses production resources
# any other string will be appended to the names of all resources
testid="${1:-test}"
# "True" tearsdown/deletes resources, else setup
teardown="${2:-False}"
# name of the survey this broker instance will ingest
survey="${3:-swift}"
schema_version="${4:-4.5.0}"
versiontag=v$(echo "${schema_version}" | tr . _) # 1.0.0 -> v1_0_0
region="${5:-us-central1}"
zone="${region}-a"  # just use zone "a" instead of adding another script arg

PROJECT_ID=$GOOGLE_CLOUD_PROJECT # get the environment variable
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")

#--- Make the user confirm the settings
echo
echo "setup_broker.sh will run with the following configs: "
echo
echo "GOOGLE_CLOUD_PROJECT = ${PROJECT_ID}"
echo "survey = ${survey}"
echo "testid = ${testid}"
echo "schema_version = ${schema_version}"
echo "teardown = ${teardown}"
echo
echo "Continue?  [y/(n)]: "

read -r continue_with_setup
continue_with_setup="${continue_with_setup:-n}"
if [ "$continue_with_setup" != "y" ]; then
    echo "Exiting setup."
    echo
    exit
fi

define_GCP_resources() {
    local base_name="$1"
    local separator="$2"
    local testid_suffix=""

    if [ "$testid" != "False" ] && [ -n "$testid" ]; then
        testid_suffix="${separator}${testid}"
    fi

    echo "${base_name}${testid_suffix}"
}

#--- GCP resources used directly in this script
alerts_table="alerts_${versiontag}"
artifact_registry_repo=$(define_GCP_resources "${survey}-cloud-run-services" "-")
bq_dataset=$(define_GCP_resources "${survey}" "_")
broker_bucket=$(define_GCP_resources "${PROJECT_ID}-${survey}-broker_files" "-")
subscription_alerts_reservoir=$(define_GCP_resources "${survey}-alerts-json-reservoir" "-")
topic_alerts_json=$(define_GCP_resources "${survey}-alerts-json" "-")
topic_alerts_raw=$(define_GCP_resources "${survey}-alerts_raw" "-")
# topics and subscriptions involved in writing alert data to BigQuery
deadletter_topic_bigquery_import=$(define_GCP_resources "${survey}-bigquery-import-deadletter" "-")
deadletter_subscription_bigquery_import="${deadletter_topic_bigquery_import}"
subscription_bigquery_import=$(define_GCP_resources "${survey}-bigquery-import-${versiontag}" "-") # BigQuery subscription

# function used to create (or delete) GCP resources
manage_resources() {
    local mode="$1"  # setup or teardown
    local environment_type="production"

    if [ "$testid" != "False" ]; then
        environment_type="testing"
    fi

    if [ "$mode" = "setup" ]; then
        #--- Create BigQuery dataset and table
        echo
        echo "Creating BigQuery dataset and table..."
        if ! bq ls "${PROJECT_ID}:${bq_dataset}" >/dev/null 2>&1; then
            bq --location="${region}" mk --dataset "${bq_dataset}"
        else
            echo "${bq_dataset} already exists."
        fi
        (cd templates && bq mk --table "${PROJECT_ID}:${bq_dataset}.${alerts_table}" "bq_${survey}_${alerts_table}_schema.json") || exit 5
        (cd templates && bq update --source "bq_${survey}_policy.json" "${PROJECT_ID}:${bq_dataset}") || exit 5
        bq update --description "Alert data from Swift/BAT-GUANO. This table is an archive of the swift-alerts Pub/Sub stream. It has the same schema as the original alert bytes, including repeated fields." "${PROJECT_ID}:${bq_dataset}.${alerts_table}"

        #--- Create GCS buckets
        echo
        echo "Creating broker_bucket and uploading files..."
        if ! gsutil ls -b "gs://${broker_bucket}" >/dev/null 2>&1; then
            gsutil mb -b on -l "${region}" "gs://${broker_bucket}"
        else
            echo "${broker_bucket} already exists."
        fi
        ./upload_broker_bucket.sh "${broker_bucket}" # upload files

        #--- Assign IAM roles to the Pub/Sub service account
        echo
        echo "Assigning IAM roles to the Pub/Sub service account..."
        roleid="roles/bigquery.dataEditor"
        service_account="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"
        gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
            --member="serviceAccount:${service_account}" \
            --role="${roleid}"

        #--- Create Pub/Sub topics and subscriptions
        echo
        echo "Configuring Pub/Sub resources..."
        gcloud pubsub topics create "${topic_alerts_json}"
        gcloud pubsub topics create "${topic_alerts_raw}"
        gcloud pubsub topics create "${deadletter_topic_bigquery_import}"
        gcloud pubsub subscriptions create "${deadletter_subscription_bigquery_import}" --topic="${deadletter_topic_bigquery_import}"
        gcloud pubsub subscriptions create "${subscription_alerts_reservoir}" --topic="${topic_alerts_json}"
        gcloud pubsub subscriptions create "${subscription_bigquery_import}" \
            --topic="${topic_alerts_json}" \
            --bigquery-table="${PROJECT_ID}:${bq_dataset}.${alerts_table}" \
            --use-table-schema \
            --drop-unknown-fields \
            --dead-letter-topic="${deadletter_topic_bigquery_import}" \
            --max-delivery-attempts=5 \
            --dead-letter-topic-project="${PROJECT_ID}"

        # set IAM policies on resources
        user="allUsers"
        roleid="projects/${GOOGLE_CLOUD_PROJECT}/roles/userPublic"
        gcloud pubsub topics add-iam-policy-binding "${topic_alerts_json}" --member="${user}" --role="${roleid}"

        #--- Create Artifact Registry Repository
        echo
        echo "Configuring Artifact Registry..."
        gcloud artifacts repositories create "${artifact_registry_repo}" --repository-format=docker \
            --location="${region}" --description="Docker repository for Cloud Run services" \
            --project="${PROJECT_ID}"

    else
        if [ "$environment_type" = "testing" ]; then
            # delete testing resources
            # Note: create_vm.sh will delete the VM instance
            o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
            gsutil -m -o "${o}" rm -r "gs://${broker_bucket}"
            bq rm -r -f "${PROJECT_ID}:${bq_dataset}"
            gcloud pubsub topics delete "${topic_alerts_json}"
            gcloud pubsub topics delete "${topic_alerts_raw}"
            gcloud pubsub topics delete "${deadletter_topic_bigquery_import}"
            gcloud pubsub subscriptions delete "${subscription_alerts_reservoir}"
            gcloud pubsub subscriptions delete "${deadletter_subscription_bigquery_import}"
            gcloud pubsub subscriptions delete "${subscription_bigquery_import}"
            gcloud artifacts repositories delete "${artifact_registry_repo}" --location="${region}"
        else
            echo 'ERROR: No testid supplied.'
            echo 'To avoid accidents, this script will not delete production resources.'
            echo 'If that is your intention, you must delete them manually.'
            echo 'Otherwise, please supply a testid.'
            exit 1
        fi
    fi
}

#--- Create (or delete) BigQuery, GCS, Pub/Sub resources
echo
echo "Configuring BigQuery, GCS, Pub/Sub resources..."
if [ "$teardown" = "True" ]; then
    manage_resources "teardown"
else
    manage_resources "setup"
fi

#--- Create (or delete) VM instance
echo
echo "Configuring VM..."
./create_vm.sh "${broker_bucket}" "${testid}" "${teardown}" "${survey}" "${zone}" "${PROJECT_ID}"

#--- Deploy Cloud Run services
echo
echo "Configuring Cloud Run services..."
(
    # navigate to the correct directory
    cd .. && cd .. && cd cloud_run && cd swift

    #--- ps_to_storage Cloud Run service
    cd ps_to_storage
    ./deploy.sh "$testid" "$teardown" "$survey" "$region"
)
