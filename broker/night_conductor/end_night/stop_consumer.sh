#! /bin/bash
# stop the ztf-consumer VM instance

testid=$1
survey="${2:-ztf}"

consumerVM="${survey}-consumer"
if [ "${testid}" != "False" ]; then
    consumerVM="${consumerVM}-${testid}"
fi
zone="us-central1-a"

# unset the startup script and other metadata so there is
# no unexpected behavior on the next startup
gcloud compute instances add-metadata "${consumerVM}" --zone="${zone}" \
    --metadata="startup-script-url=,KAFKA_TOPIC=,PS_TOPIC="

# stop the instance
gcloud compute instances stop "${consumerVM}" --zone="${zone}"
