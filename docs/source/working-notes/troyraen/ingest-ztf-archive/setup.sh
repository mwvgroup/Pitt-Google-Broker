#! /bin/bash
"""Setup Cloud resources needed to ingest tarballs from the ZTF alert archive.

This file is NOT meant to be called as a script.
Its contents are intended to be run manually.
"""
TESTID="raenarch"  # choose your own testid
PROJECT_ID="${GOOGLE_CLOUD_PROJECT}"
echo $PROJECT_ID

# set some variables
schema_version="3_3"
bucket="${PROJECT_ID}-ztf_alerts_v${schema_version}-${TESTID}"
dataset="ztf_${TESTID}"
vmname="ingest-ztfarchive-${TESTID}"
region="us-central1"
zone="${region}-a"

# create bucket
gsutil mb -l "${region}" "gs://${bucket}"
gsutil uniformbucketlevelaccess set on "gs://${bucket}"
gsutil requesterpays set on "gs://${bucket}"
gcloud storage buckets add-iam-policy-binding "gs://${bucket}" \
    --member="allUsers" \
    --role="roles/storage.objectViewer"
# gsutil -m rm -r "gs://${bucket}"
# gsutil ls gs://${bucket} > alerts-in-bucket.txt

# create datset
bq mk --location "${region}" "${dataset}"
# bq rm "${dataset}"
# bq rm --table "${dataset}.${table}"

# create VMs
#
installscript="""#! /bin/bash
echo 'GCP_PROJECT=${PROJECT_ID}' >> /etc/environment
echo 'TESTID=${TESTID}' >> /etc/environment
echo 'SURVEY=ztf' >> /etc/environment
apt-get update
apt-get install -y wget python3-pip screen
gcloud compute instances remove-metadata ${vmname} --zone=${zone} --keys=startup-script
"""
#
# big machine with ssd used for bulk of the work
# need hi cpu/memory for example: https://cloud.google.com/compute/docs/general-purpose-machines#n1-high-cpu
# standard disk space is actually networked storage
# a local ssd drive is faster, allows more IOPS, etc.
# machines with ssd cannot be turned off, only deleted.
# https://cloud.google.com/compute/docs/disks/add-local-ssd#gcloud
# https://cloud.google.com/compute/docs/disks/performance?_ga=2.32094903.-865460638.1622387917#performance_limits
# https://cloud.google.com/compute/docs/disks/optimizing-pd-performance
machinetype="custom-32-49152"  # 49152 = 48G
gcloud compute instances create "${vmname}" \
    --local-ssd="interface=SCSI" \
    --zone="${zone}" \
    --machine-type="${machinetype}" \
    --scopes="cloud-platform" \
    --metadata="google-logging-enabled=false,startup-script=${installscript}"
# will get warning about partition resizing but i've ignored it and seems fine
# gcloud compute instances delete "${vmname}"

# smaller machine without ssd just for load bucket -> table
machinetype="e2-custom-6-16896"  # 6 vCPU, 16.5 GB mem
disksize="20GB"  # need just a little more than default of 10 GB
gcloud compute instances create "${vmname}" \
    --zone="${zone}" \
    --machine-type="${machinetype}" \
    --boot-disk-size="${disksize}" \
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

# the ssd must be reformatted and mounted (only needed for machine with ssd)
# list the devices
lsblk
# find the name of the device with 375G and enter it below
ssdname="sdb"
mntdir="localssd"
sudo mkfs.ext4 -F "/dev/${ssdname}"  # this erases the disk
sudo mkdir -p "/mnt/disks/${mntdir}"
sudo mount "/dev/${ssdname}" "/mnt/disks/${mntdir}"
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
pip install db-dtypes # for bigquery query -> pandas df
pip3 uninstall fastavro
pip3 install fastavro==1.4.4
pip3 install lxml
pip3 install ipython  # optional

# now everything should be ready for ingest_tarballs.run()


gcloud compute instances set-machine-type $vmname --machine-type e2-highmem-8
