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
zone="${CE_ZONE:-us-central1-a}" # use env variable CE_ZONE if it exists

#--- GCP resources used in this script
consumerVM="${survey}-consumer"
nconductVM="${survey}-night-conductor"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    consumerVM="${consumerVM}-${testid}"
    nconductVM="${nconductVM}-${testid}"
fi

#--- Teardown resources
if [ "$teardown" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "$testid" != "False" ]; then
        gcloud compute instances delete "$consumerVM" "$nconductVM" --zone="$zone"
    fi

#--- Create resources
else
#--- Create and configure the ZTF Kafka Consumer VM
    installscript="gs://${broker_bucket}/consumer/vm_install.sh"
    startupscript="gs://${broker_bucket}/consumer/vm_startup.sh"
    machinetype=e2-standard-2
    gcloud compute instances create "$consumerVM" \
        --zone="$zone" \
        --machine-type="$machinetype" \
        --scopes=cloud-platform \
        --metadata=google-logging-enabled=true,startup-script-url="$installscript" \
        --tags=ztfport # for the firewall rule to open the port
    # give the vm time to start the install before switching the startup script
    echo "Waiting to allow the ${consumerVM} build to start."
    sleep 120
    # set the startup script
    gcloud compute instances add-metadata "$consumerVM" --zone "$zone" \
        --metadata startup-script-url="$startupscript"

#--- Create and configure the Night Conductor VM
    installscript="gs://${broker_bucket}/night_conductor/vm_install.sh"
    startupscript="gs://${broker_bucket}/night_conductor/vm_startup.sh"
    machinetype=e2-standard-2
    gcloud compute instances create "$nconductVM" \
        --zone="$zone" \
        --machine-type="$machinetype" \
        --scopes=cloud-platform \
        --metadata=google-logging-enabled=true,startup-script-url="$installscript"
    # give the vm time to start the install before switching the startup script
    echo "Waiting to allow the ${nconductVM} build to start."
    sleep 120
    # set the startup script
    gcloud compute instances add-metadata "$nconductVM" --zone "$zone" \
        --metadata startup-script-url="$startupscript"

fi
