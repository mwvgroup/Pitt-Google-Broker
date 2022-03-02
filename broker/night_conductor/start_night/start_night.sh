#! /bin/bash
# Start/setup up all GCS resources required to ingest and process
# the ZTF stream.

PROJECT_ID=$1
testid=$2
broker_bucket=$3
survey="${4:-ztf}"

brokerdir=/home/broker
mkdir -p "${brokerdir}"

#--- Start the consumer, if the KAFKA_TOPIC attribute is not "NONE"
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
KAFKA_TOPIC=$(curl "${baseurl}/instance/attributes/KAFKA_TOPIC" -H "${H}")
if [ "${KAFKA_TOPIC}" != "NONE" ]; then
    echo
    echo "Starting the consumer..."
    ./start_consumer.sh "${testid}" "${broker_bucket}" "${KAFKA_TOPIC}" "${survey}"
else
    echo "KAFKA_TOPIC attribute is 'NONE'... skipping Consumer startup."
fi
