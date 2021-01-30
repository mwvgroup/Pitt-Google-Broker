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

#--- Start the consumer, if the KAFKA_TOPIC attribute is not "NONE"
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
KAFKA_TOPIC=$(curl "${baseurl}/instance/attributes/KAFKA_TOPIC" -H "${H}")
if [ "$KAFKA_TOPIC" != "NONE" ]; then
    echo
    echo "Starting the consumer..."
    ./start_consumer.sh ${testid} ${broker_bucket} ${KAFKA_TOPIC}
else
    echo
    echo "KAFKA_TOPIC attribute is 'NONE'."
    echo "The broker's consumer has NOT been started."
    echo "Use the consumer simulator instead."
    echo
fi
