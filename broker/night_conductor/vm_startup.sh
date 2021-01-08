#! /bin/bash
# Start up all resources required to ingest and process the ZTF stream.
#---
# [ToDo]:
# 1. Set up the end_night script
# 2. Use custom metadata attribute NIGHT=[START or END]
# plus an if statement below to trigger to appropriate script
# 3. Use custom metadata attribute KAFKA_TOPIC,
# pass it to start_night.sh which will pass it on to the consumer.
#
# See this directory's README.sh for links re: metadata attributes


workingdir=/home/broker/night_conductor
mkdir -p ${workingdir}
cd ${workingdir}

baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
PROJECT_ID=$(curl "${baseurl}/project/project-id" -H "${H}")
bucket="${PROJECT_ID}-broker_files"

# copy broker's start_night directory from GCS and cd in
gsutil -m cp -r gs://${bucket}/night_conductor/start_night .
cd start_night
chmod 744 *.sh

# start up the resources, begin consuming and processing
KAFKA_TOPIC=nodate  # pass a neutral arg.
# topic must be set, and consumer started, manually after the VM starts
./start_night.sh ${KAFKA_TOPIC}
