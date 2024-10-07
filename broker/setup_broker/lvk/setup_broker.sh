#! /bin/bash
# Create and configure GCP resources needed to run the nightly broker.

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
topic_storebigquery="${survey}-bigquery"

# use test resources, if requested
if [ "$testid" != "False" ]; then
    broker_bucket="${broker_bucket}-${testid}"
    bq_dataset="${bq_dataset}_${testid}"
    topic_alerts="${topic_alerts}-${testid}"
    topic_storebigquery="${topic_storebigquery}-${testid}"
fi

alerts_table="alerts_${versiontag}"

#--- Create (or delete) BigQuery, GCS, Pub/Sub resources
echo
echo "Configuring BigQuery, GCS, Pub/Sub resources..."
if [ "${teardown}" != "True" ]; then
    # create bigquery dataset and table
    bq --location="${region}" mk --dataset "${bq_dataset}"

    cd templates && bq mk --table "${PROJECT_ID}:${bq_dataset}.${alerts_table}" "bq_${survey}_${alerts_table}_schema.json" || exit 5
    cd .. || exit 5

    # create broker bucket and upload files
    echo "Creating broker_bucket and uploading files..."
    gsutil mb -b on -l "${region}" "gs://${broker_bucket}"
    ./upload_broker_bucket.sh "${broker_bucket}"

    # create pubsub
    echo "Configuring Pub/Sub resources..."
    gcloud pubsub topics create "${topic_alerts}"
    gcloud pubsub topics create "${topic_storebigquery}"

    # Set IAM policies on resources
    user="allUsers"
    roleid="projects/${GOOGLE_CLOUD_PROJECT}/roles/userPublic"
    gcloud pubsub topics add-iam-policy-binding "${topic_alerts}" --member="${user}" --role="${roleid}"
    gcloud pubsub topics add-iam-policy-binding "${topic_storebigquery}" --member="${user}" --role="${roleid}"

else
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
        gsutil -m -o "${o}" rm -r "gs://${broker_bucket}"
        bq rm -r -f "${PROJECT_ID}:${bq_dataset}"
        gcloud pubsub topics delete "${topic_alerts}"
        gcloud pubsub topics delete "${topic_storebigquery}"
    fi
fi

#--- Create VM instances
echo
echo "Configuring VMs..."
./create_vms.sh "${broker_bucket}" "${testid}" "${teardown}" "${survey}" "${zone}"

#--- Deploy Cloud Functions
echo
echo "Configuring Cloud Functions..."
cd .. && cd .. && cd cloud_functions && cd lvk || exit 5

#--- BigQuery storage cloud function
cd store_BigQuery && ./deploy.sh "$testid" "$teardown" "$survey" "$versiontag"|| exit 5

#--- return to setup_broker/lvk directory
cd .. && cd .. && cd .. && cd setup_broker && cd lvk || exit 5
