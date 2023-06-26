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
schema_version="${4:-3.3}"
versiontag=v$(echo "${schema_version}" | tr . _)  # 3.3 -> v3_3
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

read continue_with_setup
continue_with_setup="${continue_with_setup:-n}"
if [ "$continue_with_setup" != "y" ]; then
    echo "Exiting setup."
    echo
    exit
fi

#--- GCP resources used directly in this script
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
bq_dataset="${survey}"
avro_bucket="${PROJECT_ID}-${survey}_alerts_${versiontag}"
avro_topic="projects/${PROJECT_ID}/topics/${survey}-alert_avros"
# use test resources, if requested
# (there must be a better way to do this)
if [ "$testid" != "False" ]; then
    broker_bucket="${broker_bucket}-${testid}"
    bq_dataset="${bq_dataset}_${testid}"
    avro_bucket="${avro_bucket}-${testid}"
    avro_topic="${avro_topic}-${testid}"
fi


#--- Create (or delete) BigQuery, GCS, Pub/Sub resources
echo
echo "Configuring BigQuery, GCS, Pub/Sub resources..."
if [ "$testid" != "False" ]; then
    if [ "$teardown" = "True" ]; then
        # delete testing resources
        python3 setup_gcp.py --survey="$survey" --testid="$testid" --teardown --confirmed --versiontag="${versiontag}"
    else
        # setup testing resources
        python3 setup_gcp.py --survey="$survey" --testid="$testid" --confirmed --region="${region}" --versiontag="${versiontag}"
    fi
else
    # setup production resources
    python3 setup_gcp.py --survey="$survey" --production --confirmed --region="${region}"
fi


#--- finish setting up buckets and dataset
if [ "$teardown" != "True" ]; then
    ./upload_broker_bucket.sh "$broker_bucket"

    gsutil uniformbucketlevelaccess set on "gs://${avro_bucket}"
    gsutil requesterpays set on "gs://${avro_bucket}"
    gcloud storage buckets add-iam-policy-binding "gs://${avro_bucket}" \
        --member="allUsers" \
        --role="roles/storage.objectViewer"

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
./create_vms.sh "$broker_bucket" "$testid" "$teardown" "$survey" "$region" "$zone"


#--- Create the cron jobs that check the VM status
echo
echo "Setting up Cloud Scheduler cron jobs"
./create_cron_jobs.sh "$testid" "$teardown" "$survey" "$region"


if [ "$teardown" != "True" ]; then

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
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag"

#--- BigQuery storage cloud function
cd .. && cd store_BigQuery || exit
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag"

#--- tag alerts cloud function
cd .. && cd tag || exit
./deploy.sh "$testid" "$teardown" "$survey" "$versiontag"

#--- return to setup_broker directory
cd .. && cd .. || exit
cd setup_broker
