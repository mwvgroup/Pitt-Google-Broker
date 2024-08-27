#! /bin/bash
# Create and configure GCP resources needed to run the nightly broker.

testid="${1:-test}"
# "False" uses production resources
# any other string will be appended to the names of all resources
teardown="${2:-False}"
# "True" tearsdown/deletes resources, else setup
survey="${3:-lvk}"
# name of the survey this broker instance will ingest
observation_run="${4:-4}"
versiontag="O${observation_run}" # 4 -> O4
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
topic_storeBigQuery="${survey}-BigQuery"

# use test resources, if requested
if [ "$testid" != "False" ]; then
    broker_bucket="${broker_bucket}-${testid}"
    bq_dataset="${bq_dataset}_${testid}"
    topic_alerts="${topic_alerts}-${testid}"
    topic_storeBigQuery="${topic_storeBigQuery}-${testid}"
fi

alerts_table="alerts_${versiontag}"

#--- Create (or delete) BigQuery, GCS, Pub/Sub resources
echo
echo "Configuring BigQuery, GCS, Pub/Sub resources..."
if [ "${teardown}" != "True" ]; then
    # create bigquery dataset and table
    bq --location="${region}" mk --dataset "${bq_dataset}"

    cd templates || exit
    bq mk --table "${PROJECT_ID}:${bq_dataset}.${alerts_table}" "bq_${survey}_${alerts_table}_schema.json"
    cd .. || exit

    # create broker bucket and upload files
    echo "Creating broker_bucket and uploading files..."
    gsutil mb -b on -l "${region}" "gs://${broker_bucket}"
    ./upload_broker_bucket.sh "${broker_bucket}"

    # create pubsub
    echo "Configuring Pub/Sub resources..."
    gcloud pubsub topics create "${topic_alerts}"
    gcloud pubsub topics create "${topic_storeBigQuery}"

    # Set IAM policies on resources
    user="allUsers"
    roleid="projects/${GOOGLE_CLOUD_PROJECT}/roles/userPublic"
    gcloud pubsub topics add-iam-policy-binding "${topic_alerts}" --member="${user}" --role="${roleid}"
    gcloud pubsub topics add-iam-policy-binding "${topic_storeBigQuery}" --member="${user}" --role="${roleid}"

else
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
        bq rm -r -f "${PROJECT_ID}:${bq_dataset}"
        gsutil -m -o "${o}" rm -r "gs://${broker_bucket}"
        gcloud pubsub topics delete "${topic_alerts}"
    fi
fi

#--- Create VM instances
echo
echo "Configuring VMs..."
./create_vms.sh "${broker_bucket}" "${testid}" "${teardown}" "${survey}" "${zone}"

#--- Deploy Cloud Functions
echo
echo "Configuring Cloud Functions..."
cd .. && cd .. || exit
cd cloud_functions && cd lvk || exit

#--- BigQuery storage cloud function
cd store_BigQuery || exit
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag"

#--- return to setup_broker directory
cd .. && cd .. || exit
cd .. && cd setup_broker || exit
