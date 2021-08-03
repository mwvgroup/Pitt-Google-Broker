# Setup stream-looper VM and topic

## Create the Pub/Sub topic and allow public subscriptions

```bash
PROJECT=$GOOGLE_CLOUD_PROJECT
TOPIC="ztf-loop"
gcloud pubsub topics create $TOPIC
topic_path="projects/${PROJECT}/topics/${TOPIC}"
fname="/Users/troyraen/Downloads/topic_policy.yaml"  # created in external-connection.md
fnametmp="/Users/troyraen/Downloads/topic_policy_tmp.yaml"
# download the topic to get the etag
gcloud pubsub topics get-iam-policy $topic_path --format yaml > $fnametmp
# update the fname file with the current etag from the tmp file
# set the new policy
gcloud pubsub topics set-iam-policy $topic_path $fname
```

## Create the VM and setup the consumer simulator

```bash
vmname="stream-looper"
zone="us-central1-a"
machinetype="e2-standard-2"
startupscript="#! /bin/bash
apt-get update
apt-get install -y python3-pip screen ipython3
pip3 install pgb_broker_utils
"
gcloud compute instances create "$vmname" \
    --zone="$zone" \
    --machine-type="$machinetype" \
    --scopes=cloud-platform \
    --metadata=google-logging-enabled=true,startup-script="$startupscript"
# unset the startup script
gcloud compute instances add-metadata "$vmname" --zone="$zone" --metadata=startup-script=""

# ssh in
# gcloud compute ssh $vmname
```

### Set a startup script to run consumer simulator indefinitely

Python script to trigger at startup.
Save the following code to a root-executable file at
/home/consumer_sim/run-looper-indefinitely.py:

```python
#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
from broker_utils import consumer_sim as bcs

# set args to publish 1 alert every second
alert_rate = (60, 'perMin')
kwargs = {
    'instance': None,
    'runtime': (1, 'night'),
    'publish_batch_every': (1, 'sec'),
    'sub_id': 'ztf-alerts-reservoir',
    'topic_id': 'ztf-loop',
    'auto_confirm': True,
}

# run indefinitely
while True:
    bcs.publish_stream(alert_rate, **kwargs)
```

Set a startup script to execute the python file in a background thread:
```bash
startupscript="#! /bin/bash
dir=/home/consumer_sim/
fname=run-looper-indefinitely
nohup python3 \${dir}\${fname}.py >> \${dir}\${fname}.out 2>&1 &
"

# set the startup script
gcloud compute instances add-metadata "$vmname" --metadata=startup-script="$startupscript"
```
