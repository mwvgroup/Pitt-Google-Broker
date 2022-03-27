
## broker-utils not installing on night-conductor

Solution: use a Conda environment with Python 3.7

```bash
# shart over with a fresh vm
survey=ztf
testid=brokerutils
vm_name="${survey}-night-conductor-${testid}"
gcloud compute instances stop "$vm_name"
gcloud compute instances delete "$vm_name"
machinetype=e2-standard-2
gcloud compute instances create "$vm_name" \
    --machine-type="$machinetype" \
    --scopes=cloud-platform \
    --metadata=google-logging-enabled=true
# log in
gcloud compute instances start "$vm_name"
gcloud compute ssh "$vm_name"
# install pip3 and screen
apt-get update
apt-get install -y python3-pip screen
# then install pgb-broker-utils==0.2.28
pip3 install pgb-broker-utils==0.2.28 &> install_broker_utils_0.2.28.out
# this does not succeed
# astropy requires jinja2 which requires MarkupSafe.soft_unicode
# but this was removed in v2.1.0
# https://markupsafe.palletsprojects.com/en/2.1.x/changes/#version-2-1-0
# go back to local machine and the download the log file to this directory
exit
gcloud compute scp "troyraen@${vm_name}:/home/troyraen/install_broker_utils_0.2.28.out" .

gcloud compute instances add-metadata --zone="$zone" "$vm_name" \
    --metadata "ATTRIBUTE1=${ATTRIBUTE1},ATTRIBUTE2=${ATTRIBUTE2}"


wget https://repo.anaconda.com/archive/Anaconda3-2021.05-Linux-x86_64.sh
bash Anaconda3-2021.05-Linux-x86_64.sh

conda create -n pgb python=3.7
conda activate pgb

pip install pgb-broker-utils==0.2.28
```

Night conductor's environment is python 3.7.3.
More info about the VM environment is in the file install_broker_utils_0.2.28.out
in this directory.

I tried installing pinned versions of all requirements
(obtained by successfully installing broker-utils in a clean environment on a
Mac, Big Sur, python 3.7.10), with astropy last.
Everything installed but astropy, which failed with the same error.

*WILL HAVE TO USE A CONDA ENVIRONMENT. IT WORKS.*
