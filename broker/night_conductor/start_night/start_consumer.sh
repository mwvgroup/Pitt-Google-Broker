#! /bin/bash

# Set consumer VM metadata for the day's topic
# for info on working with custom metadata, see here
# https://cloud.google.com/compute/docs/storing-retrieving-metadata#custom
KAFKA_TOPIC=$1  # ztf_20210105_programid1
instancename=ztf-consumer
zone=us-central1-a
PS_TOPIC=ztf_alert_data
gcloud compute instances add-metadata ${instancename} --zone=${zone} \
      --metadata KAFKA_TOPIC=${KAFKA_TOPIC},PS_TOPIC=${PS_TOPIC}

# set the startup script
startupscript="gs://${bucket}/consumer/vm_startup.sh"
gcloud compute instances add-metadata ${instancename} --zone ${zone} \
  --metadata startup-script-url=${startupscript}

# start the VM
gcloud compute instances start ${instancename} --zone ${zone}
# this launches the startup script which configures and starts the
# Kafka -> Pub/Sub connector
