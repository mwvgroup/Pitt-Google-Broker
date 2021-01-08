#! /bin/bash

# GOOGLE_CLOUD_PROJECT should exist as an environment variable
PROJECT_ID=${GOOGLE_CLOUD_PROJECT}
# # Set brokerdir as the parent directory of this script's directory
# brokerdir=$(dirname "$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )")
# # https://stackoverflow.com/questions/4774054/reliable-way-for-a-bash-script-to-get-the-full-path-to-itself

# Create BigQuery, GCS, Pub/Sub and Logging resources
python3 setup_gcp.py

# Upload some broker files to GCS so the VMs can use them
bucket="${PROJECT_ID}-broker_files"
gsutil -m cp -r ../beam gs://${bucket}
gsutil -m cp -r ../consumer gs://${bucket}
gsutil -m cp -r ../night_conductor gs://${bucket}

# Setup the Pub/Sub notifications on ZTF Avro storage bucket
BUCKET_NAME=${PROJECT_ID}_ztf_alert_avro_bucket
TOPIC_NAME=projects/${PROJECT_ID}/topics/ztf_alert_avro_bucket
format=none  # json or none; whether to deliver the payload with the PS msg
gsutil notification create \
            -t ${TOPIC_NAME} \
            -e OBJECT_FINALIZE \
            -f ${format} \
            gs://${BUCKET_NAME}

# Deploy Cloud Functions
./deploy_cloud_fncs.sh

# Create a firewall rule to open the port used by Kafka/ZTF
# on any instance with the flag --tags=ztfport
gcloud compute firewall-rules create 'ztfport' \
    --allow=tcp:9094 \
    --description="Allow incoming traffic on TCP port 9094" \
    --direction=INGRESS \
    --enable-logging

# Create VM instances
./create_vms.sh ${bucket}
# takes about 5 min to complete; waits for VMs to start up
