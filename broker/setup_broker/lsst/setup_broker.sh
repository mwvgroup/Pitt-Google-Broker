#! /bin/bash
# Create and configure GCP resources needed to run the nightly broker.

# "False" uses production resources
# any other string will be appended to the names of all resources
testid="${1:-test}"
# "True" tearsdown/deletes resources, else setup
teardown="${2:-False}"
# name of the survey this broker instance will ingest
survey="${3:-lsst}"
schema_version="${4:-9.0}"
versiontag=v$(echo "${schema_version}" | tr . _) # 9.0 -> v9_0
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

define_GCP_resources() {
    local base_name="$1"
    local separator="${2:--}"
    local testid_suffix=""

    if [ "$testid" != "False" ] && [ -n "$testid" ]; then
        testid_suffix="${separator}${testid}"
    fi
    echo "${base_name}${testid_suffix}"
}

#--- GCP resources used directly in this script
artifact_registry_repo=$(define_GCP_resources "${survey}-cloud-run-services")
bq_dataset=$(define_GCP_resources "${survey}" "_")
bq_table_alerts="alerts_${versiontag}"
bq_table_supernnova="supernnova"
bq_table_upsilon="upsilon"
bq_table_variability="variability"
gcs_broker_bucket=$(define_GCP_resources "${PROJECT_ID}-${survey}-broker_files")
ps_subscription_reservoir=$(define_GCP_resources "${survey}-alerts-reservoir")
ps_topic_alerts_raw=$(define_GCP_resources "${survey}-alerts_raw")
ps_topic_alerts=$(define_GCP_resources "${survey}-alerts")
ps_topic_alerts_json=$(define_GCP_resources "${survey}-alerts-json")
ps_topic_alerts_lite=$(define_GCP_resources "${survey}-lite")
# topics and subscriptions involved in writing alert data to BigQuery
ps_bigquery_subscription=$(define_GCP_resources "${survey}-bigquery-import-${versiontag}")
ps_deadletter_subscription=$(define_GCP_resources "${survey}-deadletter")
ps_deadletter_topic="${ps_deadletter_subscription}"

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
            # grant public access to the dataset; for more information, see:
            # https://cloud.google.com/bigquery/docs/control-access-to-resources-iam#grant_access_to_a_dataset
            (cd templates && bq update --source "bq_${survey}_policy.json" "${PROJECT_ID}:${bq_dataset}") || exit 5
        else
            echo "${bq_dataset} already exists."
        fi
        (cd templates && bq mk --table --clustering_fields=healpix9,healpix19,healpix29 --time_partitioning_field=kafkaPublishTimestamp --time_partitioning_type=DAY "${PROJECT_ID}:${bq_dataset}.${bq_table_alerts}" "bq_${survey}_${bq_table_alerts}_schema.json") || exit 5
        (cd templates && bq mk --table --time_partitioning_field=kafkaPublishTimestamp --time_partitioning_type=DAY "${PROJECT_ID}:${bq_dataset}.${bq_table_supernnova}" "bq_${survey}_${bq_table_supernnova}_schema.json") || exit 5
        (cd templates && bq mk --table --time_partitioning_field=kafkaPublishTimestamp --time_partitioning_type=DAY "${PROJECT_ID}:${bq_dataset}.${bq_table_variability}" "bq_${survey}_${bq_table_variability}_schema.json") || exit 5
        (cd templates && bq mk --table --time_partitioning_field=kafkaPublishTimestamp --time_partitioning_type=DAY "${PROJECT_ID}:${bq_dataset}.${bq_table_upsilon}" "bq_${survey}_${bq_table_upsilon}_schema.json") || exit 5
        bq update --description "Alert data from LSST. This table is an archive of the lsst-alerts Pub/Sub stream. It has the same schema as the original alert bytes, including nested and repeated fields." "${PROJECT_ID}:${bq_dataset}.${bq_table_alerts}"
        bq update --description "Binary classification results from SuperNNova." "${PROJECT_ID}:${bq_dataset}.${bq_table_supernnova}"

        #--- Create GCS bucket
        echo
        echo "Creating broker_bucket and uploading files..."
        if ! gsutil ls -b "gs://${gcs_broker_bucket}" >/dev/null 2>&1; then
            gsutil mb -b on -l "${region}" "gs://${gcs_broker_bucket}"
        else
            echo "${gcs_broker_bucket} already exists."
        fi
        ./upload_broker_bucket.sh "${gcs_broker_bucket}"

        #--- Assign IAM roles to the Pub/Sub service account
        echo
        echo "Assigning IAM roles to the Pub/Sub service account..."
        roleid="roles/bigquery.dataEditor"
        service_account="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"
        gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
            --member="serviceAccount:${service_account}" \
            --role="${roleid}"

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

        #--- Create Pub/Sub
        echo "Configuring Pub/Sub resources..."
        gcloud pubsub topics create "${ps_topic_alerts_raw}"
        gcloud pubsub topics create "${ps_topic_alerts}"
        gcloud pubsub topics create "${ps_topic_alerts_json}"
        gcloud pubsub topics create "${ps_topic_alerts_lite}"
        gcloud pubsub topics create "${ps_deadletter_topic}"
        gcloud pubsub subscriptions create "${ps_deadletter_subscription}" \
            --topic="${ps_deadletter_topic}"
        gcloud pubsub subscriptions create "${ps_subscription_reservoir}" \
            --topic="${ps_topic_alerts}"
        gcloud pubsub subscriptions create "${ps_bigquery_subscription}" \
            --topic="${ps_topic_alerts_json}" \
            --bigquery-table="${PROJECT_ID}:${bq_dataset}.${bq_table_alerts}" \
            --use-table-schema \
            --drop-unknown-fields \
            --dead-letter-topic="${ps_deadletter_topic}" \
            --max-delivery-attempts=5 \
            --dead-letter-topic-project="${PROJECT_ID}" \
            --message-filter='attributes.schema_version = "'"${versiontag}"'"' \
            --message-transforms-file=templates/ps_lsst_add_top_level_fields_smt.yaml
        # set IAM policies on public Pub/Sub resources
        if [ "$testid" = "False" ]; then
            user="allUsers"
            roleid="roles/pubsub.subscriber"
            gcloud pubsub topics add-iam-policy-binding "${ps_topic_alerts}" --member="${user}" --role="${roleid}"
            gcloud pubsub topics add-iam-policy-binding "${ps_topic_alerts_json}" --member="${user}" --role="${roleid}"
            gcloud pubsub topics add-iam-policy-binding "${ps_topic_alerts_lite}" --member="${user}" --role="${roleid}"
            gcloud pubsub topics add-iam-policy-binding "${ps_deadletter_topic}" \
                --member="serviceAccount:${service_account}" \
                --role="roles/pubsub.publisher"
            gcloud pubsub subscriptions add-iam-policy-binding "${ps_bigquery_subscription}" \
                --member="serviceAccount:${service_account}" \
                --role="roles/pubsub.subscriber"
        fi

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
            gsutil -m -o "${o}" rm -r "gs://${gcs_broker_bucket}"
            bq rm -r -f "${PROJECT_ID}:${bq_dataset}"
            gcloud pubsub topics delete "${ps_topic_alerts_raw}"
            gcloud pubsub topics delete "${ps_topic_alerts}"
            gcloud pubsub topics delete "${ps_topic_alerts_json}"
            gcloud pubsub topics delete "${ps_deadletter_topic}"
            gcloud pubsub topics delete "${ps_topic_alerts_lite}"
            gcloud pubsub subscriptions delete "${ps_subscription_reservoir}"
            gcloud pubsub subscriptions delete "${ps_deadletter_subscription}"
            gcloud pubsub subscriptions delete "${ps_bigquery_subscription}"
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
echo "Configuring VMs..."
./create_vm.sh "${gcs_broker_bucket}" "${testid}" "${teardown}" "${survey}" "${zone}" "${firewallrule}"

#--- Create (or delete) Cloud Run services
echo
echo "Configuring Cloud Run services..."
(
    # navigate to the Cloud Run directory for LSST
    cd .. && cd .. && cd cloud_run && cd lsst

    #--- alerts-to-storage Cloud Run service
    cd ps_to_storage
    ./deploy.sh "${testid}" "${teardown}" "${survey}" "${region}"

    #--- supernnova Cloud Run service
    cd .. && cd classify_snn
    ./deploy.sh "${testid}" "${teardown}" "${survey}" "${region}"

    #--- variability Cloud Run service
    cd .. && cd variability
    ./deploy.sh "${testid}" "${teardown}" "${survey}" "${region}"

    #--- upsilon Cloud Run service
    cd .. && cd classify_upsilon
    ./deploy.sh "${testid}" "${teardown}" "${survey}" "${region}"
) || exit
