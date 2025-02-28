#! /bin/bash
# Create and configure GCP resources needed to run the nightly broker.

# "False" uses production resources
# any other string will be appended to the names of all resources
testid="${1:-test}"
# "True" tearsdown/deletes resources, else setup
teardown="${2:-False}"
# name of the survey this broker instance will ingest
survey="${3:-lsst}"
schema_version="${4:-7.4}"
versiontag=v$(echo "${schema_version}" | tr . _) # 7.4 -> v7_4
region="${5:-us-central1}"
zone="${region}-a"  # just use zone "a" instead of adding another script arg
# get environment variables
PROJECT_ID=$GOOGLE_CLOUD_PROJECT
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

#--- GCP resources used directly in this script
artifact_registry_repo=$(define_GCP_resources "${survey}-cloud-run-services")
broker_bucket=$(define_GCP_resources "${PROJECT_ID}-${survey}-broker_files")
bq_dataset=$(define_GCP_resources "${survey}")
topic_alerts_raw=$(define_GCP_resources "${survey}-alerts_raw")
topic_alerts=$(define_GCP_resources "${survey}-alerts")
subscription_reservoir=$(define_GCP_resources "${survey}-alerts-reservoir")
# topics and subscriptions involved in writing alert data to BigQuery
topic_bigquery_import=$(define_GCP_resources "${survey}-bigquery-import")
subscription_bigquery_import=$(define_GCP_resources "${survey}-bigquery-import-${versiontag}") # BigQuery subscription
deadletter_topic_bigquery_import=$(define_GCP_resources "${survey}-bigquery-import-deadletter-${versiontag}")
deadletter_subscription_bigquery_import="${deadletter_topic_bigquery_import}"

alerts_table="alerts_${versiontag}"
supernnova_classifications_table="SuperNNova"

# function used to create (or delete) GCP resources
manage_resources() {
    local mode="$1"  # setup or teardown
    local environment_type="production"

    if [ "$testid" != "False" ]; then
        environment_type="testing"
    fi

    if [ "$mode" = "setup" ]; then
        # create BigQuery dataset and table
        bq --location="${region}" mk --dataset "${bq_dataset}"

        cd templates || exit 5
        bq mk --table "${PROJECT_ID}:${bq_dataset}.${alerts_table}" "bq_${survey}_${alerts_table}_schema.json" || exit 5
        bq update --description "Alert data from LSST. This table is an archive of the lsst-alerts Pub/Sub stream. It has the same schema as the original alert bytes, including nested and repeated fields." "${PROJECT_ID}:${bq_dataset}.${alerts_table}"
        bq mk --table "${PROJECT_ID}:${bq_dataset}.${supernnova_classifications_table}" "bq_${survey}_${supernnova_classifications_table}_schema.json" || exit 5
        bq update --description "Binary classification results from SuperNNova." "${PROJECT_ID}:${bq_dataset}.${supernnova_classifications_table}"

        cd .. || exit 5

        # create broker bucket and upload files
        echo
        echo "Creating broker_bucket and uploading files..."
        gsutil mb -b on -l "${region}" "gs://${broker_bucket}"
        ./upload_broker_bucket.sh "${broker_bucket}"

        # create a firewall rule to open the port used by Kafka/Rubin LSST
        # on any instance with the flag --tags=tcpport9094
        echo
        echo "Configuring Rubin/Kafka firewall rule..."
        firewallrule="tcpport9094"
        gcloud compute firewall-rules create "${firewallrule}" \
            --allow=tcp:9094 \
            --description="Allow incoming traffic on TCP port 9094" \
            --direction=INGRESS \
            --enable-logging

        # create Pub/Sub
        echo "Configuring Pub/Sub resources..."
        gcloud pubsub topics create "${topic_alerts_raw}"
        gcloud pubsub topics create "${topic_alerts}"
        gcloud pubsub topics create "${topic_bigquery_import}"
        gcloud pubsub topics create "${deadletter_topic_bigquery_import}"
        gcloud pubsub subscriptions create "${subscription_reservoir}" --topic="${topic_alerts}"
        gcloud pubsub subscriptions create "${deadletter_subscription_bigquery_import}" --topic="${deadletter_topic_bigquery_import}"
        # in order to create BigQuery subscriptions, ensure that the following service account:
        # service-<project number>@gcp-sa-pubsub.iam.gserviceaccount.com" has the
        # bigquery.dataEditor role for each table
        PUBSUB_SERVICE_ACCOUNT="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"
        roleid="roles/bigquery.dataEditor"
        bq add-iam-policy-binding \
            --member="serviceAccount:${PUBSUB_SERVICE_ACCOUNT}" \
            --role="${roleid}" \
            --table=true "${PROJECT_ID}:${bq_dataset}.${alerts_table}"
        gcloud pubsub subscriptions create "${subscription_bigquery_import}" \
            --topic="${topic_bigquery_import}" \
            --bigquery-table="${PROJECT_ID}:${bq_dataset}.${alerts_table}" \
            --use-table-schema \
            --dead-letter-topic="${deadletter_topic_bigquery_import}" \
            --max-delivery-attempts=5 \
            --dead-letter-topic-project="${PROJECT_ID}" \
            --message-filter='attributes.schema_version = "'"${versiontag}"'"'

        # set IAM policies on resources
        if [ "$testid" = "False" ]; then
            user="allUsers"
            roleid="projects/${GOOGLE_CLOUD_PROJECT}/roles/userPublic"
            gcloud pubsub topics add-iam-policy-binding "${topic_alerts}" --member="${user}" --role="${roleid}"
        fi
        # this allows dead-lettered messages to be forwarded from the BigQuery subscription to the dead letter topic
        # and it allows dead-lettered messages to be published to the dead letter topic.
        gcloud pubsub topics add-iam-policy-binding "${deadletter_topic_bigquery_import}" \
            --member="serviceAccount:$PUBSUB_SERVICE_ACCOUNT"\
            --role="roles/pubsub.publisher"
        gcloud pubsub subscriptions add-iam-policy-binding "${subscription_bigquery_import}" \
            --member="serviceAccount:$PUBSUB_SERVICE_ACCOUNT"\
            --role="roles/pubsub.subscriber"

        #--- Create Artifact Registry Repository
        echo
        echo "Configuring Artifact Registry..."
        gcloud artifacts repositories create "${artifact_registry_repo}" --repository-format=docker \
            --location="${region}" --description="Docker repository for Cloud Run services" \
            --project="${PROJECT_ID}"

    else
        if [ "$environment_type" = "testing" ]; then
            o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
            gsutil -m -o "${o}" rm -r "gs://${broker_bucket}"
            bq rm -r -f "${PROJECT_ID}:${bq_dataset}"
            gcloud pubsub topics delete "${topic_alerts_raw}"
            gcloud pubsub topics delete "${topic_alerts}"
            gcloud pubsub topics delete "${topic_bigquery_import}"
            gcloud pubsub topics delete "${deadletter_topic_bigquery_import}"
            gcloud pubsub subscriptions delete "${subscription_reservoir}"
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

#--- Create VM instances
echo
echo "Configuring VMs..."
./create_vm.sh "${broker_bucket}" "${testid}" "${teardown}" "${survey}" "${zone}" "${firewallrule}"

#--- Deploy Cloud Run services
echo
echo "Configuring Cloud Run services..."
cd .. && cd .. || exit
cd cloud_run && cd lsst || exit

#--- ps_to_storage Cloud Run service
cd ps_to_storage || exit
./deploy.sh "$testid" "$teardown" "$survey" "$region"

#--- classify_snn Cloud Run service
cd .. && cd classify_snn || exit
./deploy.sh "$testid" "$teardown" "$survey" "$region"

#--- return to setup_broker directory
cd .. && cd .. || exit
cd .. && cd setup_broker || exit
