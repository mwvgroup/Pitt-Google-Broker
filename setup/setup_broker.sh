#! /bin/bash
# Create and configure GCP resources needed to run the nightly broker.
testid="${1:-test}"  # "False" => production. else will be appended to names of all resources
teardown="${2:-False}"  # "True" tearsdown/deletes resources, else setup
survey="${3:-elasticc}"  # name of the survey this broker instance will ingest
max_instances="${4:-500}"  # max N of concurrent Cloud Fnc instances (per deployed module)
PROJECT_ID="${GOOGLE_CLOUD_PROJECT}"
BROKER_VERSION=$(cat "../VERSION")

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
if [ "${continue_with_setup}" != "y" ]; then
    echo "Exiting setup."
    echo
    exit
fi

#--- GCP resources used directly in this script
bq_dataset="${PROJECT_ID}:${survey}_alerts"
bq_topic="projects/${PROJECT_ID}/topics/${survey}-BigQuery"
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
topic_alerts="${survey}-alerts"

# use test resources, if requested
# (there must be a better way to do this)
if [ "$testid" != "False" ]; then
    bq_dataset="${bq_dataset}_${testid}"
    bq_topic="${bq_topic}-${testid}"
    broker_bucket="${broker_bucket}-${testid}"
    topic_alerts="${topic_alerts}-${testid}"
fi

# broker bucket
if [ "${teardown}" != "True" ]; then
    echo "Creating broker_bucket and uploading files..."
    gsutil mb -b on "gs://${broker_bucket}"
    ./upload_broker_bucket.sh "${broker_bucket}"
else
    # ensure that we do not teardown production resources
    if [ "$testid" != "False" ]; then
        o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
        gsutil -m -o "${o}" rm -r "gs://${broker_bucket}"
    fi
fi

#--- Create VM instances
echo
echo "Configuring VMs..."
./create_vms.sh "${broker_bucket}" "${testid}" "${teardown}" "${survey}"

#--- Create BQ, PS, GCS resources
if [ "${teardown}" != "True" ]; then
    echo "Configuring BigQuery, GCS, Pub/Sub resources..."
    # create dashboard
    gcloud monitoring dashboards create --config-from-file="templates/dashboard.json"
    # create bigquery
    alerts_table="alerts"
    source_table="DIASource"
    bq mk --dataset "${bq_dataset}"
    bq mk --table "${bq_dataset}.${alerts_table}" "templates/bq_${survey}_${alerts_table}_schema.json"
    bq mk --table "${bq_dataset}.${source_table}" "templates/bq_${survey}_${source_table}_schema.json"
    # create pubsub
    gcloud pubsub topics create "${bq_topic}"
    gcloud pubsub topics create "${topic_alerts}"
    gcloud pubsub subscriptions create "${topic_alerts}-reservoir" --topic "${topic_alerts}"
    gcloud pubsub subscriptions create "${avro_topic}-reservoir" --topic "${avro_topic}"

    # Set IAM policies on resources
    user="allUsers"
    roleid="projects/${GOOGLE_CLOUD_PROJECT}/roles/userPublic"
    gcloud pubsub topics add-iam-policy-binding "${avro_topic}" --member="${user}" --role="${roleid}"
    gcloud pubsub topics add-iam-policy-binding "${topic_alerts}" --member="${user}" --role="${roleid}"
    gsutil iam ch "${user}:${roleid}" "gs://${avro_bucket}"


else
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        bq rm --dataset true "${bq_dataset}"
        gcloud pubsub topics delete "${bq_topic}"
        gcloud pubsub topics delete "${topic_alerts}"
        gcloud pubsub subscriptions delete "${topic_alerts}-reservoir"
        gcloud pubsub subscriptions delete "${avro_topic}-reservoir"
    fi
fi


#--- Deploy Cloud Functions
echo
echo "Configuring Cloud Functions..."
cd .. && cd broker || exit

#--- Pub/Sub -> Cloud Storage Avro cloud function
cd cloud_functions && cd ps_to_gcs || exit
./deploy.sh "$testid" "$teardown" "$survey" "$max_instances" "$BROKER_VERSION"

cd .. && cd store_BigQuery || exit
./deploy.sh "$testid" "$teardown" "$survey"

cd .. && cd .. || exit
cd .. && cd setup || exit