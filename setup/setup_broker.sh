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

read continue_with_setup
continue_with_setup="${continue_with_setup:-n}"
if [ "$continue_with_setup" != "y" ]; then
    echo "Exiting setup."
    echo
    exit
fi

#--- GCP resources used directly in this script
avro_bucket="${PROJECT_ID}-${survey}-alert_avros"
avro_topic="projects/${PROJECT_ID}/topics/${survey}-alert_avros"
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
bq_dataset="${PROJECT_ID}:${survey}_alerts"
bq_topic="projects/${PROJECT_ID}/topics/${survey}-BigQuery"
topic_alerts="${survey}-alerts"
# use test resources, if requested
# (there must be a better way to do this)
if [ "$testid" != "False" ]; then
    avro_bucket="${avro_bucket}-${testid}"
    avro_topic="${avro_topic}-${testid}"
    broker_bucket="${broker_bucket}-${testid}"
    bq_dataset="${bq_dataset}_${testid}"
    bq_topic="${bq_topic}-${testid}"
    topic_alerts="${topic_alerts}-${testid}"
fi
alerts_table="alerts"
source_table="DIASource"


# broker bucket
if [ "$teardown" != "True" ]; then
    echo "Creating broker_bucket and uploading files..."
    gsutil mb -b on "gs://${broker_bucket}"
    ./upload_broker_bucket.sh "$broker_bucket"
else
    # ensure that we do not teardown production resources
    if [ "$testid" != "False" ]; then
        gsutil rm -r "gs://${broker_bucket}"
    fi
fi

#--- Create VM instances
echo
echo "Configuring VMs..."
./create_vms.sh "$broker_bucket" "$testid" "$teardown" "$survey"


if [ "$teardown" != "True" ]; then
    echo "Configuring BigQuery, GCS, Pub/Sub resources..."
    bq mk --dataset "${bq_dataset}"
    bq mk --table "${bq_dataset}.${alerts_table}" "templates/bq_${survey}_${alerts_table}_schema.json"
    bq mk --table "${bq_dataset}.${source_table}" "templates/bq_${survey}_${source_table}_schema.json"
    gcloud pubsub topics create "${avro_topic}"
    gcloud pubsub topics create "${bq_topic}"
    gcloud pubsub topics create "${topic_alerts}"
    gcloud pubsub subscriptions create "${topic_alerts}-reservoir" --topic "${topic_alerts}"
    #--- Setup the Pub/Sub notifications on ZTF Avro storage bucket
    echo
    echo "Configuring Pub/Sub notifications on GCS bucket..."
    trigger_event=OBJECT_FINALIZE
    format=json  # json or none; if json, file metadata sent in message body
    gsutil notification create \
                -t "$avro_topic" \
                -e "$trigger_event" \
                -f "$format" \
                "gs://${avro_bucket}"
else
    # ensure that we do not teardown production resources
    if [ "$testid" != "False" ]; then
        bq rm --dataset true "${bq_dataset}"
        gcloud pubsub topics delete "${avro_topic}"
        gcloud pubsub topics delete "${bq_topic}"
        gcloud pubsub topics delete "${topic_alerts}"
        gcloud pubsub subscriptions delete "${topic_alerts}-reservoir"
    fi
fi


#--- Deploy Cloud Functions
echo
echo "Configuring Cloud Functions..."
./deploy_cloud_fncs.sh "$testid" "$teardown" "$survey"
