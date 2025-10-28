#! /bin/bash
# Startup script for the `night-conductor` Compute Engine VM instance.


#--- Get metadata attributes, PROJECT_ID, and testid
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
PROJECT_ID=$(curl "${baseurl}/project/project-id" -H "${H}")
nconductVM=$(curl "${baseurl}/instance/name" -H "${H}")
# parse the survey name and testid from the VM name
survey=$(echo "$nconductVM" | awk -F "-" '{print $1}')
if [ "$nconductVM" = "${survey}-night-conductor" ]; then
    testid="False"
else
    testid=$(echo "$nconductVM" | awk -F "-" '{print $NF}')
fi

#--- GCP resources used in this script
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    broker_bucket="${broker_bucket}-${testid}"
fi

# copy fresh instructions from the broker bucket
brokerdir="/home/broker"
workingdir="${brokerdir}/night_conductor"
rm -r "${workingdir}"
mkdir -p "${workingdir}"
gsutil -m cp -r "gs://${broker_bucket}/night_conductor" "${brokerdir}"
# make shell and python files executable
find "${workingdir}" -type f \( -name "*.sh" -o -name "*.py" \) -exec chmod +x {} \;

#--- Process Pub/Sub counters
echo "Processing Pub/Sub counters..."
if [ "$testid" = "False" ]; then
    python3 "${workingdir}/process_pubsub_counters.py" --survey="$survey" --production
else
    python3 "${workingdir}/process_pubsub_counters.py" --survey="$survey" --testid="$testid"
fi

# Wait a minute, then shutdown
shutdown -h +1
