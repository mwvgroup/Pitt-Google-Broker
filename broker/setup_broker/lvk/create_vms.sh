#! /bin/bash
# Creates or deletes the GCP VM instances needed by the broker.
# This script will not delete VMs that are in production


broker_bucket=$1 # name of GCS bucket where broker files are staged
testid="${2:-test}"
#   "False" uses production resources
#   any other string will be appended to the names of all resources
teardown="${3:-False}" # "True" tearsdown/deletes resources, else setup
survey="${4:-lvk}"
# name of the survey this broker instance will ingest
zone="${5:-us-central1-a}"

#--- GCP resources used in this script
consumerVM="${survey}-consumer"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    consumerVM="${consumerVM}-${testid}"
fi

#--- Teardown resources
if [ "$teardown" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "$testid" != "False" ]; then
        gcloud compute instances delete "$consumerVM" --zone="$zone"
    fi

#--- Create resources
else
#--- Consumer VM
    # create VM
    machinetype=e2-standard-2
    # metadata
    googlelogging="google-logging-enabled=true"
    startupscript="startup-script-url=gs://${broker_bucket}/consumer/${survey}/vm_install.sh"
    shutdownscript="shutdown-script-url=gs://${broker_bucket}/consumer/${survey}/vm_shutdown.sh"
    gcloud compute instances create "$consumerVM" \
        --zone="$zone" \
        --machine-type="$machinetype" \
        --scopes=cloud-platform \
        --metadata="${googlelogging},${startupscript},${shutdownscript}"

fi
