#! /bin/bash
# Create and configure GCP resources needed to run the nightly broker.

testid="${1:-test}"
# "False" uses production resources
# any other string will be appended to the names of all resources
teardown="${2:-False}"
# "True" tearsdown/deletes resources, else setup
survey="${3:-ztf}"
# name of the survey this broker instance will ingest
# 'ztf' or 'decat'
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
echo
echo "Continue?  [y/(n)]: "

read continue_with_setup
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
broker_bucket=$(define_GCP_resources "${PROJECT_ID}-${survey}-broker_files")
bq_dataset=$(define_GCP_resources "${survey}")
# topics and subscriptions involved in writing alert data to BigQuery
topic_bigquery_import=$(define_GCP_resources "${survey}-bigquery-import")
subscription_bigquery_import="${topic_bigquery_import}" # BigQuery subscription
deadletter_topic_bigquery_import=$(define_GCP_resources "${survey}-bigquery-import-deadletter")
deadletter_subscription_bigquery_import="${deadletter_topic_bigquery_import}"

alerts_table="alerts_${versiontag}"

# function used to create (or delete) GCP resources
manage_resources() {
    local mode="$1"  # setup or teardown
    local environment_type="production"

    if [ "$testid" != "False" ]; then
        environment_type="testing"
    fi

    if [ "$mode" = "setup" ]; then
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
        PUBSUB_SERVICE_ACCOUNT="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"
        gcloud pubsub topics add-iam-policy-binding ${deadletter_topic_bigquery_import} \
            --member="serviceAccount:$PUBSUB_SERVICE_ACCOUNT"\
            --role="roles/pubsub.publisher"
        gcloud pubsub subscriptions add-iam-policy-binding ${deadletter_subscription_bigquery_import} \
            --member="serviceAccount:$PUBSUB_SERVICE_ACCOUNT"\
            --role="roles/pubsub.subscriber"
    else
        if [ "$environment_type" = "testing" ]; then
            # delete testing resources
            python3 setup_gcp.py --survey="$survey" --testid="$testid" --teardown --confirmed --versiontag="${versiontag}"
            gcloud pubsub topics delete "${topic_bigquery_import}"
            gcloud pubsub topics delete "${deadletter_topic_bigquery_import}"
            gcloud pubsub subscriptions delete "${deadletter_subscription_bigquery_import}"
            gcloud pubsub subscriptions delete "${subscription_bigquery_import}"
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
./create_vms.sh "${broker_bucket}" "${testid}" "${teardown}" "${survey}" "${region}" "${zone}" "${use_authentication}"


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
cd .. && cd cloud_functions || exit

#--- Check cue response cloud function
cd check_cue_response || exit
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag" "$zone"

#--- classify with SNN cloud function
cd .. && cd classify_snn || exit
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag"

#--- alerts-lite cloud function
cd .. && cd lite || exit
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag"

#--- Pub/Sub -> Cloud Storage Avro cloud function
cd .. && cd ps_to_gcs || exit
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag" "$region"

#--- BigQuery storage cloud function
cd .. && cd store_BigQuery || exit
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag"

#--- tag alerts cloud function
cd .. && cd tag || exit
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag"

#--- return to setup_broker directory
cd .. && cd .. || exit
cd setup_broker || exit
