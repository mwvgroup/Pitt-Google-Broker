#! /bin/bash
# stop the ztf-consumer VM instance

instancename=ztf-consumer
zone=us-central1-a
gcloud compute instances stop ${instancename} --zone ${zone}
