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
avro_bucket="${PROJECT_ID}-${survey}-alert_avros"
avro_topic="${survey}-alert_avros"
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
topic_alerts="${survey}-alerts"

# use test resources, if requested
# (there must be a better way to do this)
if [ "$testid" != "False" ]; then
    avro_bucket="${avro_bucket}-${testid}"
    avro_topic="${avro_topic}-${testid}"
    broker_bucket="${broker_bucket}-${testid}"
    topic_alerts="${topic_alerts}-${testid}"
fi

# broker bucket
if [ "${teardown}" != "True" ]; then
    echo "Creating broker_bucket and uploading files..."
    gsutil mb -b on "gs://${broker_bucket}"
    gsutil mb -b on "gs://${avro_bucket}"
    ./upload_broker_bucket.sh "${broker_bucket}"
else
    # ensure that we do not teardown production resources
    if [ "$testid" != "False" ]; then
        o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
        gsutil -m -o "${o}" rm -r "gs://${broker_bucket}"
        gsutil -m -o "${o}" rm -r "gs://${avro_bucket}"
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
    # create pubsub
    gcloud pubsub topics create "${avro_topic}"
    gcloud pubsub topics create "${topic_alerts}"
    gcloud pubsub subscriptions create "${topic_alerts}-reservoir" --topic "${topic_alerts}"
    gcloud pubsub subscriptions create "${avro_topic}-reservoir" --topic "${avro_topic}"

    # Set IAM policies on resources
    user="allUsers"
    roleid="projects/${GOOGLE_CLOUD_PROJECT}/roles/userPublic"
    gcloud pubsub topics add-iam-policy-binding "${avro_topic}" --member="${user}" --role="${roleid}"
    gcloud pubsub topics add-iam-policy-binding "${topic_alerts}" --member="${user}" --role="${roleid}"
    gsutil iam ch "${user}:${roleid}" "gs://${avro_bucket}"

    #--- Setup the Pub/Sub notifications on ZTF Avro storage bucket
    echo
    echo "Configuring Pub/Sub notifications on GCS bucket..."
    trigger_event=OBJECT_FINALIZE
    format=json  # json or none; if json, file metadata sent in message body
    gsutil notification create \
                -t "${avro_topic}" \
                -e "${trigger_event}" \
                -f "${format}" \
                "gs://${avro_bucket}"
else
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        gcloud pubsub topics delete "${avro_topic}"
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
cd .. && cd setup