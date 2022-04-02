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
consumerVMsched="${consumerVM}-schedule"
nconductVM="${survey}-night-conductor"
nconductVMsched="${nconductVM}-schedule"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    consumerVM="${consumerVM}-${testid}"
    consumerVMsched="${consumerVMsched}-${testid}"
    nconductVM="${nconductVM}-${testid}"
    nconductVMsched="${nconductVMsched}-${testid}"
fi

#--- Teardown resources
if [ "$teardown" = "True" ]; then
    # ensure that we do not teardown production resources
    if [ "$testid" != "False" ]; then
        gcloud compute instances delete "$consumerVM" "$nconductVM" --zone="$zone"
    fi

#--- Create resources
else
#--- Night Conductor VM
    # create schedule
    start_schedule='00 16 * * *'  # 4:00pm UTC / 9:00am PDT, everyday
    gcloud compute resource-policies create instance-schedule "${nconductVMsched}" \
        --description="Start ${nconductVM} each morning." \
        --vm-start-schedule="${start_schedule}" \
        --timezone="UTC"
    # create VM
    installscript="gs://${broker_bucket}/night_conductor/vm_install.sh"
    machinetype=e2-standard-2
    gcloud compute instances create "$nconductVM" \
        --resource-policies="${nconductVMsched}" \
        --zone="$zone" \
        --machine-type="$machinetype" \
        --scopes=cloud-platform \
        --metadata=google-logging-enabled=true,startup-script-url="$installscript"

#--- Consumer VM
    # create schedule
    start_schedule='30 1 * * *'  # 1:30am UTC / 5:30pm PDT, everyday
    stop_schedule='55 13 * * *'  # 1:55pm UTC / 6:55am PDT, everyday
    gcloud compute resource-policies create instance-schedule "${consumerVMsched}" \
    --description="Start ${consumerVM} each night, stop each morning." \
    --vm-start-schedule="${start_schedule}" \
    --vm-stop-schedule="${stop_schedule}" \
    --timezone="UTC"
    # create VM
    machinetype=e2-standard-2
    # metadata
    googlelogging="google-logging-enabled=true"
    startupscript="startup-script-url=gs://${broker_bucket}/consumer/vm_install.sh"
    shutdownscript="shutdown-script-url=gs://${broker_bucket}/consumer/vm_shutdown.sh"
    gcloud compute instances create "$consumerVM" \
        --resource-policies="${consumerVMsched}" \
        --zone="$zone" \
        --machine-type="$machinetype" \
        --scopes=cloud-platform \
        --metadata="${googlelogging},${startupscript},${shutdownscript}" \
        --tags=ztfport # for the firewall rule to open the port

#--- Disable the schedules for testing instances
    if [ "$testid" != "False" ]; then
        gcloud compute instances remove-resource-policies "${nconductVM}" \
            --resource-policies="${nconductVMsched}"
        gcloud compute instances remove-resource-policies "${consumerVM}" \
            --resource-policies="${consumerVMsched}"
    fi

fi
