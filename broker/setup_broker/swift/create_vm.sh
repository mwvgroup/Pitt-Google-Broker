#! /bin/bash
# Creates or deletes the GCP VM instances needed by the broker.
# This script will not delete VMs that are in production

# name of GCS bucket where broker files are staged
gcs_broker_bucket=$1
# "False" uses production resources
# any other string will be appended to the names of all resources
testid="${2:-test}"
# "True" tearsdown/deletes resources, else setup
teardown="${3:-False}"
# name of the survey this broker instance will ingest
survey="${4:-swift}"
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
#--- Setup resources if they do not exist
else
    if ! gcloud compute instances describe "${consumerVM}" --zone="${zone}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
        machinetype=e2-custom-1-5632
        # metadata
        googlelogging="google-logging-enabled=true"
        startupscript="startup-script-url=gs://${gcs_broker_bucket}/${survey}/vm_install.sh"
        shutdownscript="shutdown-script-url=gs://${gcs_broker_bucket}/${survey}/vm_shutdown.sh"
        #--- Create VM
        gcloud compute instances create "$consumerVM" \
            --zone="$zone" \
            --machine-type="$machinetype" \
            --scopes=cloud-platform \
            --metadata="${googlelogging},${startupscript},${shutdownscript}"
    else
        echo
        echo "VM instance ${consumerVM} already exists in zone ${zone}."
    fi
fi
