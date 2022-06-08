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
filter_exgal_trigger_topic="${survey}-alerts"
filter_exgal_CF_name="${survey}-filter_exgalac_trans"
classify_snn_trigger_topic="${survey}-exgalac_trans_cf"
classify_snn_CF_name="${survey}-classify_with_SuperNNova"
publish_classifications_trigger_topic="${survey}-SuperNNova"
publish_classifications_CF_name="${survey}-publish_classifications"
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
topic_alerts="${survey}-alerts"
topic_exgalac="${survey}-exgalac_trans_cf"
topic_snn="${survey}-SuperNNova"
topic_classifications="${survey}-classifications"
bq_dataset="${PROJECT_ID}:${survey}_alerts"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    filter_exgal_trigger_topic="${filter_exgal_trigger_topic}-${testid}"
    filter_exgal_CF_name="${filter_exgal_CF_name}-${testid}"
    classify_snn_trigger_topic="${classify_snn_trigger_topic}-${testid}"
    classify_snn_CF_name="${classify_snn_CF_name}-${testid}"
    publish_classifications_trigger_topic="${publish_classifications_trigger_topic}-${testid}"
    publish_classifications_CF_name="${publish_classifications_CF_name}-${testid}"
    broker_bucket="${broker_bucket}-${testid}"
    topic_alerts="${topic_alerts}-${testid}"
    topic_exgalac="${topic_exgalac}-${testid}"
    topic_snn="${topic_snn}-${testid}"
    topic_classifications="${topic_classifications}-${testid}"
    bq_dataset="${bq_dataset}_${testid}"
fi
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
        gcloud functions delete "$filter_exgal_CF_name" --quiet
        gcloud functions delete "$classify_snn_CF_name" --quiet
        gcloud functions delete "$publish_classifications_CF_name" --quiet
        gsutil -m rm -r "gs://${broker_bucket}"
        gcloud pubsub topics delete "${topic_alerts}" --quiet
        gcloud pubsub topics delete "${topic_exgalac}" --quiet
        gcloud pubsub topics delete "${topic_snn}" --quiet
        gcloud pubsub topics delete "${topic_classifications}" --quiet
        gcloud pubsub subscriptions delete "${topic_classifications}" --quiet
    fi

else # Deploy the Cloud Functions and create other Cloud resources
    OGdir=$(pwd)

#--- create the broker's cloud storage bucket and upload files
    gsutil mb -b on "gs://${broker_bucket}"
    ./upload_broker_bucket.sh "${broker_bucket}"

#--- create the pub/sub topics and subscriptions
    gcloud pubsub topics create "${topic_alerts}"
    gcloud pubsub topics create "${topic_exgalac}"
    gcloud pubsub topics create "${topic_snn}"
    gcloud pubsub topics create "${topic_classifications}"
    gcloud pubsub subscriptions create "${topic_classifications}" \
        --topic "${topic_classifications}"

#--- create the bigquery dataset and tables
    bq mk --dataset "${bq_dataset}"
    bq mk --table "${bq_dataset}.${snn_table}" "templates/bq_${survey}_${snn_table}_schema.json"

#--- publish classifications cloud function
    echo "Deploying Cloud Function: $publish_classifications_CF_name"
    publish_classifications_entry_point="run"

    cd .. && cd cloud_functions
    cd publish_classifications

    gcloud functions deploy "$publish_classifications_CF_name" \
        --entry-point "$publish_classifications_entry_point" \
        --runtime python37 \
        --trigger-topic "$publish_classifications_trigger_topic" \
        --set-env-vars TESTID="$testid",SURVEY="$survey"

    cd $OGdir

#--- classify with SNN cloud function
    echo "Deploying Cloud Function: $classify_snn_CF_name"
    classify_snn_entry_point="run"
    memory=512MB  # standard 256MB is too small here

    cd .. && cd cloud_functions
    cd classify_snn

    gcloud functions deploy "$classify_snn_CF_name" \
        --entry-point "$classify_snn_entry_point" \
        --memory "$memory" \
        --runtime python37 \
        --trigger-topic "$classify_snn_trigger_topic" \
        --set-env-vars TESTID="$testid",SURVEY="$survey"

    cd $OGdir

#--- filter for extragalactic transients cloud function
    echo "Deploying Cloud Function: $filter_exgal_CF_name"
    filter_exgal_entry_point="run"

    cd .. && cd cloud_functions
    cd filter_exgalac_trans

    gcloud functions deploy "$filter_exgal_CF_name" \
        --entry-point "$filter_exgal_entry_point" \
        --runtime python37 \
        --trigger-topic "$filter_exgal_trigger_topic" \
        --set-env-vars TESTID="$testid",SURVEY="$survey"

    cd $OGdir

fi
