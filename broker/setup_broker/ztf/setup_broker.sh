#! /bin/bash
# Create and configure GCP resources needed to run the nightly broker.

# "False" uses production resources
# any other string will be appended to the names of all resources
testid="${1:-test}"
# "True" tearsdown/deletes resources, else setup
teardown="${2:-False}"
# name of the survey this broker instance will ingest
# 'ztf' or 'decat'
survey="${3:-ztf}"
schema_version="${4:-4.02}"
versiontag=v$(echo "${schema_version}" | tr . _)  # 4.02 -> v4_02
use_authentication="${5:-false}"  # whether the consumer VM should use an authenticated connection
region="${6:-us-central1}"
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
echo "teardown = ${teardown}"
echo "schema_version = ${schema_version}"
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
bq_dataset_value_added=$(define_GCP_resources "${survey}_value_added" "_")
broker_bucket=$(define_GCP_resources "${PROJECT_ID}-${survey}-broker_files")
# topics and subscriptions involved in writing alert data to BigQuery
topic_bigquery_import=$(define_GCP_resources "${survey}-bigquery-import")
subscription_bigquery_import="${topic_bigquery_import}" # BigQuery subscription
deadletter_topic_bigquery_import=$(define_GCP_resources "${survey}-bigquery-import-deadletter")
deadletter_subscription_bigquery_import="${deadletter_topic_bigquery_import}"

alerts_table="alerts_${versiontag}"
variability_table="variability"
upsilon_table="upsilon"
hostless_table="hostless"
euclid_table="euclid_crossmatch"

# function used to create (or delete) GCP resources
manage_resources() {
    local mode="$1"  # setup or teardown
    local environment_type="production"

    if [ "$testid" != "False" ]; then
        environment_type="testing"
    fi

    if [ "$mode" = "setup" ]; then
        bq --location="${region}" mk --dataset "${bq_dataset_value_added}"
        (cd templates && bq mk --table "${PROJECT_ID}:${bq_dataset_value_added}.${variability_table}" "bq_${survey}_value_added_${variability_table}_schema.json") || exit 5
        (cd templates && bq mk --table "${PROJECT_ID}:${bq_dataset}.${upsilon_table}" "bq_${survey}_${upsilon_table}_schema.json") || exit 5
        (cd templates && bq mk --table "${PROJECT_ID}:${bq_dataset}.${hostless_table}" "bq_${survey}_${hostless_table}_schema.json") || exit 5
        (cd templates && bq mk --table "${PROJECT_ID}:${bq_dataset}.${euclid_table}" "bq_${survey}_${euclid_table}_schema.json") || exit 5
        # setup resources
        python3 setup_gcp.py --survey="$survey" --testid="$testid" --confirmed --region="${region}" --versiontag="${versiontag}"
        # the following resources are not created/deleted by setup_gcp.py
        # will eventually migrate away from using setup_gcp.py altogether
        gcloud pubsub topics create "${topic_bigquery_import}"
        gcloud pubsub topics create "${deadletter_topic_bigquery_import}"
        gcloud pubsub subscriptions create "${deadletter_subscription_bigquery_import}" --topic="${deadletter_topic_bigquery_import}"
        # in order to create BigQuery subscriptions, ensure that the following service account:
        # service-<project number>@gcp-sa-pubsub.iam.gserviceaccount.com" has the
        # bigquery.dataEditor role for each table
        gcloud pubsub subscriptions create "${subscription_bigquery_import}" \
            --topic="${topic_bigquery_import}" \
            --bigquery-table="${PROJECT_ID}:${bq_dataset}.${alerts_table}" \
            --use-table-schema \
            --drop-unknown-fields \
            --dead-letter-topic="${deadletter_topic_bigquery_import}" \
            --max-delivery-attempts=5 \
            --dead-letter-topic-project="${PROJECT_ID}"
        # assign required permissions to the Pub/Sub service account
        # this allows dead-lettered messages to be forwarded from the BigQuery subscription to the dead letter topic
        # and it allows dead-lettered messages to be published to the dead letter topic.
        PUBSUB_SERVICE_ACCOUNT="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"
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
            # delete testing resources
            bq rm -r -f "${PROJECT_ID}:${bq_dataset_value_added}"
            python3 setup_gcp.py --survey="$survey" --testid="$testid" --teardown --confirmed --versiontag="${versiontag}"
            gcloud pubsub topics delete "${topic_bigquery_import}"
            gcloud pubsub topics delete "${deadletter_topic_bigquery_import}"
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

#--- finish setting up buckets and dataset
if [ "$teardown" != "True" ]; then
    ./upload_broker_bucket.sh "$broker_bucket"

    bq add-iam-policy-binding \
        --member="allUsers" \
        --role="roles/bigquery.metadataViewer" \
        "${bq_dataset}"
    bq add-iam-policy-binding \
        --member="allUsers" \
        --role="roles/bigquery.dataViewer" \
        "${bq_dataset}"
fi


#--- Create VM instances
echo
echo "Configuring VMs..."
./create_vm.sh "${broker_bucket}" "${testid}" "${teardown}" "${survey}" "${region}" "${zone}" "${use_authentication}"


#--- Create the cron jobs that check the VM status
echo
echo "Setting up Cloud Scheduler cron jobs"
./create_cron_jobs.sh "$testid" "$teardown" "$survey" "$region"


if [ "$teardown" != "True" ]; then

#--- Create a firewall rule to open the port used by Kafka/ZTF
# on any instance with the flag --tags=ztfport
    echo
    echo "Configuring ZTF/Kafka firewall rule..."
    gcloud compute firewall-rules create 'ztfport' \
        --allow=tcp:9094 \
        --description="Allow incoming traffic on TCP port 9094" \
        --direction=INGRESS \
        --enable-logging
fi

#--- Deploy Cloud Functions
echo
echo "Configuring Cloud Functions..."
(
    #--- navigate to the Cloud Run Functions directory for ZTF
    cd .. && cd .. && cd cloud_functions && cd ztf

    #--- alerts-lite cloud function
    cd lite
    ./deploy.sh "$testid" "$teardown" "$survey" "$versiontag"

    #--- Pub/Sub -> Cloud Storage Avro cloud function
    cd .. && cd ps_to_gcs
    ./deploy.sh "$testid" "$teardown" "$survey" "$versiontag" "$region"

    #--- BigQuery storage cloud function
    cd .. && cd store_BigQuery
    ./deploy.sh "$testid" "$teardown" "$survey" "$versiontag"

    #--- tag alerts cloud function
    cd .. && cd tag
    ./deploy.sh "$testid" "$teardown" "$survey" "$versiontag"

    # navigate to the Cloud Run directory for ZTF
    cd .. && cd .. && cd .. && cd cloud_run && cd ztf

    #--- variability Cloud Run service
    cd variability
    ./deploy.sh "$testid" "$teardown" "$survey" "$region"

    #--- upsilon Cloud Run service
    cd .. && cd classify_upsilon
    ./deploy.sh "$testid" "$teardown" "$survey" "$region"

    #--- supernnova Cloud Run service
    cd .. && cd classify_snn
    ./deploy.sh "$testid" "$teardown" "$survey" "$region"

    #--- hostless-transients Cloud Run service
    cd .. && cd hostless_transients
    ./deploy.sh "$testid" "$teardown" "$survey" "$region"

    cd .. && cd euclid
    ./deploy.sh "$testid" "$teardown" "$survey" "$region"

) || exit
