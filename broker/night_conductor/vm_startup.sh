#! /bin/bash
# Startup script for the `night-conductor` Compute Engine VM instance.


#--- Get metadata attributes, PROJECT_ID, and testid
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
NIGHT=$(curl "${baseurl}/instance/attributes/NIGHT" -H "${H}")
PROJECT_ID=$(curl "${baseurl}/project/project-id" -H "${H}")
nconductVM=$(curl "${baseurl}/instance/name" -H "${H}")
# parse the survey name and testid from the VM name
survey=$(echo "${nconductVM}" | awk -F "-" '{print $1}')
if [ "$nconductVM" = "${survey}-night-conductor" ]; then
    testid="False"
else
    testid=$(echo "${nconductVM}" | awk -F "-" '{print $NF}')
fi

#--- GCP resources used in this script
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
# use test resources, if requested
if [ "${testid}" != "False" ]; then
    broker_bucket="${broker_bucket}-${testid}"
fi

workingdir=/home/broker/night_conductor
mkdir -p ${workingdir}
cd ${workingdir}

if [ "${NIGHT}" = "START" ]
then
    # replace broker's start_night directory with GCS files and cd in
    rm -r start_night
    gsutil -m cp -r gs://${broker_bucket}/night_conductor/start_night .
    cd start_night
    chmod 744 *.sh

    # start up the resources, begin consuming and processing
    ./start_night.sh ${PROJECT_ID} ${testid} ${broker_bucket} ${survey}

elif [ "${NIGHT}" = "END" ]
then
    # replace broker's end_night directory with GCS files and cd in
    rm -r end_night
    gsutil -m cp -r gs://${broker_bucket}/night_conductor/end_night .
    cd end_night
    chmod 744 *.sh

    # stop ingesting and teardown resources
    ./end_night.sh ${PROJECT_ID} ${testid} ${survey}
fi

# Wait a few minutes, then clear all metadata attributes and shutdown
# skip this if not starting/stoping the night (so we can turn it on to debug)
if [ "${NIGHT}" = "START" ] || [ "${NIGHT}" = "END" ]; then
    sleep 120

    zone="us-central1-a"
    gcloud compute instances add-metadata "${nconductVM}" --zone="${zone}" \
          --metadata="NIGHT=,KAFKA_TOPIC=,PS_TOPIC="

    shutdown -h now
fi
