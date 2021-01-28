#! /bin/bash
#
# Startup script for the `night-conductor` Compute Engine VM instance.
# Orchestrates the broker to ingest and process the
# nightly LSST/ZTF alert stream.
#
# This script downloads a set of scripts in the broker's
# night_conductor GCS bucket and runs them,
# triggering the start up or shutdown of the
# GCP resources/jobs that ingest and process the alert stream.
#
# We use metadata attributes
# (set on `night-conductor` prior to starting it, see README.md for links)
# to pass information to this script which triggers the desired behavior.
# For example:
#
# To start the broker using testing resources tagged with "mytest"
# and ingest ZTF's stream for Jan. 19, 2021:
#---
# testid=mytest
# NIGHT=START
# KAFKA_TOPIC=ztf_20210119_programid1
# nconductVM="night-conductor-${testid}"
# zone=us-central1-a
# gcloud compute instances add-metadata "$nconductVM" --zone="$zone" \
#       --metadata NIGHT="$NIGHT",KAFKA_TOPIC="$KAFKA_TOPIC"
# gcloud compute instances start ${nconductVM} --zone ${zone}
#---
#
# To end the night and tear down broker resources:
#---
# testid=mytest
# NIGHT=END
# nconductVM="night-conductor-${testid}"
# zone=us-central1-a
# gcloud compute instances add-metadata ${nconductVM} --zone=${zone} \
#       --metadata NIGHT="$NIGHT"
# gcloud compute instances start ${nconductVM} --zone ${zone}
#---
#
# At the end of this script, metadata attributes are cleared so that there is
# no unanticipated behavior the next time the VM starts.
# Finally, the script shuts down `night-conductor`.
#


#--- Get metadata attributes, PROJECT_ID, and testid
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
NIGHT=$(curl "${baseurl}/instance/attributes/NIGHT" -H "${H}")
PROJECT_ID=$(curl "${baseurl}/project/project-id" -H "${H}")
nconductVM=$(curl "${baseurl}/instance/name" -H "${H}")
# parse the testid from the VM name
if [ "$nconductVM" = "night-conductor" ]; then
    testid="False"
else
    testid=$(echo "$nconductVM" | awk -F "-" '{print $NF}')
fi

#--- GCP resources used in this script
broker_bucket="${PROJECT_ID}-broker_files"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    broker_bucket="${broker_bucket}-${testid}"
fi

workingdir=/home/broker/night_conductor
mkdir -p ${workingdir}
cd ${workingdir}

if [ "${NIGHT}" = "START" ]
then
    # copy broker's start_night directory from GCS and cd in
    gsutil -m cp -r gs://${broker_bucket}/night_conductor/start_night .
    cd start_night
    chmod 744 *.sh

    # start up the resources, begin consuming and processing
    ./start_night.sh ${PROJECT_ID} ${testid} ${broker_bucket}

elif [ "${NIGHT}" = "END" ]
then
    # copy broker's end_night directory from GCS and cd in
    gsutil -m cp -r gs://${broker_bucket}/night_conductor/end_night .
    cd end_night
    chmod 744 *.sh

    # stop ingesting and teardown resources
    ./end_night.sh ${testid}
fi

# Wait a few minutes, then clear all metadata attributes and shutdown
sleep 120

zone=us-central1-a
gcloud compute instances add-metadata ${nconductVM} --zone=${zone} \
      --metadata NIGHT="",KAFKA_TOPIC="",PS_TOPIC=""

shutdown -h now
