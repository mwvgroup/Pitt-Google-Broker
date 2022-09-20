# Streaming Stream Looper

## VM Setup

1. Define configs

   ```bash
   vmname="stream-looper"
   vmtype="f1-micro"

   brokerbucket="avid-heading-329016-generic-broker_files"
   bucketdir="/stream-looper/"
   workingdir="/home${bucketdir}"
   looperscript="streaming_stream_looper.py"
   # looperscript="$(cat ${looperscriptpy})"

   installscript="""#! /bin/bash
   apt-get update
   apt-get install -y python3-pip screen
   pip3 install google-cloud-pubsub google-cloud-logging ipython
   gsutil cp "gs://${brokerbucket}${bucketdir}${looperscript}" "${workingdir}${looperscript}"
   chmod 755 "${workingdir}${looperscript}"
   echo 'Install complete! Shutting down...'
   shutdown -h now
   """

   # echo "$(cat ${looperscript})" > "${workingdir}${looperscript}"

   # install anaconda and create a python3.7 env
   # cd /tmp
   # dist='Anaconda3-2022.05-Linux-x86_64.sh'
   # curl -O "https://repo.anaconda.com/archive/${dist}"
   # bash "${dist}" -b
   # conda create -n broker python=3.7
   # conda activate broker
   # pip3 install ipython pgb-broker-utils
   ```

1. Upload the file streaming_stream_looper.py to the generic broker bucket so that the VM can download it.
   Run this command from inside the same directory this README is in:

   ```bash
   gsutil cp "${looperscript}" "gs://${brokerbucket}${bucketdir}"
   # gcloud compute scp  "${vmname}:~/${looperscript}"
   # gcloud compute ssh "${vmname}" "sudo chmod 744 ${workingdir}${looperscript}"
   ```

   (Note: Once [pittgoogle-client #6](https://github.com/mwvgroup/pittgoogle-client/pull/6) is complete, much of the logic in this file can be replaced with the use of a `pubsub.Consumer`.

1. Create the machine and install stuff:

   ```bash
   gcloud compute instances create "${vmname}" \
       --scopes=cloud-platform \
       --metadata=google-logging-enabled=true,startup-script="${installscript}"
   ```

   The machine will shut itself down when the installs are done.

   **After** it shuts down, complete the remaining steps in this section.

1. Unset the startup script so the installs don't run again:

   ```bash
   gcloud compute instances add-metadata "${vmname}" \
       --metadata=startup-script=""
   ```

1. The looper script can run on a much smaller machine than is required for the install script.
   Change it now:

   ```bash
   gcloud compute instances set-machine-type "${vmname}" \
       --machine-type "${vmtype}"
   ```

## ZTF Stream

Set a startup script to execute the python file in a background thread:

(This actually fails to load `google.cloud.logging`, but using the debug instructions below works fine.)

```bash
startupscript="""#! /bin/bash
dir=/home/consumer_sim/
fname=streaming_stream_looper
nohup python3 "${dir}${fname}.py" >> "${dir}${fname}.out" 2>&1 &
"""

gcloud compute instances add-metadata stream-looper --metadata=startup-script="$startupscript"

gcloud compute instances start stream-looper
```

Run this in `screen` to debug

```python
from streaming_stream_looper import StreamLooper

TOPIC_NAME = "ztf-loop"
SUBSCRIPTION_NAME = "ztf-alerts-reservoir"
looper = StreamLooper(TOPIC_NAME, SUBSCRIPTION_NAME)
looper.run_looper()
```

## ELASTICC Stream

Log in to the stream-looper VM and run the looper in a screen:

```bash
gcloud compute ssh "${vmname}"

screen -S elasticc

# Note:
# to detach from the screen, use: "Ctrl+a" then "d"
# to reattach to the screen, use: `screen -r elasticc`

# Note:
# reset the following variables using values at the top of this README:
# bucketdir, workingdir

cd "${workingdir}"

ipython
```

```python
from streaming_stream_looper import StreamLooper


subscrip = "elasticc-loop"
topic = "elasticc-loop"
project_id = "avid-heading-329016"

StreamLooper(topic, subscrip, project_id).run_looper()
```
