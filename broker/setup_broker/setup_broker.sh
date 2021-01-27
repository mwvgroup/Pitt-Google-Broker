#! /bin/bash
# Create and configure GCP resources needed to run the nightly broker.

testrun="${1:-True}" # "True" uses test resources, else production resources
teardown="${2:-False}" # "True" tearsdown/deletes resources, else setup
PROJECT_ID=$GOOGLE_CLOUD_PROJECT # get the environment variable

#--- GCP resources used directly in this script
broker_bucket="${PROJECT_ID}-broker_files"
avro_bucket="${PROJECT_ID}_ztf_alert_avro_bucket"
avro_topic="projects/${PROJECT_ID}/topics/ztf_alert_avro_bucket"
# use test resources, if requested
# (there must be a better way to do this)
if [ "$testrun" = "True" ]; then
    broker_bucket="${broker_bucket}-test"
    avro_bucket="${avro_bucket}-test"
    avro_topic="${avro_topic}-test"
fi

#--- Create (or delete) BigQuery, GCS, Pub/Sub resources
echo
echo "Configuring BigQuery, GCS, Pub/Sub resources..."
if [ "$testrun" = "True" ]; then
    if [ "$teardown" = "True" ]; then
        python3 setup_gcp.py --testrun --teardown
    else
        python3 setup_gcp.py --testrun
    fi
else
    python3 setup_gcp.py --production
fi

if [ "$teardown" != "True" ]; then

    #--- Upload some broker files to GCS so the VMs can use them
    echo
    echo "Uploading broker files to GCS..."
    gsutil -m cp -r ../beam "gs://${broker_bucket}"
    gsutil -m cp -r ../consumer "gs://${broker_bucket}"
    gsutil -m cp -r ../night_conductor "gs://${broker_bucket}"

    #--- Setup the Pub/Sub notifications on ZTF Avro storage bucket
    echo
    echo "Configuring Pub/Sub notifications on GCS bucket(s)..."
    format=none  # json or none; whether to deliver the payload with the PS msg
    gsutil notification create \
                -t "$avro_topic" \
                -e OBJECT_FINALIZE \
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
./deploy_cloud_fncs.sh "$testrun" "$teardown"

#--- Create VM instances
echo
echo "Configuring VMs..."
./create_vms.sh "$broker_bucket" "$testrun" "$teardown"
# takes about 5 min to complete; waits for VMs to start up
