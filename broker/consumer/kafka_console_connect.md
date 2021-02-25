# Install Kafka and Run a Consumer (2 Methods) to Listen to the ZTF Stream

This document walks through installing Kafka and then
connecting to the ZTF alert stream via 2 different methods:
1. Console Consumer: Command-line consumer (installed with Confluent Platform) that prints alert content to `stdout`; _useful for testing the connection_.
2. Kafka Connectors: Plugins that listen to a stream and route the message to another service. _Our consumer is a Kafka -> Pub/Sub connector that simply passes the bytes through (no data decoding or conversions)._

# ToC
- [Pre-configured instance](#preconfig-instance)
- [Install Kafka (Confluent Platform) manually](#manual-install)
- [Install Kafka on a Compute Engine instance using the prepackaged, "Google Click to Deploy" stack the Google Marketplace](#gce-marketplace-install) (not recommended)
- [Console Consumer](#cons-consumer) (useful for testing the connection)
    - [Configure for ZTF access](#config)
    - [__Run the Kafka Console Consumer__](#run-consumer)
- [Kafka Connectors](#connectors) (run a consumer and route the messages to another service)
    - [General Configuration and ZTF Authentication](#config-connect)
    - [Pub/Sub Connector](#psconnect)
        - [Install and Configure](#psconnect-config)
        - [__Run the Pub/Sub Connector__](#psconnect-run)
    - [BigQuery Connector](#bqconnect)
---

<a name="preconfig-instance"></a>
## Pre-configured instance
<!-- fs -->
The example code that follows creates a Compute Engine (CE) instance called `kafka-consumer-test` and then
installs and configures both methods to listen to the ZTF stream.
(ZTF auth files are required, but not provided here.)
There is an existing CE instance, [`kafka-consumer`](https://console.cloud.google.com/compute/instancesDetail/zones/us-central1-a/instances/kafka-consumer?project=ardent-cycling-243415), that has been setup following this example.
_You(*) can log into it and test or use the methods described here to connect to ZTF without having to install or configure anything_
(see the "Run" sections below;
you could also take advantage of the installed software and auth files, but create/configure your own _working_ directory).
It is _not_ a "production" instance.
The python commands to access `kafka-consumer` are:

```python
# first start the instance
gcloud compute instances start kafka-consumer --zone us-central1-a
# then log in
gcloud beta compute ssh kafka-consumer --zone us-central1-a

# make sure you STOP the instance when you are done
# so that we don't pay for it to run
gcloud compute instances stop kafka-consumer --zone us-central1-a
```

If you need permissions to access it or use `sudo`, you should be able to grant them in the IAM section of the GCP Console.
I can help if you get stuck.

(*) Assuming "you" are a PGB member with access to the GCP project.
<!-- fe preconfigured instance -->

---

<a name="manual-install"></a>
## Install Kafka (Confluent Platform) manually
<!-- fs -->
[Confluent Platform](https://docs.confluent.io/1.0/platform.html#what-is-the-confluent-platform) is a collection of tools (including Kafka) to run and manage data streams.
In some sense, installing the full platform is overkill (listening to a stream requires fewer tools than producing a stream).
However, it's worth it:
1) This is a (the?) standard way to install Kafka, so it becomes easier to follow online examples/tutorials and to troubleshoot with ZTF folks;
2) The tasks we need to accomplish (testing and running connections) run smoothly using Confluent Platform
(the same cannot be said of other methods I and we have tried); and
3) It's easy to imagine needing some of the other components in the package down the road.

Instruction Links:
- [`gcloud compute instances create`](https://cloud.google.com/sdk/gcloud/reference/compute/instances/create)
- [How To Install Java with Apt on Debian 10](https://www.digitalocean.com/community/tutorials/how-to-install-java-with-apt-on-debian-10)
- [Confluent Platform: Manual Install on Ubuntu and Debian](https://docs.confluent.io/platform/current/installation/installing_cp/deb-ubuntu.html)

See [`vm_install.sh`](vm_install.sh) for a quick list of the commands required for steps 2 and 3.
(this file is used to set up the production instance `ztf-consumer`).

1. (Optional) Create a Compute Engine VM instance (Debian 10):

```bash
# configs
instancename=kafka-consumer-test
machinetype=e2-standard-2
zone=us-central1-a

# create the instance
gcloud compute instances create ${instancename} \
    --zone=${zone} \
    --machine-type=${machinetype} \
    --scopes=cloud-platform \
    --metadata=google-logging-enabled=true \
    --tags=ztfport # firewall rule, opens port used by Kafka/ZTF

# log in
gcloud compute ssh ${instancename} --zone=${zone}
```

2. Install Java and the Java Development Kit (JDK).
    - Debian 10 instructions are at the link above.
    - From that page you can select different versions or distributions.
    - I used the "Default" OpenJDK option.
    - Be sure to set the `JAVA_HOME` environment variable; instructions at the bottom of the page.

3. Install the Confluent Platform. This installs Kafka + additional tools.
    - Follow the instructions in in the "Get the Software" section of the Confluent Platform link above.
    - See links on LHS of the page for RHEL, CentOS, or Docker installs.

<!-- fe Install Confluent Platform manually -->

<a name="gce-marketplace-install"></a>
## Install Kafka on a Google Compute Engine VM using the prepackaged, "Click to Deploy" stack on the Google Marketplace
<!-- fs -->
Note: this does _not_ install Confluent Platform,
and so it cannot be used with Confluent Hub which manages many of the available [Kafka Connectors](#connectors). (The [Pub/Sub connector](#psconnect) that we use is maintained by Pub/Sub developers and does _not_ require Confluent Hub). Also, it installs Kafka to
The manual install method (above) is smooth, and is a more standard setup.
__*For these reasons, I do not recommend this "Click to Deploy" method (and the broker does not use it).*__
Really, this section can probably be deleted.

1. Go to the [Kafka, Click to Deploy stack on Google Marketplace](https://console.cloud.google.com/marketplace/product/click-to-deploy-images/kafka?q=kafka&id=f19a0f63-fc57-47fd-9d94-8d5ca6af935e&project=ardent-cycling-243415&folder=&organizationId=)
2. Click "Launch", fill in VM configuration info
    - This will spin up a VM and install Kafka, Java, and other necessary packages.

You can view the deployment at [GCP Console: Deployments](https://console.cloud.google.com/dm/deployments)

Helpful notice from GCP:
__"Kafka has been installed into /opt/kafka. Here you will find kafka config files and provided scripts. Documentation on configuration can be found [here](https://www.google.com/url?q=https%3A%2F%2Fkafka.apache.org%2Fdocumentation%2F%23configuration). You can also restart the kafka server by running the below command."__
```bash
sudo systemctl restart kafka
```

`ssh` into the VM from the GCP Console Deployments or VM instances pages, or the following:
```bash
gcloud beta compute ssh --zone "us-west3-c" "kafka-1-vm" --project "ardent-cycling-243415"
```

Set `JAVA_HOME` env variable following instructions in doc linked in previous section.

_[ToDo:] Create an "image" or a "machine image" of this VM and figure out how to use it to deploy a new ZTF consumer daily._

<!-- fe # Install on a Google Compute Engine VM -->

---

<a name="cons-consumer"></a>
# Console Consumer
<!-- fs -->
`kafka-console-consumer.sh` is a command line utility that creates a consumer and prints the messages to the terminal. It is useful for testing the connection.

<a name="config"></a>
## Configure for ZTF access
<!-- fs -->
The following instructions are pieced together from:
- [Kafka Consumer Configs](https://kafka.apache.org/documentation/#consumerconfigs)
- [SASL configuration for Kafka Clients](https://docs.confluent.io/3.0.0/kafka/sasl.html#sasl-configuration-for-kafka-clients)
- [Confluent Kafka Consumer](https://docs.confluent.io/platform/current/clients/consumer.html)
- info I got from Christopher Phillips over phone/email.

1. Find out where Kafka is installed.
On the VM using Marketplace, it is in `/opt/kafka`.
On the VM using manual install of Confluent Platform, components are scattered around a bit; look in:
    - `/etc/kafka` (example properties and config files)
    - `/bin` (e.g., for `kafka-console-consumer` and `confluent-hub`)
The following assumes we are on the VM with Confluent Platform.

2. Create a working directory. In the following I use `/home/ztf_consumer`

2. This requires two authorization files (not provided here):
    1. `krb5.conf`, which should be at `/etc/krb5.conf`
    2. `pitt-reader.user.keytab`. I store this in the directory `/home/ztf_consumer`; we need the path for config below.

3. Create `kafka_client_jaas.conf ` in your working directory containing (change the `keyTab` path if needed):
```
KafkaClient {
    com.sun.security.auth.module.Krb5LoginModule required 
    useKeyTab=true 
    storeKeyTab=true 
    debug=true
    serviceName="kafka" 
    keyTab="/home/ztf_consumer/pitt-reader.user.keytab" 
    principal="pitt-reader@KAFKA.SECURE" 
    useTicketCache=false; 
};
```
Make sure there are no extra spaces at the ends of the lines,
else the connection will not succeed.

4. Set an environment variable so Java can find the file we just created:
```bash
export KAFKA_OPTS="-Djava.security.auth.login.config=/home/ztf_consumer/kafka_client_jaas.conf"
```

5. Setup the Kafka config file `consumer.properties`.
Sample config files are provided with the installation in `/opt/kafka/config/` (Marketplace VM) or `/etc/kafka/` on the manual install VM.
Create a `consumer.properties` file in your working directory that contains the following:

```bash
bootstrap.servers=public2.alerts.ztf.uw.edu:9094
group.id=group
session.timeout.ms=6000
enable.auto.commit=False
sasl.kerberos.kinit.cmd='kinit -t "%{sasl.kerberos.keytab}" -k %{sasl.kerberos.principal}'
sasl.kerberos.service.name=kafka
security.protocol=SASL_PLAINTEXT
sasl.mechanism=GSSAPI
auto.offset.reset=earliest
```

<!-- fe Configure for ZTF access  -->

<a name="run-consumer"></a>
## Run the Kafka Console Consumer
<!-- fs -->
The following assumes we are using the manual install VM.

```bash
# make sure the KAFKA_OPTS env variable is set
export KAFKA_OPTS="-Djava.security.auth.login.config=/home/ztf_consumer/kafka_client_jaas.conf"

# Set the topic and run the console consumer
topicday=20210105  # yyyymmdd, must be within 7 days of present
cd /bin
./kafka-console-consumer \
    --bootstrap-server public2.alerts.ztf.uw.edu:9094 \
    --topic ztf_${topicday}_programid1 \
    --consumer.config /home/ztf_consumer/consumer.properties
# final argument should point to the consumer.properties file created above
```

After a few moments, if the connection is successful you will see encoded alerts printing to `stdout`.
Use `control-C` to stop consuming.

<!-- fe Run the Kafka Consumer -->
<!-- fe Console Consumer -->

---

<a name="connectors"></a>
# Kafka Connectors
<!-- fs -->
Kafka connectors run a Kafka consumer and route the messages to another service.

<a name="config-connect"></a>
## General Configuration and ZTF Authentication

The following uses instructions at:
- [Getting Started with Kafka Connect](https://docs.confluent.io/home/connect/userguide.html)

1. Create a directory to store the connectors (plugins):
```bash
mkdir /usr/local/share/kafka/plugins
```

2. To use connectors, the `.properties` file called when running the consumer/connector must include the following:
```bash
plugin.path=/usr/local/share/kafka/plugins
```

3. Create a working directory. In the following I use `/home/ztf_consumer`

4. Two authorization files are required:
    1. `krb5.conf`, which should be at `/etc/krb5.conf`
    2. `pitt-reader.user.keytab`. I store this in the directory `/home/ztf_consumer`; we need the path for config below.


<!-- fe Kafka Connectors main -->

<a name="psconnect"></a>
## Pub/Sub Connector
<!-- fs -->
We use a Kafka-Pub/Sub connector ([`kafka-connector`](https://github.com/GoogleCloudPlatform/pubsub/tree/master/kafka-connector)) that is maintained by Pub/Sub developers.
There is another connector managed by Confluent ([here](https://www.confluent.io/hub/confluentinc/kafka-connect-gcp-pubsub)) but it only supports a Pub/Sub _source_ (i.e., Pub/Sub -> Kafka), we need a Pub/Sub _sink_.

We pass the alert bytes straight through to Pub/Sub without decoding or converting them.

<a name="psconnect-config"></a>
### Install and Configure
<!-- fs -->
The following instructions were pieced together from:
- Installation:
    - [Getting Started with Kafka Connect](https://docs.confluent.io/home/connect/userguide.html)
    - the `copy_tool.py` file provided with connector (see the [repo](https://github.com/GoogleCloudPlatform/pubsub/tree/master/kafka-connector) )
- Configuration:
    - Worker configuration:
        - [Configuring and Running Workers](https://docs.confluent.io/home/connect/userguide.html#configuring-and-running-workers)
        - [Worker Configuration Properties](https://docs.confluent.io/platform/current/connect/references/allconfigs.html)
        - [Configuring Key and Value Converters](https://docs.confluent.io/home/connect/userguide.html#connect-configuring-converters)
        - [Configuring GSSAPI: Kafka Connect](https://docs.confluent.io/platform/current/kafka/authentication_sasl/authentication_sasl_gssapi.html#kconnect-long)
        - [Consumer Overrides](https://docs.confluent.io/home/connect/userguide.html#producer-and-consumer-overrides)
    - Connector configuration:
        - [CloudPubSubConnector Sink Configuration Properties](https://github.com/GoogleCloudPlatform/pubsub/tree/master/kafka-connector#sink-connector)
        - Example config files, which you can find at:
            - `/etc/kafka/connect-standalone.properties`
            - `/etc/kafka/connect-distributed.properties`
            - [`cps-sink-connector.properties`](https://github.com/GoogleCloudPlatform/pubsub/blob/master/kafka-connector/config/cps-sink-connector.properties)

The connector can be configured to run in "standalone" or "distributed" mode.
Distributed is recommended for production environments, partly due to its fault tolerance.
I initially tried distributed, but:
a) I got confused about where to put the connector configs, and
b) I'm not totally clear on what the distributed-specific worker options are and what they do.
Starting with standalone mode for the following
(but we should probably switch at some point):

__Install__
```bash
# navigate to the directory created above to store connectors
cd /usr/local/share/kafka/plugins
# download the .jar file
CONNECTOR_RELEASE=v0.5-alpha
sudo wget https://github.com/GoogleCloudPlatform/pubsub/releases/download/${CONNECTOR_RELEASE}/pubsub-kafka-connector.jar
# now the plugin is installed
```

__Configure__

__Worker configuration__

```bash
# navigate to the working directory created when configuring Kafka for ZTF
cd /home/ztf_consumer
```

Create a file called `psconnect-worker.properties` containing the following:
```bash
plugin.path=/usr/local/share/kafka/plugins
# ByteArrayConverter provides a “pass-through” option that does no conversion
key.converter=org.apache.kafka.connect.converters.ByteArrayConverter
value.converter=org.apache.kafka.connect.converters.ByteArrayConverter
offset.storage.file.filename=/tmp/connect.offsets
# Flush much faster than normal, which is useful for testing/debugging
# offset.flush.interval.ms=10000

# workers need to use SASL
sasl.mechanism=GSSAPI
sasl.kerberos.service.name=kafka
security.protocol=SASL_PLAINTEXT
sasl.jaas.config=com.sun.security.auth.module.Krb5LoginModule required \
   useKeyTab=true \
   storeKeyTab=true \
   serviceName="kafka" \
   keyTab="/home/ztf_consumer/pitt-reader.user.keytab" \
   principal="pitt-reader@KAFKA.SECURE" \
   useTicketCache=false;

# connecting to ZTF
bootstrap.servers=public2.alerts.ztf.uw.edu:9094
# group.id=group
# session.timeout.ms=6000
# enable.auto.commit=False
# sasl.kerberos.kinit.cmd='kinit -t "%{sasl.kerberos.keytab}" -k %{sasl.kerberos.principal}'
consumer.auto.offset.reset=earliest
consumer.sasl.mechanism=GSSAPI
consumer.sasl.kerberos.service.name=kafka
consumer.security.protocol=SASL_PLAINTEXT
consumer.sasl.jaas.config=com.sun.security.auth.module.Krb5LoginModule required \
   useKeyTab=true \
   storeKeyTab=true \
   serviceName="kafka" \
   keyTab="/home/ztf_consumer/pitt-reader.user.keytab" \
   principal="pitt-reader@KAFKA.SECURE" \
   useTicketCache=false;
```

__Connector configuration__

Create a file in your working directory called `ps-connector.properties` containing the following:
```bash
name=ps-sink-connector-ztf
connector.class=com.google.pubsub.kafka.sink.CloudPubSubSinkConnector
tasks.max=10
# set ZTF Kafka the topic
topics=ztf_20210107_programid1
# set our Pub/Sub topic and configs
cps.topic=ztf_alert_data-kafka_consumer
cps.project=ardent-cycling-243415
# include Kafka topic, partition, offset, timestamp as msg attributes
metadata.publish=true
```
<!-- fe Install and Configure -->

<a name="psconnect-run"></a>
### Run the Pub/Sub Connector
<!-- fs -->
```bash
cd /bin
# if you want to leave it running and disconnect your terminal from the VM:
screen
# if needed, change the Kafka/ZTF topic (must be within 7 days of present)
# or other configs in the .properties files called below
./connect-standalone \
    /home/ztf_consumer/psconnect-worker.properties \
    /home/ztf_consumer/ps-connector.properties
```

This will start up a Kafka consumer and route the messages to Pub/Sub.
After a few minutes, if it is working correctly, you will see log messages similar to
```
INFO WorkerSinkTask{id=ps-sink-connector-ztf-0} Committing offsets asynchronously using sequence number 3
```
and messages streaming into the Pub/Sub topic [`ztf_alert_data-kafka_consumer`](https://console.cloud.google.com/cloudpubsub/topic/detail/ztf_alert_data-kafka_consumer?project=ardent-cycling-243415).

<!-- fe Run the Pub/Sub Connector -->
<!-- fe Pub/Sub Connector -->

<a name="bqconnect"></a>
## BigQuery Connector
<!-- fs -->
This exists and it is free (some connectors require a Confluent Enterprise License), but I haven't actually tried it.

One question that I haven't been able to find the answer to is this:
_If we run two Kafka connectors, does that create two separate connections to ZTF, or do both connectors use the same incoming stream?_
We could just install this and try it; I just haven't done it yet.
I'm guessing it would be bad form (cost more money on both ends) to pull in two connections every night.

- [Google BigQuery Sink Connector for Confluent Platform](https://docs.confluent.io/kafka-connect-bigquery/current/index.html)
- [BigQuery Quotas and Limits: Streaming Inserts](https://cloud.google.com/bigquery/quotas#streaming_inserts)

<!-- fe BigQuery Connector -->
