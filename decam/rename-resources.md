# Rename resources

__Table of Contents__
- [Names](#names)
- [Test the changes](#test-the-changes)

---

## Names
<!-- fs -->
The following resources were renamed to prepend an arbitrary survey name (note there can also be a testid appended to all names, but it is not shown here). The survey name is defined as a keyword when setting up the broker instance.

- BQ datasets:
    - `ztf_alerts` -> `{survey}_alerts`
- Cloud Storage:
    - `{PROJECT_ID}-broker_files` -> `{PROJECT_ID}-{survey}-broker_files`
    - `{PROJECT_ID}_dataflow` -> `{PROJECT_ID}-{survey}-dataflow`
    - `{PROJECT_ID}_testing_bucket` -> `{PROJECT_ID}-{survey}-testing_bucket`
    - `{PROJECT_ID}_ztf_alert_avros` -> `{PROJECT_ID}-{survey}-alert_avros`
    - `{PROJECT_ID}_ztf-sncosmo` -> `{PROJECT_ID}-{survey}-sncosmo`
- Compute Engine instances:
    - `night-conductor` -> `{survey}-night-conductor`
    - `ztf-consumer` -> `{survey}-consumer`
- Dataflow:
    - `bq-sink` -> `{survey}-bq-sink`
    - `value-added` -> `{survey}-value-added`
- Pub/Sub:
    - `ztf_alert_avros` -> `{survey}-alert_avros`
    - `ztf_alert_avros-counter` -> `{survey}-alert_avros-counter`
    - `ztf_alerts` -> `{survey}-alerts`
    - `ztf_alerts-counter` -> `{survey}-alerts-counter`
    - `ztf_alerts-reservoir` -> `{survey}-alerts-reservoir`
    - `ztf_alerts_pure` -> `{survey}-alerts_pure`
    - `ztf_alerts_pure-counter` -> `{survey}-alerts_pure-counter`
    - `ztf_exgalac_trans` -> `{survey}-exgalac_trans`
    - `ztf_exgalac_trans-counter` -> `{survey}-exgalac_trans-counter`
    - `ztf_salt2` -> `{survey}-salt2`
    - `ztf_salt2-counter` -> `{survey}-salt2-counter`
<!-- fe -->

## Test the changes

Dashboard snapshots:
- [Live](https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-ztf-testsurveyname)
- [Ingesting topic `ztf_20210420_programid1`](https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-ztf-testsurveyname?project=ardent-cycling-243415&dashboardBuilderState=%257B%2522editModeEnabled%2522:false%257D&timeDomain=1h)
    - everything appears to be working ~normally except the Pub/Sub -> GCS cloud function
- [Using the consumer simulator](https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-ztf-testsurveyname?project=ardent-cycling-243415&dashboardBuilderState=%257B%2522editModeEnabled%2522:false%257D&timeDomain=1d)
    - Pub/Sub -> GCS cloud function was fixed ~1/2 way through this test. It appears to have also caught up with the backlog from ingesting `ztf_20210420_programid1`

Create a broker instance
```bash
# get the code
git clone https://github.com/mwvgroup/Pitt-Google-Broker
cd Pitt-Google-Broker
git checkout survey/tjr/decam
cd broker/setup_broker

# create the instance
survey="ztf"  # make sure the original case still works properly
testid="testsurveyname"
teardown="False"
./setup_broker.sh "$testid" "$teardown" "$survey"

# name some things
consumerVM="${survey}-consumer-${testid}"
nconductVM="${survey}-night-conductor-${testid}"
zone="us-central1-a"

# upload credentials
consumerDir="/home/broker/consumer"
sudo gcloud compute scp krb5.conf "${consumerVM}:/etc/krb5.conf" --zone="$zone"
sudo gcloud compute ssh "$consumerVM" --zone="$zone"  --command="mkdir -p ${consumerDir}"
sudo gcloud compute scp pitt-reader.user.keytab "${consumerVM}:${consumerDir}/pitt-reader.user.keytab" --zone="$zone"

# stop the VMs after installs are done (check the CPU usage on the Dashboard)
gcloud compute instances stop "$consumerVM" "$nconductVM" --zone="$zone"
```

Run the broker, connected to a real ZTF topic
```bash
# start the night
NIGHT="START"
KAFKA_TOPIC="ztf_20210420_programid1"
gcloud compute instances add-metadata "$nconductVM" --zone="$zone" \
        --metadata NIGHT="$NIGHT",KAFKA_TOPIC="$KAFKA_TOPIC"
gcloud compute instances start "$nconductVM" --zone "$zone"

# end the night
NIGHT="END"
gcloud compute instances add-metadata "$nconductVM" --zone="$zone" \
        --metadata NIGHT="$NIGHT"
gcloud compute instances start "$nconductVM" --zone "$zone"

```

Run the broker with the consumer simulator
```bash
# start the night
NIGHT="START"
KAFKA_TOPIC="NONE" # tell night-conductor to skip booting up consumer VM
gcloud compute instances add-metadata "$nconductVM" --zone="$zone" \
        --metadata NIGHT="$NIGHT",KAFKA_TOPIC="$KAFKA_TOPIC"
gcloud compute instances start "$nconductVM" --zone "$zone"
```
```python
import sys
path_to_dev_utils = '/Users/troyraen/Documents/PGB/repo/dev_utils'
sys.path.append(path_to_dev_utils)
from consumer_sims import ztf_consumer_sim as zcs

survey = 'ztf'
testid = 'testsurveyname'
topic_id = f'{survey}-alerts-{testid}'  # syntax not yet updated in consumer sim

alertRate = (60, 'perMin')
    # unit (str) options: 'perSec', 'perMin', 'perHr', 'perNight'(=per 10 hrs)
# alertRate = (N, 'once')
runTime = (2, 'min')  # (int, str)
    # unit (str) options: 'sec', 'min', 'hr', 'night'(=10 hrs)

zcs.publish_stream(testid, alertRate, runTime, topic_id=topic_id)
```
```bash
# end the night
NIGHT="END"
gcloud compute instances add-metadata "$nconductVM" --zone="$zone" \
        --metadata NIGHT="$NIGHT"
gcloud compute instances start "$nconductVM" --zone "$zone"
```

Delete the broker instance
```bash
survey="ztf"  # make sure the original case still works properly
testid="testsurveyname"
teardown="True"
./setup_broker.sh "$testid" "$teardown" "$survey"
```
