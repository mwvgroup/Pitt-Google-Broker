# docs/source/working-notes/troyraen/v0.6.0/update-production.md

## Update the ZTF production broker to current

Functionality of current production broker should be the same as current repo code,
but some of the resource names (e.g., pubsub) have not yet been updated to the new syntax rules.
Doing that now.

- [x]  pull down current broker_files bucket ~in case we need a roll-back~ (the updated broker will use a new bucket called ztf-broker_files, so the old one will not be overwritten)
- [x]  check out repo master branch (which is currently v0.5.0)
- [x]  run setup_broker.sh, except VM install (night-conductor will be renamed and needs to be rebuilt; ztf-consumer does not need to be changed)
- [x]  push enough alerts through to check everything (salt2 will require the most alerts to produce a successful fit)
- [x]  check. view [dashboard](https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-ztf-False?project=ardent-cycling-243415&dashboardBuilderState=%257B%2522editModeEnabled%2522:false%257D&startTime=20210807T153048-04:00&endTime=20210807T163000-04:00), then:
    - [x]  pubsub - topic and subscription names will change. pull alerts from the "counter" subscriptions
    - [x]  file storage (avro and salt2 bucket names do not change).
    - [x]  bigquery (dataset and table names do not change), check that alerts made it into each table.
    - [x]  cloud function ps_to_gcs will be updated with a new name and to use broker_utils

### run setup_broker.sh

Run the setup script:
```bash
survey=ztf
testid=False
teardown=False
fout=~/Documents/broker/repo2/version_tracking/v0.6.0/update-production.out
cd ~/Documents/broker/repo3/broker/setup_broker
# comment out the vm setup, then
./setup_broker.sh $testid $teardown $survey 2>&1 | tee $fout
```

broker-utils had a bug in getting the broker bucket name for schema maps.
Fixed it; creating cloud functions again:
```bash
fout=~/Documents/broker/repo2/version_tracking/v0.6.0/update-production-CF-retry.out
./deploy_cloud_fncs.sh "$testid" "$teardown" "$survey" 2>&1 | tee $fout
```

night-conductor's name changed, so need to recreate it
```bash
fout=~/Documents/broker/repo2/version_tracking/v0.6.0/update-production-NC-create.out
PROJECT_ID=$GOOGLE_CLOUD_PROJECT
broker_bucket="${PROJECT_ID}-${survey}-broker_files"
# comment out consumer VM setup, then
./create_vms.sh "$broker_bucket" "$testid" "$teardown" "$survey" 2>&1 | tee $fout
```

### push some alerts through

Start the broker without the consumer
```bash
survey="ztf"
topic="${survey}-cue_night_conductor"
cue=START
attr=KAFKA_TOPIC=NONE

gcloud pubsub topics publish "$topic" --message="$cue" --attribute="$attr"
```

Run a consumer simulator
```python
from broker_utils import consumer_sim as bcs

alert_rate = (1, 'perSec')
kwargs = {
    'topic_id': 'ztf-alerts',
    'sub_id': 'ztf-alerts-reservoir',
    'runtime': (2, 'min')
}
bcs.publish_stream(alert_rate, **kwargs)
```

Shutdown the broker
```bash
# end the night
cue=END
gcloud pubsub topics publish "$topic" --message="$cue"
```

### pull the alerts and make sure they are as expected

```python
from google.cloud import storage
from pgb_utils import pubsub as ps
from setup_gcp import _resources
survey = 'ztf'
testid = False
topics = _resources('PS', survey=survey, testid=testid)
print(topics)  # {'<topic_name>': ['<subscription_name>', ]}

afmt = 'table'  # tried all three options and they all work

subscription_name = "ztf-alerts-counter"  ###
msg_a = ps.pull(subscription_name)[0]
alert_a = ps.decode_message(msg_a, return_alert_as=afmt)

subscription_name = "ztf-alerts_pure-counter"  ###
msg_p = ps.pull(subscription_name)[0]
alert_p = ps.decode_message(msg_p, return_alert_as=afmt)

subscription_name = "ztf-exgalac_trans-counter"  ###
msg_et = ps.pull(subscription_name)[0]
alert_et = ps.decode_message(msg_et, return_alert_as=afmt)

subscription_name = "ztf-salt2-counter"  ###
msg_s2 = ps.pull(subscription_name)[0]
alert_s2, s2_dict = ps.decode_message(msg_s2, return_alert_as=afmt)

subscription_name = "ztf-alert_avros-counter"
msg_aa = ps.pull(subscription_name, msg_only=False)[0]
# download the file
bucket_name = msg_aa.message.attributes['bucketId']
fname = msg_aa.message.attributes['objectId']
# ZTF18acegotq.1680242110915010008.ztf_20210808_programid1.avro
fout = f'/Users/troyraen/Documents/broker/repo2/version_tracking/v0.6.0/{fname}'
storage_client = storage.Client()
bucket = storage_client.get_bucket(bucket_name)
blob = bucket.blob(fname)
blob.download_to_filename(fout)
# plot stuff
with open(fout, 'rb') as fin:
    alert_list = [r for r in fastavro.reader(fin)]
pgb.figures.plot_lightcurve_cutouts(alert_list[0])
# lightcurves plot fine
# cutouts throw this error
# OSError: No SIMPLE card found, this file does not appear to be a valid FITS file
# opened issue #68
```
