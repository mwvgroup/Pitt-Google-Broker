#! /bin/bash
# stop the ztf-consumer VM instance

testid=$1

consumerVM=ztf-consumer
if [ "$testid" != "False" ]; then
    consumerVM="${consumerVM}-${testid}"
fi
zone=us-central1-a
gcloud compute instances stop ${consumerVM} --zone ${zone}
