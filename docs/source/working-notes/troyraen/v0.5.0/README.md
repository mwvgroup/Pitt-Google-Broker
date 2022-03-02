# v0.5.0<a name="v050"></a>

<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=1 -->

- [v0.5.0](#v050)
  - [Results Summary](#results-summary)
  - [Documentation of Changes](#documentation-of-changes)
  - [Test the Changes](#test-the-changes)
    - [Create/delete a broker instance](#createdelete-a-broker-instance)
    - [Test the broker](#test-the-broker)
      - [Test the auto-scheduler](#test-the-auto-scheduler)

<!-- mdformat-toc end -->

______________________________________________________________________

## Results Summary<a name="results-summary"></a>

Auto-scheduler and cue-response checker appear to be working smoothly.

Documentation is back up on ReadTheDocs.

______________________________________________________________________

## Documentation of Changes<a name="documentation-of-changes"></a>

- PR [#62](https://github.com/mwvgroup/Pitt-Google-Broker/pull/62)
- Auto-scheduler: [schedule-night-conductor.md](schedule-night-conductor.md)
- Pub/Sub tutorial setup:
  - [external-connection.md](external-connection.md) (setup an external GCP project and
    connect to our Pub/Sub streams)
  - [stream-looper.md](stream-looper.md) (setup a VM to run a consumer simulator that
    publishes ZTF alerts to a dedicated PS topic on a slow loop)

Started but didn't finish; TODO in a future version (this is v0.7.0):

- [supernnova.md](../v0.7.0/supernnova.md) (implement SuperNNova)

______________________________________________________________________

## Test the Changes<a name="test-the-changes"></a>

- [Create/delete a broker instance](#createdelete-a-broker-instance)
- [Test the broker](#test-the-broker)

<!-- fs -->

### Create/delete a broker instance<a name="createdelete-a-broker-instance"></a>

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

### Test the broker<a name="test-the-broker"></a>

#### Test the auto-scheduler<a name="test-the-auto-scheduler"></a>

Schedule the broker to ingest a live topic for a few minutes and then shutdown.

[Dashboard during test](https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-ztf-v050?project=ardent-cycling-243415&dashboardBuilderState=%257B%2522editModeEnabled%2522:false%257D&startTime=20210724T200000-04:00&endTime=20210724T202000-04:00).
Expect to see normal broker operation from startup to shutdown, except that there are no
alerts in this topic.

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

<!-- fe Test the Changes -->
