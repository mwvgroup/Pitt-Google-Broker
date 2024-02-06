# docs/source/working-notes/troyraen/Rubin-stream-test/README.md

## Connect Pitt-Google to the Rubin alert stream testing deployment

Note: The active copy of this README.md is in broker/consumer/rubin and will be kept up to date as the main LSST alert stream developments. This README.md here is specifically for this test stream.

December 2021 - Author: Troy Raen

Details and access credentials were sent to us by Eric Bellm via email.
Spencer Nelson provided some additional details specific to our Kafka Connect consumer.
Here are some links they gave us for reference, which I (Troy Raen) used to set this up:

- [Rubin sample alerts: obtaining the data with Kafka](https://github.com/lsst-dm/sample_alert_info#obtaining-the-data-with-kafka)
- [Rubin Alert Stream Integration Endpoint](https://github.com/lsst-dm/sample_alert_info/blob/main/doc/alert_stream_integration_endpoint.md)
- Schemas are stored at: https://alert-schemas-int.lsst.cloud/
- [Using schema registry with Kafka Connect](https://docs.confluent.io/platform/7.0.1/schema-registry/connect.html). Spencer says, "Our stream uses Avro for the message values, not keys (we don't set the key to anything in particular), so you probably want the `value.converter` properties."
- Tools and libraries for VOEvents: https://wiki.ivoa.net/twiki/bin/view/IVOA/IvoaVOEvent#Tools_and_Libraries
- [Rubin example: java console consumer](https://github.com/lsst-dm/sample_alert_info/tree/main/examples/alert_stream_integration_endpoint/java_console_consumer)

Rubin alert packets will be Avro serialized, but the schema will not be included with the packet.
There are several ways to handle this.
For now, I have simply passed the alert bytes straight through from Kafka to Pub/Sub and deserialized alerts after pulling from the Pub/Sub stream.
For other methods, see [Alternative methods for handling the schema](#alternative-methods-for-handling-the-schema) below.

Below is the code I used to set up the necessary resources in GCP, ingest the Rubin stream, pull messages from the resulting Pub/Sub stream and deserialize the alerts.

## Setup

Clone the repo, checkout the branch (currently `rubin`, but in the future will be merged into `master`), cd into the directory:

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
PUBSUB_SUBSCRIPTION="$PUBSUB_TOPIC"
KAFKA_TOPIC="alerts-simulated"
```

Setup resources on Google Cloud Platform.
(You must be authenticated with `gcloud` using an account that has permissions in the project defined by `PROJECT_ID` above.)

```bash
# Create a firewall rule to open port 9094 (only needs to be done once, per project)
gcloud compute firewall-rules create "$firewallrule" \
    --allow=tcp:9094 \
    --description="Allow incoming traffic on TCP port 9094" \
    --direction=INGRESS \
    --enable-logging

# Create a Cloud Storage bucket to store the consumer config files
gsutil mb "gs://${broker_bucket}"

# Upload the install script and config files for the consumer
o="GSUtil:parallel_process_count=1" # disable multiprocessing for Macs
gsutil -m -o "$o" cp -r broker/consumer "gs://${broker_bucket}"

# Create a Pub/Sub topic and subscription for Rubin alerts
gcloud pubsub topics create $PUBSUB_TOPIC
gcloud pubsub subscriptions create $PUBSUB_SUBSCRIPTION --topic=$PUBSUB_TOPIC

# Create a Rubin Consumer VM
zone="us-central1-a"
machinetype="e2-standard-2"
installscript="gs://${broker_bucket}/consumer/vm_install.sh"
gcloud compute instances create "$consumerVM" \
    --zone="$zone" \
    --machine-type="$machinetype" \
    --scopes=cloud-platform \
    --metadata=google-logging-enabled=true,startup-script-url="$installscript" \
    --tags="$firewallrule"
```

## Ingest the Rubin test stream

### Setup

```bash
# start the consumer vm and ssh in
gcloud compute instances start "$consumerVM"
gcloud compute ssh "$consumerVM"

# define some variables
brokerdir=/home/broker
workingdir="${brokerdir}/consumer/rubin"
# Also define the variables from the "Setup" section
# at the very top of this README file.
```

### Test the connection

#### Check available Kafka topics

```bash
/bin/kafka-topics \
    --bootstrap-server alert-stream-int.lsst.cloud:9094 \
    --list \
    --command-config "${workingdir}/admin.properties"
# should see output that includes the topic: alerts-simulated
```

#### Test the topic connection using the Kafka Console Consumer

Set Java env variable

```bash
export JAVA_HOME="/usr/lib/jvm/java-11-openjdk-amd64"
```

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
# if successful, you will see a lot of JSON flood the terminal
```

### Run the Kafka -> Pub/Sub connector

Setup:

```bash
# download the config files from broker_bucket
sudo mkdir "$brokerdir"
sudo gsutil -m cp -r "gs://${broker_bucket}/consumer" "$brokerdir"

# set the password in two of the config files
sudo sed -i "s/KAFKA_PASSWORD/${KAFKA_PASSWORD}/g" "${workingdir}/admin.properties"
sudo sed -i "s/KAFKA_PASSWORD/${KAFKA_PASSWORD}/g" "${workingdir}/psconnect-worker.properties"

# replace topic and project configs in ps-connector.properties
fconfig="${workingdir}/ps-connector.properties"
sudo sed -i "s/PROJECT_ID/${PROJECT_ID}/g" ${fconfig}
sudo sed -i "s/PUBSUB_TOPIC/${PUBSUB_TOPIC}/g" ${fconfig}
sudo sed -i "s/KAFKA_TOPIC/${KAFKA_TOPIC}/g" ${fconfig}
```

Run the connector:

```bash
mydir="/home/troyraen"  ## use my dir because don't have permission to write to workingdir
fout_run="${mydir}/run-connector.out"
sudo /bin/connect-standalone \
    ${workingdir}/psconnect-worker.properties \
    ${workingdir}/ps-connector.properties \
    &> ${fout_run}
```

## Pull a Pub/Sub message and open it

In the future, we should download schemas from the Confluent Schema Registry and store them.
Then for each alert, check the schema version in the Confluent Wire header, and load the schema file using `fastavro`.
See [Alternative methods for handling the schema](#alternative-methods-for-handling-the-schema) below.

For now, use the schema in the `lsst-alert-packet` library. Install the library:

```bash
pip install lsst-alert-packet
```

Following the deserialization example at
https://github.com/lsst-dm/alert_stream/blob/main/python/lsst/alert/stream/serialization.py

```python
import io
import fastavro
from google.cloud import pubsub_v1
from lsst.alert.packet import Schema

# pull a message
project_id = "avid-heading-329016"
subscription_name = "rubin-alerts"
max_messages = 5

subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_name)
request = {
    "subscription": subscription_path,
    "max_messages": max_messages,
}

response = subscriber.pull(**request)

# load the schema
latest_schema = Schema.from_file().definition

# deserialize the alerts.
# This follows the deserialization example at
# https://github.com/lsst-dm/alert_stream/blob/main/python/lsst/alert/stream/serialization.py
for received_message in response.received_messages:
    alert_bytes = received_message.message.data
    # header_bytes = alert_bytes[:5]
    # schema_version = deserialize_confluent_wire_header(header_bytes)
    content_bytes = io.BytesIO(alert_bytes[5:])
    alert_dict = fastavro.schemaless_reader(content_bytes, latest_schema)
    alertId = alert_dict['alertId']
    diaSourceId = alert_dict['diaSource']['diaSourceId']
    psFlux = alert_dict['diaSource']['psFlux']
    print(f"alertId: {alertId}, diaSourceId: {diaSourceId}, psFlux: {psFlux}")
```

## Alternative methods for handling the schema

### Download with a `GET` request, and read the alert's schema version from the Confluent Wire header

In the future, we should download schemas from the Confluent Schema Registry and store them (assuming we do not use the schema registry directly in the Kafka connector).
Then for each alert, check the schema version in the Confluent Wire header, and load the schema file using `fastavro`.

Pub/Sub topics can be configured with an Avro schema attached, but it cannot be changed once attached.
We would have to create a new topic for every schema version.
Therefore, I don't think we should do it this way.

#### Download a schema from the Confluent Schema Registry using a `GET` request

```bash
SCHEMA_REGISTRY_BASIC_AUTH_USER_INFO=$KAFKA_USERNAME:$KAFKA_PASSWORD
SCHEMA_REGISTRY_URL="https://alert-schemas-int.lsst.cloud"
schema_version=1
fout_rubinschema="rubinschema_v${schema_version}.avsc"

# get list of schema subjects
curl --silent -X GET -u $SCHEMA_REGISTRY_BASIC_AUTH_USER_INFO $SCHEMA_REGISTRY_URL/subjects
# download a particular schema
curl --silent -X GET -u $SCHEMA_REGISTRY_BASIC_AUTH_USER_INFO $SCHEMA_REGISTRY_URL/schemas/ids/${schema_version} > $fout_rubinschema
```

#### Read the alert's schema version from the Confluent Wire header

The following is copied from
https://github.com/lsst-dm/alert_stream/blob/main/python/lsst/alert/stream/serialization.py

```python
import struct

_ConfluentWireFormatHeader = struct.Struct(">bi")

def deserialize_confluent_wire_header(raw):
    """Parses the byte prefix for Confluent Wire Format-style Kafka messages.
    Parameters
    ----------
    raw : `bytes`
        The 5-byte encoded message prefix.
    Returns
    -------
    schema_version : `int`
        A version number which indicates the Confluent Schema Registry ID
        number of the Avro schema used to encode the message that follows this
        header.
    """
    _, version = _ConfluentWireFormatHeader.unpack(raw)
    return version

header_bytes = alert_bytes[:5]
schema_version = deserialize_confluent_wire_header(header_bytes)
```

### Use the Confluent Schema Registry with the Kafka Connector

Kafka Connect can use the Confluent Schema Registry directly.
But schemas are stored under subjects and Kafka Connect is picky about how those
subjects are named.
See
https://docs.confluent.io/platform/current/schema-registry/serdes-develop/index.html#subject-name-strategy
**Rubin has set the schema subject name to “alert-packet”**, which does not conform
to any of the name strategies that Kafka Connect uses.
I did not find a workaround for this issue.
Instead, I passed the alert bytes straight through into Pub/Sub and deserialized
them after pulling the messages from Pub/Sub.

If you want to try this in the future, set the following configs in the connector's psconnect-worker.properties file.

```bash
value.converter=io.confluent.connect.avro.AvroConverter
value.converter.schema.registry.url=https://alert-schemas-int.lsst.cloud
value.converter.enhanced.avro.schema.support=true
```
