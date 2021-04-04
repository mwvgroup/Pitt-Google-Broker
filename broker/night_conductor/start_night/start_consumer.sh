#! /bin/bash

testid=$1
broker_bucket=$2
KAFKA_TOPIC=$3

#--- GCP resources used in this script
PS_TOPIC=ztf_alerts
consumerVM=ztf-consumer
if [ "$testid" != "False" ]; then
    PS_TOPIC="${PS_TOPIC}-${testid}"
    consumerVM="${consumerVM}-${testid}"
fi

# Set consumer VM metadata for the day's topic
zone=us-central1-a
gcloud compute instances add-metadata ${consumerVM} --zone=${zone} \
      --metadata KAFKA_TOPIC=${KAFKA_TOPIC},PS_TOPIC=${PS_TOPIC}

# set the startup script
startupscript="gs://${broker_bucket}/consumer/vm_startup.sh"
gcloud compute instances add-metadata ${consumerVM} --zone ${zone} \
  --metadata startup-script-url=${startupscript}

# start the VM
gcloud compute instances start ${consumerVM} --zone ${zone}
# this launches the startup script which configures and starts the
# Kafka -> Pub/Sub connector
