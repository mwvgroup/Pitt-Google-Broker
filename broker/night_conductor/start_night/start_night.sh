#! /bin/bash
# Start/setup up all GCS resources required to ingest and process
# the ZTF stream.

PROJECT_ID=$1
bucket=$2

brokerdir=/home/broker
mkdir -p ${brokerdir}

# Reset Pub/Sub counters
./reset_ps_counters.sh ${PROJECT_ID}

# Start the Beam/Dataflow jobs
./start_beam_jobs.sh ${PROJECT_ID} ${brokerdir} ${bucket}

# Start the consumer
./start_consumer.sh ${bucket}
