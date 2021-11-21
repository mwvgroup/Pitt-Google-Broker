#! /bin/bash
#
# To create the troy VM:
# installscript="gs://ardent-cycling-243415-troy-broker_files/vm_install.sh"
# machinetype="n2-standard-4"
# zone="us-central1-a"
# gcloud compute instances create troy \
#     --zone="$zone" \
#     --machine-type="$machinetype" \
#     --scopes=cloud-platform \
#     --metadata=google-logging-enabled=true,startup-script-url="$installscript"


#--- Get metadata attributes
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
PROJECT_ID=$(curl "${baseurl}/project/project-id" -H "${H}")
troyVM=$(curl "${baseurl}/instance/name" -H "${H}")
zone=$(curl "${baseurl}/instance/zone" -H "${H}")

#--- GCP resources used in this script
broker_bucket="${PROJECT_ID}-troy-broker_files"

#--- install some utils
apt-get update
apt-get install -y python3-pip wget screen software-properties-common
pip3 install ipython

# wget https://repo.anaconda.com/archive/Anaconda3-2021.05-Linux-x86_64.sh
# bash Anaconda-latest-Linux-x86_64.sh


#### night conductor install
#--- download the python requirements.txt file from GCS
gsutil cp "gs://${broker_bucket}/night_conductor/requirements.txt" .
# install
echo "Installing requirements.txt..."
pip3 install -r requirements.txt
echo "Done installing requirements.txt."


#### consumer install
#--- Install general utils
# apt-get update
# apt-get install -y wget screen software-properties-common
# software-properties-common installs add-apt-repository

#--- Install Java and the dev kit
# see https://www.digitalocean.com/community/tutorials/how-to-install-java-with-apt-on-debian-10
apt update
echo "Installing Java..."
apt install -y default-jre
apt install -y default-jdk
echo 'JAVA_HOME="/usr/lib/jvm/java-11-openjdk-amd64/bin/java"' >> /etc/environment
source /etc/environment
echo $JAVA_HOME
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
plugindir=/usr/local/share/kafka/plugins
CONNECTOR_RELEASE=v0.5-alpha
mkdir -p ${plugindir}
#- install the connector
cd ${plugindir}
wget https://github.com/GoogleCloudPlatform/pubsub/releases/download/${CONNECTOR_RELEASE}/pubsub-kafka-connector.jar
echo "Done installing the Kafka -> Pub/Sub connector"


####
echo "vm_install.sh is complete."
