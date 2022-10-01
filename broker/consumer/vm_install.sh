#! /bin/bash
# Installs the software required to run the Kafka Consumer.
# Assumes a Debian 10 OS.

#--- Get metadata attributes
# for info on working with metadata, see here
# https://cloud.google.com/compute/docs/storing-retrieving-metadata
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
consumerVM=$(curl "${baseurl}/instance/name" -H "${H}")
zone=$(curl "${baseurl}/instance/zone" -H "${H}")
PROJECT_ID=$(curl "${baseurl}/project/project-id" -H "${H}")

# parse the survey name and testid from the VM name
survey=$(echo "${consumerVM}" | awk -F "-" '{print $1}')
if [ "${consumerVM}" = "${survey}-consumer" ]; then
    testid="False"
else
    testid=$(echo "${consumerVM}" | awk -F "-" '{print $NF}')
fi

#--- GCP resources used in this script
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
# use test resources, if requested
if [ "${testid}" != "False" ]; then
    broker_bucket="${broker_bucket}-${testid}"
fi

#--- Setup the working dir
# CONNECTION REQUIREMENT: keytab authorization file must be manually uploaded here
workingdir="/home/broker/consumer"
mkdir -p "${workingdir}"
cd "${workingdir}"
gsutil -m cp -r "gs://${broker_bucket}/consumer/**" .
mv "krb5.conf" "/etc/krb5.conf"

#--- Install general utils
apt-get update
apt-get install -y wget screen software-properties-common snapd
# software-properties-common installs add-apt-repository
snap install core
snap install yq

#--- Install Java and the dev kit
# see https://www.digitalocean.com/community/tutorials/how-to-install-java-with-apt-on-debian-11
apt update
echo "Installing Java..."
apt install -y default-jre
apt install -y default-jdk
echo 'JAVA_HOME="/usr/lib/jvm/java-11-openjdk-amd64"' >> /etc/environment
source /etc/environment
echo "${JAVA_HOME}"
echo "Done installing Java."
apt update

#--- Install Confluent Platform (includes Kafka)
# see https://docs.confluent.io/platform/current/installation/installing_cp/deb-ubuntu.html
echo "Installing Confluent Platform..."
# install the key used to sign packages
wget -qO - https://packages.confluent.io/deb/6.0/archive.key | sudo apt-key add -
# add the repository
add-apt-repository "deb [arch=amd64] https://packages.confluent.io/deb/6.0 stable main"
# install
apt-get update && sudo apt-get install -y confluent-platform
echo "Done installing Confluent Platform."

#--- Install Kafka -> Pub/Sub connector
# see https://github.com/GoogleCloudPlatform/pubsub/tree/master/kafka-connector
echo "Installing the Kafka -> Pub/Sub connector"
plugindir="/usr/local/share/kafka/plugins"
CONNECTOR_RELEASE="v0.5-alpha"
mkdir -p "${plugindir}"
#- install the connector
cd "${plugindir}"
wget "https://github.com/GoogleCloudPlatform/pubsub/releases/download/${CONNECTOR_RELEASE}/pubsub-kafka-connector.jar"
echo "Done installing the Kafka -> Pub/Sub connector"

#--- Set the startup script and shutdown
startupscript="gs://${broker_bucket}/consumer/vm_startup.sh"
shutdownscript="gs://${broker_bucket}/consumer/vm_shutdown.sh"
gcloud compute instances add-metadata "${consumerVM}" \
    --zone "$zone" \
    --metadata="startup-script-url=${startupscript},shutdown-script-url=${shutdownscript}"
echo "vm_install.sh is complete. Shutting down."
shutdown -h now
