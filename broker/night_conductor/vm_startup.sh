#! /bin/bash
# Start up all resources required to ingest and process the ZTF stream.

workingdir=/home/broker/night_conductor
mkdir -p ${workingdir}
cd ${workingdir}

baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
PROJECT_ID=$(curl "${baseurl}/project/project-id" -H "${H}")
bucket="${PROJECT_ID}-broker_files"

# copy broker's start_night directory from GCS and cd in
gsutil cp -r gs://${bucket}/night_conductor/start_night .
cd start_night

# start up the resources, begin consuming and processing
./start_night.sh
