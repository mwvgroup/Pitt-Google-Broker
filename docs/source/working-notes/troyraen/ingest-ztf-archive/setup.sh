#! /bin/bash
"""Setup Cloud resources needed to ingest tarballs from the ZTF alert archive.

This file is not meant to be called as a script.
Its contents are intended to be run manually.
"""
testid="raenarch"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT}"
echo $PROJECT_ID

bucket="${PROJECT_ID}-ztf-alert_avros-${testid}"
dataset="ztf_alerts_${testid}"
vmname="ingest-ztfarchive-${testid}"
zone='us-central1-a'

gsutil mb "gs://${bucket}"
# gsutil -m rm -r "gs://${bucket}"

bq mk "${dataset}"
# bq rm "${dataset}"
# bq rm --table "${dataset}.${table}"

# VM
installscript="""#! /bin/bash
echo 'GCP_PROJECT=${PROJECT_ID}' >> /etc/environment
echo 'TESTID=${testid}' >> /etc/environment
echo 'SURVEY=ztf' >> /etc/environment
apt-get update
apt-get install -y wget python3-pip screen
gcloud compute instances remove-metadata ${vmname} --zone=${zone} --keys=startup-script
"""
gcloud compute instances create "${vmname}" \
    --zone="${zone}" \
    --machine-type="n1-highcpu-16" \
    --boot-disk-size="200GB" \
    --scopes="cloud-platform" \
    --metadata="google-logging-enabled=true,startup-script=${installscript}"
    # --machine-type="n1-standard-4" \
# gcloud compute instances delete "${vmname}"

# allow installs to run for a few minutes. then:
gcloud compute ssh "${vmname}"
# install Ops Agent to monitor resource usage
curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
sudo bash add-google-cloud-ops-agent-repo.sh --also-install
rm add-google-cloud-ops-agent-repo.sh
# manual install conda, then broker_utils.
# need conda to avoid issues with astropy/jinja2/MarkupSafe/soft_unicode
wget https://repo.anaconda.com/archive/Anaconda3-2022.05-Linux-x86_64.sh
bash Anaconda3-2022.05-Linux-x86_64.sh
rm Anaconda3-2022.05-Linux-x86_64.sh
source ~/.bashrc
conda create -n pgb python=3.7
conda activate pgb
pip3 install pgb-broker-utils
pip3 uninstall fastavro
pip3 install fastavro==1.4.4
pip3 install lxml
pip3 install ipython
