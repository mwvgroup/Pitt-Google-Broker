#! /bin/bash
# Start/setup up all GCS resources required to ingest and process
# the ZTF stream.

PROJECT_ID=$1
testid=$2
broker_bucket=$3

brokerdir=/home/broker
mkdir -p ${brokerdir}

#--- Reset Pub/Sub counters
echo
echo "Resetting Pub/Sub counters..."
./reset_ps_counters.sh ${PROJECT_ID} ${testid}

#--- Start the Beam/Dataflow jobs
echo
echo "Starting Dataflow Beam jobs..."
./start_beam_jobs.sh ${PROJECT_ID} ${testid} ${brokerdir} ${broker_bucket}

# Start the consumer
./start_consumer.sh ${testid} ${broker_bucket}
