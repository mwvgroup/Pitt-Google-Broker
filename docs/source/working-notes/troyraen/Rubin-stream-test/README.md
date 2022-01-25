# Connect Pitt-Google to the Rubin alert stream testing deployment

December 2021

Details and access credentials were sent to us by Eric Bellm via email.
Spencer Nelson provided some additional details specific to our Kafka Connect consumer.
Here are some links for reference:

- Connecting: https://github.com/lsst-dm/sample_alert_info#obtaining-the-data-with-kafka
- Schemas: https://alert-schemas-int.lsst.cloud/
- `consumer.properties` config file example: https://github.com/lsst-dm/sample_alert_info/tree/main/examples/alert_stream_integration_endpoint/java_console_consumer
- Using schema registry with Kafka Connect: https://docs.confluent.io/platform/7.0.1/schema-registry/connect.html. Spencer says, "Our stream uses Avro for the message values, not keys (we don't set the key to anything in particular), so you probably want the `value.converter` properties."
- Tools and libraries for VOEvents: https://wiki.ivoa.net/twiki/bin/view/IVOA/IvoaVOEvent#Tools_and_Libraries

# Setup

Clone the repo, checkout the branch, cd into the directory:

```bash
git clone https://github.com/mwvgroup/Pitt-Google-Broker.git
git checkout u/tjr/rubin

cd Pitt-Google-Broker
```

Define variables used below in multiple calls

```bash
PROJECT_ID="avid-heading-329016"  # project: pitt-google-broker-user-test
survey="rubin"
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
consumerVM="${survey}-consumer"
firewallrule="tcpport9094"

# Replace KAFKA_PASSWORD with the appropriate value.
# Contact Troy Raen if you don't know the password.
KAFKA_USERNAME="pittgoogle-idfint"
KAFKA_PASSWORD=""

PUBSUB_TOPIC="rubin-alerts"
KAFKA_TOPIC="alerts-simulated"
```

GCP setup

```bash
# create the broker_bucket (only needs to be done once, per project)
gsutil mb "gs://${broker_bucket}"
# upload consumer files
o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
gsutil -m -o "$o" cp -r broker/consumer "gs://${broker_bucket}"

# create firewall rule to open port 9094
gcloud compute firewall-rules create "$firewallrule" \
    --allow=tcp:9094 \
    --description="Allow incoming traffic on TCP port 9094" \
    --direction=INGRESS \
    --enable-logging
```

# Create a Pub/Sub topic and subscription for Rubin alerts

```bash
gcloud pubsub topics create $PUBSUB_TOPIC
gcloud pubsub subscriptions create $PUBSUB_TOPIC --topic=$PUBSUB_TOPIC
```

# Create a Rubin Consumer VM

```bash
# define variables
zone="us-central1-a"
machinetype_setup="e2-standard-2"
machinetype_production="g1-small"
installscript="gs://${broker_bucket}/consumer/vm_install.sh"

# create VM
gcloud compute instances create "$consumerVM" \
    --zone="$zone" \
    --machine-type="$machinetype_setup" \
    --scopes=cloud-platform \
    --metadata=google-logging-enabled=true,startup-script-url="$installscript" \
    --tags="$firewallrule"

# wait until the consumer VM completes the install script and shuts down
# then change the machine type
gcloud compute instances set-machine-type "$consumerVM" \
    --machine-type="$machinetype_production"
```

# Ingest the Rubin test stream

Reference links:

- [Rubin sample alerts: obtaining the data with Kafka](https://github.com/lsst-dm/sample_alert_info#obtaining-the-data-with-kafka)
- [Rubin Alert Stream Integration Endpoint](https://github.com/lsst-dm/sample_alert_info/blob/main/doc/alert_stream_integration_endpoint.md)
- [Rubin example: java console consumer](https://github.com/lsst-dm/sample_alert_info/tree/main/examples/alert_stream_integration_endpoint/java_console_consumer)

## Setup

```bash
# start the consumer vm and ssh in
gcloud compute instances start "$consumerVM"
gcloud compute ssh "$consumerVM"

# define some variables
brokerdir=/home/broker
workingdir="${brokerdir}/consumer/rubin"
# Also define the variables defined in the "Setup" section
# at the very top of this README file.

# download config files from broker_bucket
sudo mkdir "$brokerdir"
sudo gsutil -m cp -r "gs://${broker_bucket}/consumer" "$brokerdir"

# set these values in the two config files
sudo sed -i "s/KAFKA_PASSWORD/${KAFKA_PASSWORD}/g" "${workingdir}/admin.properties"
sudo sed -i "s/KAFKA_PASSWORD/${KAFKA_PASSWORD}/g" "${workingdir}/psconnect-worker.properties"

# set java env variable
export JAVA_HOME="/usr/lib/jvm/java-11-openjdk-amd64"
```

## Check available Kafka topics

```bash
/bin/kafka-topics \
    --bootstrap-server alert-stream-int.lsst.cloud:9094 \
    --list \
    --command-config "${workingdir}/admin.properties"
# should see output that includes the topic: alerts-simulated
```

## Test the topic connection using the Kafka console consumer

Make a file called 'consumer.properties' and fill it with this
(change `KAFKA_PASSWORD` to the appropriate value):

```bash
security.protocol=SASL_SSL
sasl.mechanism=SCRAM-SHA-512

sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required \
  username="pittgoogle-idfint"\
  password="KAFKA_PASSWORD";
```

Run the Kafka console consumer

```bash
sudo /bin/kafka-avro-console-consumer \
    --bootstrap-server alert-stream-int.lsst.cloud:9094 \
    --group "${KAFKA_USERNAME}-example-javaconsole" \
    --topic "$KAFKA_TOPIC" \
    --property schema.registry.url=https://alert-schemas-int.lsst.cloud \
    --consumer.config consumer.properties \
    --timeout-ms=60000
# should see a lot of JSON flood the terminal
```
