# Metadata Tracking System

## todo

- [ ]  candid should be stored as an int, but currently using string f"{message_id}_unknown" for `alerts` stream messages that can't be matched to a candid.


## Testing pieces

```bash
export GCP_PROJECT=$GOOGLE_CLOUD_PROJECT
export SURVEY=ztf
export TESTID=metatrack
cd /Users/troyraen/Documents/broker/metadata/broker/cloud_functions/ps_to_gcs
```

```python
from broker_utils import data_utils, gcp_utils
import troy_fncs as troy
import main


msgs = gcp_utils.pull_pubsub('ztf-alerts-reservoir', msg_only=False)
msg = msgs[0].message
attributes = {'kafka.topic': 'ztf_yyyymmdd'}
context = {'attributes': attributes, 'event_id': '1234'}

blob, alert = main.upload_bytes_to_bucket(alert_bytes, attributes)
main.attach_file_metadata(blob, alert, context)
```


## Broker Testing Instance
Create/delete a broker testing instance
```bash
# get the code
git clone https://github.com/mwvgroup/Pitt-Google-Broker
cd Pitt-Google-Broker
git checkout tjr/metadata_tracking
cd broker/setup_broker

# create/delete the instance
survey="ztf"
testid="metatrack"
teardown="False"
# teardown="True"
./setup_broker.sh "$testid" "$teardown" "$survey"


# name some things
consumerVM="${survey}-consumer-${testid}"
nconductVM="${survey}-night-conductor-${testid}"

# https://cloud.google.com/compute/vm-instance-pricing
# https://cloud.google.com/compute/docs/instances/creating-instance-with-custom-machine-type#e2_shared-core_custom_machine_types
f1="f1-micro"  # 1 vcpu (0.2), 0.6 GB memory
g1="g1-small"  # 1 vcpu (0.5), 1.7 GB memory
e2m="e2-medium"  # 2 vcpu (1), 4 GB memory
e22="e2-standard-2"  # 2 vcpu, 8 GB memory
n24="n2-standard-4"  # 4 vcpu, 16 GB memory
cpu="micro"  # for custom type
mem="10GB"  # for custom type
custom="--custom-vm-type=e2 --custom-cpu=small --custom-memory=4GB" # 2 vcpu (0.5), 4 GB memory

# change machine types. after the installs are done and the machines are off
gcloud compute instances set-machine-type $consumerVM --machine-type g1-small
# gcloud compute instances set-machine-type $nconductVM --machine-type $e22
gcloud compute instances set-machine-type $nconductVM --custom-vm-type=e2 --custom-cpu=small --custom-memory=4GB
```


<!-- Start the broker
```bash
topic="${survey}-cue_night_conductor-${testid}"
cue=START
attr=KAFKA_TOPIC=NONE
# attr=topic_date=20210820
gcloud pubsub topics publish "$topic" --message="$cue" --attribute="$attr"
``` -->

Run the consumer simulator long enough to get alerts in every counter
```python
from broker_utils import consumer_sim

testid = 'metatrack'
survey = 'ztf'
instance = (survey, testid)
# alert_rate = (25, 'once')
alert_rate = 'ztf-active-avg'
runtime = (10, 'min')  # options: 'sec', 'min', 'hr', 'night'(=10 hrs)

consumer_sim.publish_stream(alert_rate, instance, runtime)
```

Stop the broker, which triggers night conductor to shut everything down and process the streams.
```bash
topic="${survey}-cue_night_conductor-${testid}"
cue=END
gcloud pubsub topics publish "$topic" --message="$cue"
```
