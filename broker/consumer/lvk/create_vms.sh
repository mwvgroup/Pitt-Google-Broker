#! /bin/bash
# Creates or deletes the GCP VM instances needed by the broker.
# This script will not delete VMs that are in production


broker_bucket=$1 # name of GCS bucket where broker files are staged
testid="${2:-test}"
#   "False" uses production resources
#   any other string will be appended to the names of all resources
teardown="${3:-False}" # "True" tearsdown/deletes resources, else setup
survey="${4:-ztf}"
# name of the survey this broker instance will ingest
region="${5:-us-central1}"
zone="${6:-us-central1-a}"

#--- GCP resources used in this script
consumerVM="${survey}-consumer"
consumerVMsched="${consumerVM}-schedule"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    consumerVM="${consumerVM}-${testid}"
fi
consumerIP="${consumerVM}"  # gcp resource name of the consumer's static ip address

#--- Teardown resources
if [ "$teardown" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "$testid" != "False" ]; then
        gcloud compute instances delete "$consumerVM" --zone="$zone"
        gcloud compute addresses delete "${consumerIP}" --region="${region}"
    fi

#--- Create resources
else
#--- Consumer VM
    # create a static ip address so that it can be whitelisted by the survey
    gcloud compute addresses create "${consumerIP}" --region="${region}"
    # create VM
    machinetype=e2-standard-2
    # metadata
    googlelogging="google-logging-enabled=true"
    startupscript="startup-script-url=gs://${broker_bucket}/consumer/${survey}/vm_install.sh"
    shutdownscript="shutdown-script-url=gs://${broker_bucket}/consumer/${survey}/vm_shutdown.sh"
    gcloud compute instances create "$consumerVM" \
        --resource-policies="${consumerVMsched}" \
        --zone="$zone" \
        --address="$consumerIP" \
        --machine-type="$machinetype" \
        --scopes=cloud-platform \
        --metadata="${googlelogging},${startupscript},${shutdownscript}" \
        --tags=ztfport # for the firewall rule to open the port

#--- Disable the schedules for testing instances
    if [ "$testid" != "False" ]; then
        gcloud compute instances remove-resource-policies "${consumerVM}" \
            --resource-policies="${consumerVMsched}"
    fi

fi
