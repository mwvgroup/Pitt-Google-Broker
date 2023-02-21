#! /bin/bash
"""Setup Cloud resources needed to ingest tarballs from the ZTF alert archive.

This file is NOT meant to be called as a script.
Its contents are intended to be run manually.
"""
TESTID="raenarch"  # choose your own testid
PROJECT_ID="${GOOGLE_CLOUD_PROJECT}"
echo $PROJECT_ID

bucket="${PROJECT_ID}-ztf-alerts-${TESTID}"
dataset="ztf_alerts_${TESTID}"
vmname="ingest-ztfarchive-${TESTID}"
zone='us-central1-a'

gsutil mb "gs://${bucket}"
gcloud storage buckets add-iam-policy-binding "gs://${bucket}" \
    --member="allUsers" \
    --role="roles/storage.objectViewer"
# gsutil -m rm -r "gs://${bucket}"

bq mk "${dataset}"
# bq rm "${dataset}"
# bq rm --table "${dataset}.${table}"

# VM
#
# after watching it run, we seem to need hi cpu/memory
# for example: https://cloud.google.com/compute/docs/general-purpose-machines#n1-high-cpu
# note these are vcpus == threads, not cores
# disksize="200GB"
# machinetype="n1-highcpu-32"
installscript="""#! /bin/bash
echo 'GCP_PROJECT=${PROJECT_ID}' >> /etc/environment
echo 'TESTID=${TESTID}' >> /etc/environment
echo 'SURVEY=ztf' >> /etc/environment
apt-get update
apt-get install -y wget python3-pip screen
gcloud compute instances remove-metadata ${vmname} --zone=${zone} --keys=startup-script
"""
# gcloud compute instances create "${vmname}" \
#     --zone="${zone}" \
#     --machine-type="${machinetype}" \
#     --boot-disk-size="${disksize}" \
#     --scopes="cloud-platform" \
#     --metadata="google-logging-enabled=false,startup-script=${installscript}"
# will get warning about partition resizing but i've ignored it and seems fine
# gcloud compute instances delete "${vmname}"

# ----- big
# standard disk space is actually networked storage
# a local ssd drive is faster, allows more IOPS, etc.
# https://cloud.google.com/compute/docs/disks/add-local-ssd#gcloud
# machinetype="custom-16-32768"  # 32768 = 32G
machinetype="custom-32-49152"  # 49152 = 48G
# gcloud compute instances create "${vmname}-big" \
gcloud compute instances create "${vmname}-2020" \
    --local-ssd="interface=SCSI,device-name=localssd" \
    --zone="${zone}" \
    --machine-type="${machinetype}" \
    --scopes="cloud-platform" \
    --metadata="google-logging-enabled=false,startup-script=${installscript}"
# gcloud compute instances delete "${vmname}"

# allow installscript to run for a few minutes.
# then ssh in and finish the install:
gcloud compute ssh "${vmname}"

# install Ops Agent so we can monitor cpu/memory usage on web console
curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
sudo bash add-google-cloud-ops-agent-repo.sh --also-install
rm add-google-cloud-ops-agent-repo.sh

# the ssd must be reformatted and mounted
# it must be remounted after reboot, and data is *not* persisted
# lsblk
ssdname="localssd"
mntdir="${ssdname}"
sudo mkfs.ext4 -F "/dev/${ssdname}"  # this erases the disk
sudo mkdir -p "/mnt/disks/${mntdir}"
sudo mount "/dev/${ssdname}" "/mnt/disks/${mntdir}"  # repeat after reboot
sudo chmod a+w "/mnt/disks/${mntdir}"

# manually install conda, then broker_utils
# accept conda defaults *except* accept the license and say yes to last question:
# Do you wish the installer to initialize Anaconda3 by running conda init?
# (need conda to avoid version issues with astropy/jinja2/MarkupSafe/soft_unicode)
wget https://repo.anaconda.com/archive/Anaconda3-2022.05-Linux-x86_64.sh
bash Anaconda3-2022.05-Linux-x86_64.sh
rm Anaconda3-2022.05-Linux-x86_64.sh
source ~/.bashrc
conda create -n pgb python=3.7
conda activate pgb
# we don't use this much but it installs several other dependencies we need
pip3 install pgb-broker-utils
pip3 uninstall fastavro
pip3 install fastavro==1.4.4
pip3 install lxml
pip3 install ipython  # optional

# now everything should be ready for ingest_tarballs.run()
