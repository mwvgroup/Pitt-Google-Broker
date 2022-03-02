#! /bin/bash
# Start/setup up all GCS resources required to ingest and process
# the ZTF stream.

testid=$1
broker_bucket=$2
survey="${3:-ztf}"

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
