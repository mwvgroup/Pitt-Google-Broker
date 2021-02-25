#! /bin/bash
# Installs the software required to run the Kafka Consumer.
# Assumes a Debian 10 OS.

#--- Install general utils
apt-get update
apt-get install -y wget screen software-properties-common
# software-properties-common installs add-apt-repository

#--- Install Java and the dev kit
# see https://www.digitalocean.com/community/tutorials/how-to-install-java-with-apt-on-debian-10
apt update
apt install -y default-jre
apt install -y default-jdk
echo 'JAVA_HOME="/usr/lib/jvm/java-11-openjdk-amd64/bin/java"' >> /etc/environment
source /etc/environment
echo $JAVA_HOME
apt update

#--- Install Confluent Platform (includes Kafka)
# see https://docs.confluent.io/platform/current/installation/installing_cp/deb-ubuntu.html
# install the key used to sign packages
wget -qO - https://packages.confluent.io/deb/6.0/archive.key | sudo apt-key add -
# add the repository
add-apt-repository "deb [arch=amd64] https://packages.confluent.io/deb/6.0 stable main"
# install
apt-get update && sudo apt-get install -y confluent-platform

#--- Install Kafka -> Pub/Sub connector
# see https://github.com/GoogleCloudPlatform/pubsub/tree/master/kafka-connector
plugindir=/usr/local/share/kafka/plugins
CONNECTOR_RELEASE=v0.5-alpha
mkdir -p ${plugindir}
#- install the connector
cd ${plugindir}
wget https://github.com/GoogleCloudPlatform/pubsub/releases/download/${CONNECTOR_RELEASE}/pubsub-kafka-connector.jar
