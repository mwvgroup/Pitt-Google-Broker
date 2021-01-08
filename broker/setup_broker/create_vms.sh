#! /bin/bash
# Creates the GCP VM instances needed by the broker.


bucket=$1
# CE_zone should exist as an environment variable

#--- Create and configure the Kafka Consumer VM
instancename=ztf-consumer
installscript="gs://${bucket}/consumer/vm_install.sh"
startupscript="gs://${bucket}/consumer/vm_startup.sh"
machinetype=e2-standard-2

# create the instance
gcloud compute instances create ${instancename} \
    --zone=${CE_zone} \
    --machine-type=${machinetype} \
    --scopes=cloud-platform \
    --metadata=google-logging-enabled=true,startup-script-url=${installscript} \
    --tags=ztfport # for the firewall rule to open the port
# give the vm time to start the install before switching the script
sleep 2m
# set the startup script
gcloud compute instances add-metadata ${instancename} --zone ${CE_zone} \
    --metadata startup-script-url=${startupscript}

#--- Create and configure the Night Conductor VM
instancename=night-conductor
installscript="gs://${bucket}/night_conductor/vm_install.sh"
startupscript="gs://${bucket}/night_conductor/vm_startup.sh"
machinetype=e2-standard-2
gcloud compute instances create ${instancename} \
    --zone=${CE_zone} \
    --machine-type=${machinetype} \
    --scopes=cloud-platform \
    --metadata=google-logging-enabled=true,startup-script-url=${installscript}
# give the vm time to start the install before switching the script
sleep 2m
# set the startup script
gcloud compute instances add-metadata ${instancename} --zone ${CE_zone} \
    --metadata startup-script-url=${startupscript}
