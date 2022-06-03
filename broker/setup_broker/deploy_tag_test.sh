#! /bin/bash
# Deploys or deletes broker Cloud Functions
# This script will not delete Cloud Functions that are in production

# testid="False" uses production resources
# any other string will be appended to the names of all resources
testid="${1:-test}"
# name of the survey this broker instance will ingest
survey="${2:-ztf}"
# "True" tearsdown/deletes resources, else setup
teardown="${3:-False}"
zone="${CE_ZONE:-us-central1-a}" # use env variable CE_ZONE if it exists

PROJECT_ID="${GOOGLE_CLOUD_PROJECT}"

#--- GCP resources used in this script
tag_trigger_topic="${survey}-alerts"
tag_CF_name="${survey}-tag"
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
topic_alerts="${survey}-alerts"
topic_tagged="${survey}-tagged"
bq_dataset="${PROJECT_ID}:${survey}_alerts"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    tag_trigger_topic="${tag_trigger_topic}-${testid}"
    tag_CF_name="${tag_CF_name}-${testid}"
    broker_bucket="${broker_bucket}-${testid}"
    topic_alerts="${topic_alerts}-${testid}"
    topic_tagged="${topic_tagged}-${testid}"
    bq_dataset="${bq_dataset}_${testid}"
fi
class_table="classifications"
tags_table="tags"

# make the user confirm the options
action='create resources'
if [ "$teardown" == "True" ]; then
    action='DELETE ALL RESOURCES'
fi
echo
echo "setup_broker.sh will ${action} named with the broker instance keywords:"
echo "survey = ${survey}"
echo "testid = ${testid}"
echo
echo "Do you want to continue?  [y/(n)]: "
read continue_with_setup
continue_with_setup="${continue_with_setup:-n}"
if [ "$continue_with_setup" != "y" ]; then
    exit
fi

if [ "$teardown" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "$testid" != "False" ]; then
        gcloud functions delete "$tag_CF_name" --quiet
        gsutil -m rm -r "gs://${broker_bucket}"
        gcloud pubsub topics delete "${topic_alerts}" --quiet
        gcloud pubsub topics delete "${topic_tagged}" --quiet
        gcloud pubsub subscriptions delete "${topic_tagged}" --quiet
    fi

else # Deploy the Cloud Functions and create other Cloud resources
    OGdir=$(pwd)

#--- create the broker's cloud storage bucket and upload files
    gsutil mb -b on "gs://${broker_bucket}"
    ./upload_broker_bucket.sh "${broker_bucket}"

#--- create the pub/sub topics and subscriptions
    gcloud pubsub topics create "${topic_alerts}"
    gcloud pubsub topics create "${topic_tagged}"
    gcloud pubsub subscriptions create "${topic_tagged}" \
        --topic "${topic_tagged}"

#--- create the bigquery dataset and tables
    bq mk --dataset "${bq_dataset}"
    bq mk --table "${bq_dataset}.${class_table}" "templates/bq_${survey}_${class_table}_schema.json"
    bq mk --table "${bq_dataset}.${tags_table}" "templates/bq_${survey}_${tags_table}_schema.json"

#--- tag cloud function
    echo "Deploying Cloud Function: $tag_CF_name"
    tag_entry_point="run"

    cd .. && cd cloud_functions
    cd tag

    gcloud functions deploy "$tag_CF_name" \
        --entry-point "$tag_entry_point" \
        --runtime python37 \
        --trigger-topic "$tag_trigger_topic" \
        --set-env-vars TESTID="$testid",SURVEY="$survey"

    cd $OGdir

fi
