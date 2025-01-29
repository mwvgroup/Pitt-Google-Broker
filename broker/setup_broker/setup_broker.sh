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
schema_version="${4:-4.02}"
versiontag=v$(echo "${schema_version}" | tr . _)  # 4.02 -> v4_02
use_authentication="${5:-false}"  # whether the consumer VM should use an authenticated connection
region="${6:-us-central1}"
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

read continue_with_setup
continue_with_setup="${continue_with_setup:-n}"
if [ "$continue_with_setup" != "y" ]; then
    echo "Exiting setup."
    echo
    exit
fi

# function used to define GCP resources; appends testid if needed
define_GCP_resources() {
    local base_name="$1"
    local testid_suffix=""

    if [ "$testid" != "False" ]; then
        if [ "$base_name" = "$survey" ]; then
            testid_suffix="_${testid}"  # complies with BigQuery naming conventions
        else
            testid_suffix="-${testid}"
        fi
    fi

    echo "${base_name}${testid_suffix}"
}

#--- GCP resources used directly in this script
broker_bucket=$(define_GCP_resources "${PROJECT_ID}-${survey}-broker_files")
bq_dataset=$(define_GCP_resources "${survey}")
topic_alerts=$(define_GCP_resources "${survey}-alerts")
# topics and subscriptions involved in writing DIASource data to BigQuery
topic_diasource=$(define_GCP_resources "${survey}-diasource")
subscription_diasource="${topic_diasource}" # BigQuery subscription
topic_diasource_deadletter=$(define_GCP_resources "${survey}-diasource-deadletter")
subscription_diasource_deadletter="${topic_diasource_deadletter}"
# topics and subscriptions involved in writing alert data to BigQuery
topic_alert_data=$(define_GCP_resources "${survey}-alert-data") # needs a better name
subscription_alert_data="${topic_alert_data}" # BigQuery subscription
topic_alert_data_deadletter=$(define_GCP_resources "${survey}-alert-data-deadletter")
subscription_alert_data_deadletter="${topic_alert_data_deadletter}"

alerts_table="alerts_${versiontag}"
diasource_table="DIASource"

# function used to create (or delete) GCP resources
manage_resources() {
    local mode="$1"  # setup or teardown
    local environment_type="production"

    if [ "$testid" != "False" ]; then
        environment_type="testing"
    fi

    if [ "$mode" = "setup" ]; then
        # setup resources
        python3 setup_gcp.py --survey="$survey" --testid="$testid" --confirmed --region="${region}" --versiontag="${versiontag}"
        gcloud pubsub topics create "${topic_diasource}"
        gcloud pubsub topics create "${topic_diasource_deadletter}"
        gcloud pubsub topics create "${topic_alert_data}"
        gcloud pubsub topics create "${topic_alert_data_deadletter}"
        gcloud pubsub subscriptions create "${subscription_diasource_deadletter}" --topic="${topic_diasource_deadletter}"
        gcloud pubsub subscriptions create "${subscription_alert_data_deadletter}" --topic="${topic_alert_data_deadletter}"
        gcloud pubsub subscriptions create "${subscription_alert_data}" \
            --topic="${topic_alert_data}" \
            --bigquery-table="${PROJECT_ID}:${bq_dataset}.${alerts_table}" \
            --use-table-schema \
            --drop-unknown-fields \
            --dead-letter-topic="${topic_alert_data_deadletter}" \
            --max-delivery-attempts=5 \
            --dead-letter-topic-project="${PROJECT_ID}"
        gcloud pubsub subscriptions create "${subscription_diasource}" \
            --topic="${topic_diasource}" \
            --bigquery-table="${PROJECT_ID}:${bq_dataset}.${diasource_table}" \
            --use-table-schema \
            --drop-unknown-fields \
            --dead-letter-topic="${topic_diasource_deadletter}" \
            --max-delivery-attempts=5 \
            --dead-letter-topic-project="${PROJECT_ID}"
    else
        if [ "$environment_type" = "testing" ]; then
            # delete testing resources
            python3 setup_gcp.py --survey="$survey" --testid="$testid" --teardown --confirmed --versiontag="${versiontag}"
            gcloud pubsub topics delete "${topic_diasource}"
            gcloud pubsub topics delete "${topic_diasource_deadletter}"
            gcloud pubsub topics delete "${topic_alert_data}"
            gcloud pubsub topics delete "${topic_alert_data_deadletter}"
            gcloud pubsub subscriptions delete "${subscription_diasource}"
            gcloud pubsub subscriptions delete "${subscription_diasource_deadletter}"
            gcloud pubsub subscriptions delete "${subscription_alert_data}"
            gcloud pubsub subscriptions delete "${subscription_alert_data_deadletter}"
        fi
    fi
}

#--- Create (or delete) BigQuery, GCS, Pub/Sub resources
echo
echo "Configuring BigQuery, GCS, Pub/Sub resources..."
if [ "$teardown" = "True" ]; then
    manage_resources "teardown"
else
    manage_resources "setup"
fi

#--- finish setting up buckets and dataset
if [ "$teardown" != "True" ]; then
    ./upload_broker_bucket.sh "$broker_bucket"

    bq add-iam-policy-binding \
        --member="allUsers" \
        --role="roles/bigquery.metadataViewer" \
        "${bq_dataset}"
    bq add-iam-policy-binding \
        --member="allUsers" \
        --role="roles/bigquery.dataViewer" \
        "${bq_dataset}"
fi


#--- Create VM instances
echo
echo "Configuring VMs..."
./create_vms.sh "${broker_bucket}" "${testid}" "${teardown}" "${survey}" "${region}" "${zone}" "${use_authentication}"


#--- Create the cron jobs that check the VM status
echo
echo "Setting up Cloud Scheduler cron jobs"
./create_cron_jobs.sh "$testid" "$teardown" "$survey" "$region"


if [ "$teardown" != "True" ]; then

#--- Create a firewall rule to open the port used by Kafka/ZTF
# on any instance with the flag --tags=ztfport
    echo
    echo "Configuring ZTF/Kafka firewall rule..."
    gcloud compute firewall-rules create 'ztfport' \
        --allow=tcp:9094 \
        --description="Allow incoming traffic on TCP port 9094" \
        --direction=INGRESS \
        --enable-logging

fi

#--- Deploy Cloud Functions
echo
echo "Configuring Cloud Functions..."
cd .. && cd cloud_functions || exit

#--- Check cue response cloud function
cd check_cue_response || exit
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag" "$zone"

#--- classify with SNN cloud function
cd .. && cd classify_snn || exit
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag"

#--- alerts-lite cloud function
cd .. && cd lite || exit
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag"

#--- Pub/Sub -> Cloud Storage Avro cloud function
cd .. && cd ps_to_gcs || exit
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag" "$region"

#--- tag alerts cloud function
cd .. && cd tag || exit
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag"

#--- return to setup_broker directory
cd .. && cd .. || exit
cd setup_broker || exit
