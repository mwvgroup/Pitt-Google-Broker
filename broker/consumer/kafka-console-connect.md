<!-- - [GCP Console: Deployments](https://console.cloud.google.com/dm/deployments) -->
- Access the server configured as detailed below:
    - `gcloud compute instances start kafka-consumer --zone us-central1-a`
    - `gcloud beta compute ssh kafka-consumer --zone us-central1-a`
    - `gcloud compute instances stop kafka-consumer --zone us-central1-a`

---

# ToC
- [Install Kafka](#install)
    - [Install Confluent Platform manually](#local-install)
    - [on a Compute Engine VM](#gce-install)
    - [on a Compute Engine VM using the prepackaged, "Google Click to Deploy" stack the Google Marketplace.](#gce-marketplace-install)
- [Console Consumer](#cons-consumer) (useful for testing the connection)
    - [Configure Kafka for ZTF access.](#config)
    - [Run the Kafka Console Consumer](#run-consumer)
- [Kafka Connectors](#connectors) (run a consumer and route the messages to another service)
    - [Pub/Sub Connector](#psconnect)
        - [Install and Configure](#psconnect-config)
        - [__Run the Pub/Sub Connector__](#psconnect-run)
        - [Check periodically for the topic to open up](#checktopicopen)
    - [BigQuery Connector](#bqconnect)
- [Resetting Kafka consumer offsets](#offsets)
---

<a name="install"></a>
# Install Kafka
<!-- fs -->
<a name="local-install"></a>
## Option 1: Install Confluent Platform manually
<!-- fs -->
Instruction Links:
- [How To Install Java with Apt on Debian 10](https://www.digitalocean.com/community/tutorials/how-to-install-java-with-apt-on-debian-10)
- [Confluent Platform: Manual Install on Ubuntu and Debian](https://docs.confluent.io/platform/current/installation/installing_cp/deb-ubuntu.html)

1. (Optional) Create a Compute Engine VM instance (Debian 10):

```bash
# configs
instancename=kafka-consumer
machinetype=e2-standard-4
CEserviceaccount=591409139500-compute@developer.gserviceaccount.com
zone=us-central1-a

# create the instance
gcloud compute instances create ${instancename} \
    --zone=${zone} \
    --machine-type=${machinetype} \
    --service-account=${CEserviceaccount} \
    --scopes=cloud-platform \
    --metadata=google-logging-enabled=true \
    --tags=kafka-server # for the firewall rule

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
## Option 2: Install Kafka on a Google Compute Engine VM using the prepackaged, "Click to Deploy" stack on the Google Marketplace
<!-- fs -->
Note: this does _not_ install `Confluent Platform`
(it _does_ install some of the components) and
so it cannot be used with `Confluent Hub` which manages connectors
(though not the Pub/Sub sink connector, that's maintained by Pub/Sub people).
I've abandoned this method; the manual install is smooth and is a more standard setup.

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
<!-- fe Install Kafka -->

<a name="cons-consumer"></a>
# Console Consumer
<!-- fs -->
`kafka-console-consumer` is a consumer that prints the messages to the terminal. It is useful for testing the connection.

<a name="config"></a>
## Configure Kafka for ZTF access
<!-- fs -->
Following instructions:
- [Kafka Consumer Configs](https://kafka.apache.org/documentation/#consumerconfigs)
- [SASL configuration for Kafka Clients](https://docs.confluent.io/3.0.0/kafka/sasl.html#sasl-configuration-for-kafka-clients)
- [Confluent Kafka Consumer](https://docs.confluent.io/platform/current/clients/consumer.html)
- info I got from Christopher Phillips over phone/email.

1. Find out where Kafka is installed.
On the VM using Marketplace, it is in `/opt/kafka`.
On the VM using manual install of Confluent Platform, components are scattered around a bit; look in:
    - `/etc/kafka` (example properties and config files)
    - `/bin` (e.g., for `kafka-console-consumer` and `confluent-hub`)
The following assumes we are on the VM using manual install of Confluent Platform.

2. Create a working directory. In the following I use `/home/troy_raen_pitt/consume-ztf`

2. This requires two authorization files:
    1. `krb5.conf`, which should be at `/etc/krb5.conf`
    2. `pitt-reader.user.keytab`. I store this in the directory `/home/troy_raen_pitt/consume-ztf`; we need the path for config below.

3. Create `kafka_client_jaas.conf ` in your working directory containing (change the `keyTab` path if needed):
```
KafkaClient {
    com.sun.security.auth.module.Krb5LoginModule required 
    useKeyTab=true 
    storeKeyTab=true 
    debug=true
    serviceName="kafka" 
    keyTab="/home/troy_raen_pitt/consume-ztf/pitt-reader.user.keytab" 
    principal="pitt-reader@KAFKA.SECURE" 
    useTicketCache=false; 
};
```

Note: original instructions from Christopher said to use
`principal="mirrormaker/public2.alerts.ztf.uw.edu@KAFKA.SECURE" `,
but when I used that, running the console consumer (below) => complained of being asked for a password. [This answer](https://help.mulesoft.com/s/article/javax-security-auth-login-LoginException-Could-not-login-the-client-is-being-asked-for-a-password) led me to look at this `prinicpal` line and compare it to the consumer config, which has `sasl.kerberos.principal=pitt-reader@KAFKA.SECURE`. Changing the above to match.


4. Set an environment variable so Java can find the file we just created:
```bash
export KAFKA_OPTS="-Djava.security.auth.login.config=/home/troy_raen_pitt/consume-ztf/kafka_client_jaas.conf"
```


5. Setup the Kafka config file `consumer.properties`.
Sample config files are provided with the installation in `/opt/kafka/config/` (Marketplace VM) or `/etc/kafka/` on the manual install VM.
Copy `consumer.properties` into your working directory.
Edit/add the following parameters:

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

<!-- fe Configure Kafka for ZTF access  -->

<a name="run-consumer"></a>
## Run the Kafka Console Consumer
<!-- fs -->
The following assumes we are using the manual install VM.

```bash
# `ssh` into the machine if you're not already there
gcloud beta compute ssh kafka-consumer --zone us-central1-a

# Set the environment variable
export KAFKA_OPTS="-Djava.security.auth.login.config=/home/troy_raen_pitt/consume-ztf/kafka_client_jaas.conf"

# Set the topic and run the console consumer
topicday=20201228
cd /bin
./kafka-console-consumer \
    --bootstrap-server public2.alerts.ztf.uw.edu:9094 \
    --topic ztf_${topicday}_programid1 \
    --consumer.config /home/troy_raen_pitt/consume-ztf/consumer.properties
# final argument should point to the consumer.properties file created above
```

After a few moments, if the connection is successful you will see encoded alerts printing to `stdout`.
Use `control-C` to stop consuming.

<!-- fe Run the Kafka Consumer -->
<!-- fe Console Consumer -->

<a name="connectors"></a>
# Kafka Connectors
<!-- fs -->
Kafka connectors run a Kafka consumer and route the messages to another service.

__General Configuration and ZTF Authentication:__

Following:
- [Getting Started with Kafka Connect](https://docs.confluent.io/home/connect/userguide.html)

1. Create a directory to store the connectors:
```bash
mkdir /usr/local/share/kafka/plugins
```

2. To use connectors stored here, the `.properties` file called when running the consumer/connector must include the following:
```bash
plugin.path=/usr/local/share/kafka/plugins
```

3. Create a working directory. In the following I use `/home/troy_raen_pitt/consume-ztf`

4. Two authorization files are required:
    1. `krb5.conf`, which should be at `/etc/krb5.conf`
    2. `pitt-reader.user.keytab`. I store this in the directory `/home/troy_raen_pitt/consume-ztf`; we need the path for config below.


<!-- fe Kafka Connectors main -->

<a name="psconnect"></a>
## Pub/Sub Connector
<!-- fs -->
Note: there is another connector managed by Confluent, [here](https://www.confluent.io/hub/confluentinc/kafka-connect-gcp-pubsub), but it only supports a Pub/Sub _source_ (i.e., Pub/Sub -> Kafka) which is opposite of what we need.

<a name="psconnect-config"></a>
### Install and Configure
<!-- fs -->
__Install__ Pub/Sub's [kafka-connector](https://github.com/GoogleCloudPlatform/pubsub/tree/master/kafka-connector).
I pieced the following together from:
- [Getting Started with Kafka Connect](https://docs.confluent.io/home/connect/userguide.html)
- the `copy_tool.py` file provided with the `kafka-connector`

```bash
# navigate to the directory created above to store connectors
cd /usr/local/share/kafka/plugins
# download the .jar file
CONNECTOR_RELEASE=v0.5-alpha
sudo wget https://github.com/GoogleCloudPlatform/pubsub/releases/download/${CONNECTOR_RELEASE}/pubsub-kafka-connector.jar
```

__Configure__
<!-- - [Kafka Connect Config options](http://kafka.apache.org/documentation.html#connectconfigs) -->
<!-- - [Running Kafka Connect](http://kafka.apache.org/documentation.html#connect_running) -->
<!-- - `/usr/share/confluent-hub-components/confluentinc-kafka-connect-gcp-pubsub/etc/google-pubsub-quickstart.properties` -->
<!-- - [Example `cps-sink-connector.properties`](https://github.com/GoogleCloudPlatform/pubsub/blob/master/kafka-connector/config/cps-sink-connector.properties) -->

- [Configuring and Running Workers](https://docs.confluent.io/home/connect/userguide.html#configuring-and-running-workers)

The connector can be configured to run in "standalone" or "distributed" mode.
Distributed is recommended for production environments, partly due to its fault tolerance.
Tried distributed;
confused about whether all settings go in one file;
not totally clear on what the distributed-specific worker options are/what they do;
starting with standalone mode for the following:

__Worker configuration__
- [Worker Configuration Properties](https://docs.confluent.io/platform/current/connect/references/allconfigs.html)
    - [Configuring Key and Value Converters](https://docs.confluent.io/home/connect/userguide.html#connect-configuring-converters)
    - [Configuring GSSAPI: Kafka Connect](https://docs.confluent.io/platform/current/kafka/authentication_sasl/authentication_sasl_gssapi.html#kconnect-long)
    - [Consumer Overrides](https://docs.confluent.io/home/connect/userguide.html#producer-and-consumer-overrides)
- See the example config files at
    - `/etc/kafka/connect-standalone.properties`
    - `/etc/kafka/connect-distributed.properties`

```bash
# navigate to the working directory created when configuring Kafka for ZTF
cd /home/troy_raen_pitt/consume-ztf
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
   keyTab="/home/troy_raen_pitt/consume-ztf/pitt-reader.user.keytab" \
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
   keyTab="/home/troy_raen_pitt/consume-ztf/pitt-reader.user.keytab" \
   principal="pitt-reader@KAFKA.SECURE" \
   useTicketCache=false;
```

__Connector configuration__
- [CloudPubSubConnector Sink Configuration Properties](https://github.com/GoogleCloudPlatform/pubsub/tree/master/kafka-connector#sink-connector)
- See example config file
    - [`cps-sink-connector.properties`](https://github.com/GoogleCloudPlatform/pubsub/blob/master/kafka-connector/config/cps-sink-connector.properties)

Create a file called `ps-connector.properties` containing the following:
```bash
name=ps-sink-connector-ztf
connector.class=com.google.pubsub.kafka.sink.CloudPubSubSinkConnector
tasks.max=10
# set kafka the topic
topics=ztf_20201227_programid1
# set the PS configs
cps.topic=ztf_alert_data
cps.project=ardent-cycling-243415
# include Kafka topic, partition, offset, timestamp as msg attributes
metadata.publish=true
```
<!-- fe Install and Configure -->

<a name="psconnect-run"></a>
### Run the Pub/Sub Connector
<!-- fs -->
`ssh` into the machine:
```bash
gcloud beta compute ssh kafka-consumer --zone us-central1-a
```

__Start the connector__
```bash
cd /bin
screen
# if needed, change the topic or other configs in the .properties files called below
./connect-standalone \
    /home/troy_raen_pitt/consume-ztf/psconnect-worker.properties \
    /home/troy_raen_pitt/consume-ztf/ps-connector.properties
```

This will start up a Kafka consumer and route the messages to Pub/Sub.
After a few minutes, if it is working correctly, you will see log messages similar to
```
INFO WorkerSinkTask{id=ps-sink-connector-ztf-0} Committing offsets asynchronously using sequence number 3
```

<!-- fe Run the Pub/Sub Connector -->

<a name="checktopicopen"></a>
### Check periodically for the topic to open up
<!-- fs -->
This doesn't work because the consumer fails to connect to the topic
but the command just hangs, it doesn't return an error code.
```bash
# Set the environment variable
export KAFKA_OPTS="-Djava.security.auth.login.config=/home/troy_raen_pitt/consume-ztf/kafka_client_jaas.conf"
kafka-topics --list --bootstrap-server public2.alerts.ztf.uw.edu:9094
topicday=20201228
kafka-topics --describe --topic ztf_${topicday}_programid1 --bootstrap-server public2.alerts.ztf.uw.edu:9094

cd /bin
screen
# if needed, change the topic or other configs in the .properties files called below

n=0
until [ "$n" -ge 2 ]
do
    ./connect-standalone \
        /home/troy_raen_pitt/consume-ztf/psconnect-worker.properties \
        /home/troy_raen_pitt/consume-ztf/ps-connector.properties \
        && break
   n=$((n+1))
   echo ${n}
   sleep 30
done
```

<!-- fe Check periodically for the topic to open up -->
<!-- fe Pub/Sub Connector -->

<a name="bqconnect"></a>
## BigQuery Connector
<!-- fs -->
- [Google BigQuery Sink Connector for Confluent Platform](https://docs.confluent.io/kafka-connect-bigquery/current/index.html)
- [BigQuery Quotas and Limits: Streaming Inserts](https://cloud.google.com/bigquery/quotas#streaming_inserts)

<!-- fe BigQuery Connector -->

<a name="offsets"></a>
# Resetting Kafka consumer offsets
<!-- fs -->

```bash
cd /bin
server=public2.alerts.ztf.uw.edu:9094
topic=ztf_20210102_programid1
kafka-consumer-groups --bootstrap-server ${server} --group group --topic ${topic} --reset-offsets --to-earliest --execute
# does not work
```

<!-- fe Restting Kafka consumer offsets -->
