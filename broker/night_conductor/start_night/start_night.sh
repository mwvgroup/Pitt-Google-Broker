#! /bin/bash
# Start up all required resources; ingest and process the ZTF stream.

KAFKA_TOPIC="$1"  # ztf_20210105_programid1
# KAFKA_TOPIC is currently unset; start connector manually
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
PROJECT_ID=$(curl "${baseurl}/project/project-id" -H "${H}")
# PROJECT_ID=${GOOGLE_CLOUD_PROJECT}
brokerdir=/home/broker
mkdir -p ${brokerdir}
bucket="${PROJECT_ID}-broker_files"

#--- Reset Pub/Sub counters
./reset_ps_counters.sh ${PROJECT_ID}

#--- Start the Beam/Dataflow jobs
./start_beam_jobs.sh ${PROJECT_ID} ${brokerdir} ${bucket}

#--- Start the consumer
./start_consumer.sh ${KAFKA_TOPIC}
