#! /bin/bash
# Creates or deletes the GCP VM instances needed by the broker.
# This script will not (is not configured to) delete Cloud Functions that are in production


# CE_zone should exist as an environment variable
bucket=$1 # name of GCS bucket where broker files are staged
testrun="${2:-True}" # "True" uses test resources, else production resources
teardown="${3:-False}" # "True" tearsdown/deletes resources, else setup

#--- GCP resources used in this script
consumerVM="ztf-consumer"
nconductVM="night-conductor"
if [ "$testrun" = "True" ]; then
    consumerVM="${consumerVM}-test"
    nconductVM="${nconductVM}-test"
fi

#--- Teardown resources
if [ "$teardown" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "$testrun" = "True" ]; then
        gcloud compute instances delete "$consumerVM" "$nconductVM" --zone="$CE_zone"
    fi

#--- Create resources
else
    #--- Create and configure the ZTF Kafka Consumer VM
    installscript="gs://${bucket}/consumer/vm_install.sh"
    startupscript="gs://${bucket}/consumer/vm_startup.sh"
    machinetype=e2-standard-2
    gcloud compute instances create "$consumerVM" \
        --zone="$CE_zone" \
        --machine-type="$machinetype" \
        --scopes=cloud-platform \
        --metadata=google-logging-enabled=true,startup-script-url="$installscript" \
        --tags=ztfport # for the firewall rule to open the port
    # give the vm time to start the install before switching the startup script
    sleep 120
    # set the startup script
    gcloud compute instances add-metadata "$consumerVM" --zone "$CE_zone" \
        --metadata startup-script-url="$startupscript"

    #--- Create and configure the Night Conductor VM
    installscript="gs://${bucket}/night_conductor/vm_install.sh"
    startupscript="gs://${bucket}/night_conductor/vm_startup.sh"
    machinetype=e2-standard-2
    gcloud compute instances create "$nconductVM" \
        --zone="$CE_zone" \
        --machine-type="$machinetype" \
        --scopes=cloud-platform \
        --metadata=google-logging-enabled=true,startup-script-url="$installscript"
    # give the vm time to start the install before switching the startup script
    sleep 120
    # set the startup script
    gcloud compute instances add-metadata "$nconductVM" --zone "$CE_zone" \
        --metadata startup-script-url="$startupscript"

fi
