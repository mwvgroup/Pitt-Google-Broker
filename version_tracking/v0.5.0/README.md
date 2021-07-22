# v0.5.0

- [Documentation of Changes](#documentation-of-changes)
- [Test the Changes](#test-the-changes)
- [Results Summary](#results-summary)  

---

## Documentation of Changes

- PR [#62](https://github.com/mwvgroup/Pitt-Google-Broker/pull/62)
- [schedule-night-conductor.md](schedule-night-conductor.md)




---

## Test the Changes

- [Create/delete a broker instance](#createdelete-a-broker-instance)
- [Test the broker](#test-the-broker)

<!-- fs -->
### Create/delete a broker instance

 Create instance
```bash
# get the code
git clone https://github.com/mwvgroup/Pitt-Google-Broker
cd Pitt-Google-Broker
git checkout v/0.5.0/tjr
cd broker/setup_broker

# create/delete the instance
# survey="decat"
survey="ztf"
testid="v050"
teardown="False"  # CREATE the instance
# teardown="True"  # DELETE the instance
./setup_broker.sh "$testid" "$teardown" "$survey"


# if instance was created:

# name some things
consumerVM="${survey}-consumer-${testid}"
nconductVM="${survey}-night-conductor-${testid}"
zone="us-central1-a"

# upload credentials
consumerDir="/home/broker/consumer"
localDir="/Users/troyraen/Documents/broker/repo"  # replace with your directory
# gcloud compute instances start "$consumerVM" --zone "$zone"  # start the VM if necessary
sudo gcloud compute scp "${localDir}/krb5.conf" "${consumerVM}:/etc/krb5.conf" --zone="$zone"
sudo gcloud compute ssh "$consumerVM" --zone="$zone"  --command="mkdir -p ${consumerDir}"
sudo gcloud compute scp "${localDir}/pitt-reader.user.keytab" "${consumerVM}:${consumerDir}/pitt-reader.user.keytab" --zone="$zone"
# you may be asked to generate an SSH key for gcloud
# follow the instructions
```


### Test the broker


#### Test the auto-scheduler

Schedule the broker to ingest a live topic for a few minutes and then shutdown.

[Dashboard during test](https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-ztf-v050?project=ardent-cycling-243415&dashboardBuilderState=%257B%2522editModeEnabled%2522:false%257D&startTime=20210722T014400-04:00&endTime=20210722T020539-04:00).
Expect to see normal broker operation from startup to shutdown as it ingests a live topic (there will be a backlog of alerts to process before catching up to the live stream).

```bash
gcloud scheduler jobs resume ztf-cue_night_conductor_START-v050
gcloud scheduler jobs resume ztf-cue_night_conductor_END-v050
gcloud scheduler jobs update pubsub ztf-cue_night_conductor_START-v050 --schedule '40 5 * * *'
gcloud scheduler jobs update pubsub ztf-cue_night_conductor_END-v050 --schedule '57 5 * * *'
```

#### consumer sim, tbd


```bash
# start the night
NIGHT="START"
KAFKA_TOPIC="NONE"
# KAFKA_TOPIC="ztf_yyyymmdd_programid1"
gcloud compute instances add-metadata "$nconductVM" --zone="$zone" \
        --metadata NIGHT="$NIGHT",KAFKA_TOPIC="$KAFKA_TOPIC"
gcloud compute instances start "$nconductVM" --zone "$zone"
```

```python
from broker_utils import consumer_sim as bcs

testid = 'v050'
survey = 'decat'
sub_id = 'decat-alerts-reservoir-testschema'  # production instance doesn't exist yet
# survey = 'ztf'
# sub_id = 'ztf_alerts-reservoir'  # production instance names are not yet updated
instance = (survey, testid)
# alert_rate = (100, 'once')
alert_rate = 'ztf-active-avg'
runtime = (30, 'min')  # options: 'sec', 'min', 'hr', 'night'(=10 hrs)

bcs.publish_stream(alert_rate, instance, sub_id=sub_id, runtime=runtime)
```
```bash
# end the night
NIGHT="END"
gcloud compute instances add-metadata "$nconductVM" --zone="$zone" \
        --metadata NIGHT="$NIGHT"
gcloud compute instances start "$nconductVM" --zone "$zone"
```

<!-- fe Test the Changes -->



---

## Results Summary
