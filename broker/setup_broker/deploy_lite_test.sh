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
topic_alerts="${survey}-alerts"
topic_lite="${survey}-lite"
topic_tagged="${survey}-tagged"
topic_snn="${survey}-SuperNNova"
lite_CF_name="${survey}-lite"
tag_CF_name="${survey}-tag"
snn_CF_name="${survey}-classify_with_SuperNNova"
bq_dataset="${PROJECT_ID}:${survey}_alerts"
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    topic_alerts="${topic_alerts}-${testid}"
    topic_lite="${topic_lite}-${testid}"
    topic_tagged="${topic_tagged}-${testid}"
    topic_snn="${topic_snn}-${testid}"
    lite_CF_name="${lite_CF_name}-${testid}"
    tag_CF_name="${tag_CF_name}-${testid}"
    snn_CF_name="${snn_CF_name}-${testid}"
    bq_dataset="${bq_dataset}_${testid}"
    broker_bucket="${broker_bucket}-${testid}"
fi
lite_trigger_topic="${topic_alerts}"
tag_trigger_topic="${topic_lite}"
snn_trigger_topic="${topic_tagged}"
class_table="classifications"
tags_table="tags"
snn_table="SuperNNova"

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
        gcloud functions delete "$lite_CF_name" --quiet
        gcloud functions delete "$tag_CF_name" --quiet
        gcloud functions delete "$snn_CF_name" --quiet
        gsutil -m rm -r "gs://${broker_bucket}"
        gcloud pubsub topics delete "${topic_alerts}" --quiet
        gcloud pubsub topics delete "${topic_lite}" --quiet
        bq rm -r "${bq_dataset}"
        gcloud pubsub topics delete "${topic_tagged}" --quiet
        gcloud pubsub topics delete "${topic_snn}" --quiet
        gcloud pubsub subscriptions delete "${topic_lite}" --quiet
        gcloud pubsub subscriptions delete "${topic_tagged}" --quiet
        gcloud pubsub subscriptions delete "${topic_snn}" --quiet
    fi

else # Deploy the Cloud Functions and create other Cloud resources
    OGdir=$(pwd)

#--- create the broker's cloud storage bucket and upload files
    gsutil mb -b on "gs://${broker_bucket}"
    ./upload_broker_bucket.sh "${broker_bucket}"

#--- create the pub/sub topics and subscriptions
    gcloud pubsub topics create "${topic_alerts}"
    gcloud pubsub topics create "${topic_lite}"
    gcloud pubsub topics create "${topic_tagged}"
    gcloud pubsub topics create "${topic_snn}"
    gcloud pubsub subscriptions create "${topic_lite}" --topic "${topic_lite}"
    gcloud pubsub subscriptions create "${topic_tagged}" --topic "${topic_tagged}"
    gcloud pubsub subscriptions create "${topic_snn}" --topic "${topic_snn}"

#--- create the bigquery dataset and tables
    bq mk --dataset "${bq_dataset}"
    bq mk --table "${bq_dataset}.${class_table}" "templates/bq_${survey}_${class_table}_schema.json"
    bq mk --table "${bq_dataset}.${tags_table}" "templates/bq_${survey}_${tags_table}_schema.json"
    bq mk --table "${bq_dataset}.${snn_table}" "templates/bq_${survey}_${snn_table}_schema.json"

# entry_point for all cloud fncs
    entry_point="run"

#--- lite cloud function
    echo "Deploying Cloud Function: $lite_CF_name"

    cd .. && cd cloud_functions
    cd lite

    gcloud functions deploy "$lite_CF_name" \
        --entry-point "$entry_point" \
        --runtime python37 \
        --trigger-topic "$lite_trigger_topic" \
        --set-env-vars TESTID="$testid",SURVEY="$survey"

    cd $OGdir

#--- tag cloud function
    echo "Deploying Cloud Function: $tag_CF_name"
    memory=512MB  # standard 256MB is too small here

    cd .. && cd cloud_functions
    cd tag

    gcloud functions deploy "$tag_CF_name" \
        --entry-point "$entry_point" \
        --memory "$memory" \
        --runtime python37 \
        --trigger-topic "$tag_trigger_topic" \
        --set-env-vars TESTID="$testid",SURVEY="$survey"

    cd $OGdir

#--- SNN cloud function
    echo "Deploying Cloud Function: $snn_CF_name"
    memory=512MB  # standard 256MB is too small here

    cd .. && cd cloud_functions
    cd classify_snn

    gcloud functions deploy "$snn_CF_name" \
        --entry-point "$entry_point" \
        --memory "$memory" \
        --runtime python37 \
        --trigger-topic "$snn_trigger_topic" \
        --set-env-vars TESTID="$testid",SURVEY="$survey"

    cd $OGdir
fi
