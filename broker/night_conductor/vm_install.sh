#! /bin/bash
# Installs the software required for the Nightly Conductor VM.

#--- Get metadata attributes
baseurl="http://metadata.google.internal/computeMetadata/v1"
H="Metadata-Flavor: Google"
PROJECT_ID=$(curl "${baseurl}/project/project-id" -H "${H}")
nconductVM=$(curl "${baseurl}/instance/name" -H "${H}")
# parse the survey name and testid from the VM name
survey=$(echo "$nconductVM" | awk -F "-" '{print $1}')
if [ "$nconductVM" = "${survey}-night-conductor" ]; then
    testid="False"
else
    testid=$(echo "$nconductVM" | awk -F "-" '{print $NF}')
fi

#--- GCP resources used in this script
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
# use test resources, if requested
if [ "$testid" != "False" ]; then
    broker_bucket="${broker_bucket}-${testid}"
fi

#--- install pip
apt-get update
apt-get install -y python3-pip

#--- download the python requirements.txt file from GCS
gsutil cp gs://${broker_bucket}/night_conductor/requirements.txt .
# install
echo "Installing requirements.txt..."
pip3 install -r requirements.txt
echo "Done installing requirements.txt."

echo "vm_install.sh is complete"
