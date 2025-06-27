#! /bin/bash
# Creates or deletes the GCP VM instances needed by the broker.
# This script will not delete VMs that are in production


broker_bucket=$1 # name of GCS bucket where broker files are staged
testid="${2:-test}"
#   "False" uses production resources
#   any other string will be appended to the names of all resources
teardown="${3:-False}" # "True" tearsdown/deletes resources, else setup
survey="${4:-swift}"
# name of the survey this broker instance will ingest
zone="${5:-us-central1-a}"
project_id="${6:-PROJECT_ID}"

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


else
#--- Consumer VM
    if ! gcloud compute instances describe "${consumerVM}" --zone="${zone}" --project="${project_id}" >/dev/null 2>&1; then
        #--- Create VM
        machinetype=e2-custom-1-5632
        # metadata
        googlelogging="google-logging-enabled=true"
        startupscript="startup-script-url=gs://${broker_bucket}/${survey}/vm_install.sh"
        shutdownscript="shutdown-script-url=gs://${broker_bucket}/${survey}/vm_shutdown.sh"
        gcloud compute instances create "$consumerVM" \
            --zone="$zone" \
            --machine-type="$machinetype" \
            --scopes=cloud-platform \
            --metadata="${googlelogging},${startupscript},${shutdownscript}"
    else
        echo "VM instance ${consumerVM} already exists in zone ${zone}."
    fi
fi
