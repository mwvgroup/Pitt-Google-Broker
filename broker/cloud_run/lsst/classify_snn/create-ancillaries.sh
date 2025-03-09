#! /bin/bash
# Create ancillary resources that are needed by the Cloud Run service.
# This script is intended to be run by Cloud Build.

# Define resource names.
# BigQuery
bq_dataset=$(construct-name.sh --stem "$_SURVEY" --gcp-resource bigquery)
bq_table_supernnova="supernnova"
# Pub/Sub
ps_topic_out=$(construct-name.sh --stem "supernnova")
ps_topic_bqimport=$(construct-name.sh --stem "bigquery-import-supernnova")
ps_topic_bqimport_deadletter=$(construct-name.sh --stem "bigquery-import-supernnova-deadletter")
ps_subscrip_trigger="$_TRIGGER_TOPIC"
ps_subscrip_bqimport="$ps_topic_bqimport"
ps_subscrip_bqimport_deadletter="$ps_topic_bqimport_deadletter"

# Create the resources.
gcloud pubsub topics create "${ps_topic_out}"
gcloud pubsub topics create "${ps_topic_bqimport}"
gcloud pubsub topics create "${ps_topic_bqimport_deadletter}"
gcloud pubsub subscriptions create "${ps_subscrip_bqimport_deadletter}" --topic="${ps_topic_bqimport_deadletter}"
# [FIXME] This assumes that the BigQuery dataset and table already exist.
gcloud pubsub subscriptions create "${ps_subscrip_bqimport}" \
    --topic="${ps_topic_bqimport}" \
    --bigquery-table="${PROJECT_ID}:${bq_dataset}.${bq_table_supernnova}" \
    --use-table-schema \
    --dead-letter-topic="${ps_topic_bqimport_deadletter}" \
    --max-delivery-attempts=5 \
    --dead-letter-topic-project="${PROJECT_ID}"
