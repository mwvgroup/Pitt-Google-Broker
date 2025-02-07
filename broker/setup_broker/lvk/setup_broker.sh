#! /bin/bash
# Create and configure GCP resources needed to run the broker.

# "False" uses production resources
# any other string will be appended to the names of all resources
testid="${1:-test}"
# "True" tearsdown/deletes resources, else setup
teardown="${2:-False}"
# name of the survey this broker instance will ingest
survey="${3:-lvk}"
schema_version="${4:-1.0}"
versiontag=v$(echo "${schema_version}" | tr . _) # 1.0 -> v1_0
region="${5:-us-central1}"
zone="${region}-a"  # just use zone "a" instead of adding another script arg

PROJECT_ID=$GOOGLE_CLOUD_PROJECT # get the environment variable

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
topic_alerts=$(define_GCP_resources "${survey}-alerts")
subscription_alert_data=$(define_GCP_resources "${survey}-alert-bigquery-import") # BigQuery subscription
topic_alert_data_deadletter=$(define_GCP_resources "${survey}-alert-bigquery-import-deadletter")
subscription_alert_data_deadletter="${topic_alert_data_deadletter}"

alerts_table="alerts_${versiontag}"

# function used to create (or delete) GCP resources
manage_resources() {
    local mode="$1"  # setup or teardown
    local environment_type="production"

    if [ "$testid" != "False" ]; then
        environment_type="testing"
    fi

    if [ "$mode" = "setup" ]; then
        # create BigQuery dataset and table
        echo
        echo "Creating BigQuery dataset and table..."
        bq --location="${region}" mk --dataset "${bq_dataset}"

        cd templates || exit 5
        bq mk --table "${PROJECT_ID}:${bq_dataset}.${alerts_table}" "bq_${survey}_${alerts_table}_schema.json" || exit 5
        bq update --description "Alert data from LIGO/Virgo/KAGRA. This table is an archive of the lvk-alerts Pub/Sub stream. It has the same schema as the original alert bytes, including nested and repeated fields." "${PROJECT_ID}:${bq_dataset}.${alerts_table}"
        cd .. || exit 5

        # create broker bucket and upload files
        echo
        echo "Creating broker_bucket and uploading files..."
        gsutil mb -b on -l "${region}" "gs://${broker_bucket}"
        ./upload_broker_bucket.sh "${broker_bucket}"

        # create Pub/Sub
        echo
        echo "Configuring Pub/Sub resources..."
        gcloud pubsub topics create "${topic_alerts}"
        gcloud pubsub topics create "${topic_alert_data_deadletter}"
        gcloud pubsub subscriptions create "${subscription_alert_data_deadletter}" --topic="${topic_alert_data_deadletter}"
        # in order to create BigQuery subscriptions, ensure that the following service account:
        # service-<project number>@gcp-sa-pubsub.iam.gserviceaccount.com" has the
        # bigquery.dataEditor role for each table
        gcloud pubsub subscriptions create "${subscription_alert_data}" \
            --topic="${topic_alerts}" \
            --bigquery-table="${PROJECT_ID}:${bq_dataset}.${alerts_table}" \
            --use-table-schema \
            --drop-unknown-fields \
            --dead-letter-topic="${topic_alert_data_deadletter}" \
            --max-delivery-attempts=5 \
            --dead-letter-topic-project="${PROJECT_ID}"

        # set IAM policies on resources
        user="allUsers"
        roleid="projects/${GOOGLE_CLOUD_PROJECT}/roles/userPublic"
        gcloud pubsub topics add-iam-policy-binding "${topic_alerts}" --member="${user}" --role="${roleid}"

    else
        if [ "$environment_type" = "testing" ]; then
            # delete testing resources
            o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
            gsutil -m -o "${o}" rm -r "gs://${broker_bucket}"
            bq rm -r -f "${PROJECT_ID}:${bq_dataset}"
            gcloud pubsub topics delete "${topic_alerts}"
            gcloud pubsub topics delete "${topic_alert_data_deadletter}"
            gcloud pubsub subscriptions delete "${subscription_alert_data_deadletter}"
            gcloud pubsub subscriptions delete "${subscription_alert_data}"
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
./create_vms.sh "${broker_bucket}" "${testid}" "${teardown}" "${survey}" "${zone}"
