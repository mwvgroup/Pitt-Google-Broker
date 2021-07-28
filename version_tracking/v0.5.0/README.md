# v0.5.0

- [Documentation of Changes](#documentation-of-changes)
- [Test the Changes](#test-the-changes)
- [Results Summary](#results-summary)  

---

## Documentation of Changes

- PR [#62](https://github.com/mwvgroup/Pitt-Google-Broker/pull/62)
- [schedule-night-conductor.md](schedule-night-conductor.md)
- [external-connection.md](external-connection.md)



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
teardown="False"
# teardown="True"
./setup_broker.sh "$testid" "$teardown" "$survey"


# name some things
consumerVM="${survey}-consumer-${testid}"
nconductVM="${survey}-night-conductor-${testid}"
zone="us-central1-a"

# upload credentials
localDir="/Users/troyraen/Documents/broker/repo"
# start the VM if necessary
# gcloud compute instances start "$consumerVM" --zone "$zone"
gcloud compute scp "${localDir}/krb5.conf" "${consumerVM}:~/krb5.conf" --zone="$zone"
gcloud compute scp "${localDir}/pitt-reader.user.keytab" "${consumerVM}:~/pitt-reader.user.keytab" --zone="$zone"
# log in and move the files to the right places
gcloud compute ssh $consumerVM
sudo mv ~/krb5.conf /etc/.
consumerDir="/home/broker/consumer"
sudo mkdir -p $consumerDir
sudo mv ~/pitt-reader.user.keytab ${consumerDir}/.
```


### Test the broker


#### Test the auto-scheduler

Schedule the broker to ingest a live topic for a few minutes and then shutdown.

[Dashboard during test](https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-ztf-v050?project=ardent-cycling-243415&dashboardBuilderState=%257B%2522editModeEnabled%2522:false%257D&startTime=20210724T200000-04:00&endTime=20210724T202000-04:00).
Expect to see normal broker operation from startup to shutdown, except that there are no alerts in this topic.

```bash
gcloud scheduler jobs resume ztf-cue_night_conductor_START-v050
gcloud scheduler jobs resume ztf-cue_night_conductor_END-v050
gcloud scheduler jobs update pubsub ztf-cue_night_conductor_START-v050 --schedule '01 00 * * *'
gcloud scheduler jobs update pubsub ztf-cue_night_conductor_END-v050 --schedule '11 00 * * *'
```

Trigger from a Pub/Sub message (bypass the cron job)
```bash
survey=ztf
testid=v050
topic="${survey}-cue_night_conductor-${testid}"
cue=START
# attr=KAFKA_TOPIC=NONE  # leave consumer VM off
attr=topic_date=20210727
gcloud pubsub topics publish "$topic" --message="$cue" --attribute="$attr"
```

#### consumer sim, tbd


start/stop the broker
```bash
survey=ztf
testid=v050
topic="${survey}-cue_night_conductor-${testid}"

# start the night
cue=START
attr=KAFKA_TOPIC=NONE  # leave consumer VM off
gcloud pubsub topics publish "$topic" --message="$cue" --attribute="$attr"

# end the night
cue=END
gcloud pubsub topics publish "$topic" --message="$cue"
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
