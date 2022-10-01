#! /bin/bash
# Creates or deletes the GCP VM instances needed by the broker.
# This script will not delete VMs that are in production
broker_bucket=$1
testid="${2:-test}"
teardown="${3:-False}"
survey="${4:-ztf}"
zone="${CE_ZONE:-us-central1-a}"

#--- GCP resources used in this script
consumerVM="${survey}-consumer"
# use test resources, if requested
if [ "${testid}" != "False" ]; then
    consumerVM="${consumerVM}-${testid}"
fi

#--- Teardown resources
if [ "${teardown}" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "${testid}" != "False" ]; then
        gcloud compute instances delete "${consumerVM}" --zone="${zone}"
    fi

#--- Create resources
else
#--- Consumer VM
    installscript="gs://${broker_bucket}/consumer/vm_install.sh"
    machinetype="e2-standard-2"
    gcloud compute instances create "${consumerVM}" \
        --zone "${zone}" \
        --machine-type "${machinetype}" \
        --scopes "cloud-platform" \
        --metadata "google-logging-enabled=true,startup-script-url=${installscript}" \
        --tags "kafkaport" # firewall rule that opens the port
fi
