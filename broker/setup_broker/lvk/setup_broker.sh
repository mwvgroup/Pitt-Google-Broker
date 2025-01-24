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

#--- GCP resources used directly in this script
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
bq_dataset="${survey}"
topic_alerts="${survey}-alerts"
topic_deadletter="${survey}-deadletter"
subscription_storebigquery="${survey}-bigquery"
subscription_deadletter="${survey}-deadletter"

# use test resources, if requested
if [ "$testid" != "False" ]; then
    broker_bucket="${broker_bucket}-${testid}"
    bq_dataset="${bq_dataset}_${testid}"
    topic_alerts="${topic_alerts}-${testid}"
    topic_deadletter="${topic_deadletter}-${testid}"
    subscription_storebigquery="${subscription_storebigquery}-${testid}"
    subscription_deadletter="${subscription_deadletter}-${testid}"

fi

alerts_table="alerts_${versiontag}"

#--- Create (or delete) BigQuery, GCS, Pub/Sub resources
echo
echo "Configuring BigQuery, GCS, Pub/Sub resources..."
if [ "${teardown}" != "True" ]; then
    # create bigquery dataset and table
    bq --location="${region}" mk --dataset "${bq_dataset}"

    cd templates || exit 5
    bq mk --table "${PROJECT_ID}:${bq_dataset}.${alerts_table}" "bq_${survey}_${alerts_table}_schema.json" || exit 5
    bq update --description "Alert data from LIGO/Virgo/KAGRA. This table is an archive of the lvk-alerts Pub/Sub stream. It has the same schema as the original alert bytes, including nested and repeated fields." "${PROJECT_ID}:${bq_dataset}.${alerts_table}"
    cd .. || exit 5

    # create broker bucket and upload files
    echo "Creating broker_bucket and uploading files..."
    gsutil mb -b on -l "${region}" "gs://${broker_bucket}"
    ./upload_broker_bucket.sh "${broker_bucket}"

    # create pubsub
    echo "Configuring Pub/Sub resources..."
    gcloud pubsub topics create "${topic_alerts}"
    gcloud pubsub topics create "${topic_deadletter}"
    gcloud pubsub subscriptions create "${subscription_storebigquery}" --topic="${topic_alerts}" --bigquery-table="${PROJECT_ID}:${bq_dataset}.${alerts_table}" --use-table-schema --drop-unknown-fields --dead-letter-topic="${topic_deadletter}" --max-delivery-attempts=5 --dead-letter-topic-project=$PROJECT_ID
    gcloud pubsub subscriptions create "${subscription_deadletter}" --topic="${topic_deadletter}"

    # set IAM policies on resources
    user="allUsers"
    roleid="projects/${GOOGLE_CLOUD_PROJECT}/roles/userPublic"
    gcloud pubsub topics add-iam-policy-binding "${topic_alerts}" --member="${user}" --role="${roleid}"

else
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
        gsutil -m -o "${o}" rm -r "gs://${broker_bucket}"
        bq rm -r -f "${PROJECT_ID}:${bq_dataset}"
        gcloud pubsub topics delete "${topic_alerts}"
        gcloud pubsub subscriptions delete "${subscription_storebigquery}"
    fi
fi

#--- Create VM instances
echo
echo "Configuring VMs..."
./create_vms.sh "${broker_bucket}" "${testid}" "${teardown}" "${survey}" "${zone}"
