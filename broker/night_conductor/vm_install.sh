#! /bin/bash
# Installs the software required for the Nightly Conductor VM.

# install pip
apt-get update
apt-get install -y python3-pip

# download the python requirements.txt file from GCS
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
PROJECT_ID=$(curl "${baseurl}/project/project-id" -H "${H}")
bucket="${PROJECT_ID}-broker_files"
gsutil cp gs://${bucket}/night_conductor/requirements.txt .

# install the python requirements
pip3 install -r requirements.txt
