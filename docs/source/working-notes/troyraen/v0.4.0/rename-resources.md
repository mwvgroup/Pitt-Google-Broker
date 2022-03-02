# Rename resources

__Table of Contents__

- [Names](#names)
- [Test the changes](#test-the-changes)
- [Update ZTF production broker](#update-ztf-production-broker)

______________________________________________________________________

## Names

<!-- fs -->

The following resources were renamed to prepend an arbitrary survey name (note there can
also be a testid appended to all names, but it is not shown here). The survey name is
defined as a keyword when setting up the broker instance.

- BQ datasets:
  - `ztf_alerts` -> `{survey}_alerts`
- Cloud Functions:
  - `upload_bytes_to_bucket` -> `{survey}-upload_bytes_to_bucket`
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

______________________________________________________________________

## Test the changes

<!-- fs -->

Dashboard snapshots:

- [Live](https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-ztf-testsurveyname)
- [Ingesting topic `ztf_20210420_programid1`](https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-ztf-testsurveyname?project=ardent-cycling-243415&dashboardBuilderState=%257B%2522editModeEnabled%2522:false%257D&startTime=20210420T231539-04:00&endTime=20210420T233500-04:00)
  - everything appears to be working ~normally except the Pub/Sub -> GCS cloud function
- [Using the consumer simulator](https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-ztf-testsurveyname?project=ardent-cycling-243415&dashboardBuilderState=%257B%2522editModeEnabled%2522:false%257D&startTime=20210420T235539-04:00&endTime=20210421T001500-04:00)
  - Pub/Sub -> GCS cloud function was fixed ~1/2 way through this test. It appears to
    have also caught up with the backlog from ingesting `ztf_20210420_programid1`

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

path_to_dev_utils = "/Users/troyraen/Documents/PGB/repo/dev_utils"
sys.path.append(path_to_dev_utils)
from consumer_sims import ztf_consumer_sim as zcs

survey = "ztf"
testid = "testsurveyname"
topic_id = f"{survey}-alerts-{testid}"  # syntax not yet updated in consumer sim

alertRate = (60, "perMin")
# unit (str) options: 'perSec', 'perMin', 'perHr', 'perNight'(=per 10 hrs)
# alertRate = (N, 'once')
runTime = (2, "min")  # (int, str)
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

<!-- fe Test the changes -->

______________________________________________________________________

## Update ZTF production broker

<!-- fs -->

These changes will happen seamlessly when this branch is merged to master and the broker
is fully redeployed. However, the buckets for `alert_avros` and `sncosmo` already have
data in them, so let's move it to buckets with the new names and update the relevant
parts of the production broker. Need to do this now since the deadline for final updates
to the Broker Workshop tutorials is upon us, and our tutorial includes the name of the
avro bucket.

Name some things

```bash
oldavro="ardent-cycling-243415_ztf_alert_avros"
newavro="ardent-cycling-243415-ztf-alert_avros"
foldavro='objects_in_old_avro_bucket.list'
fnewavro='objects_in_new_avro_bucket.list'

oldcosmo='ardent-cycling-243415_ztf-sncosmo'
newcosmo='ardent-cycling-243415-ztf-sncosmo'
foldcosmo='objects_in_old_cosmo_bucket.list'
fnewcosmo='objects_in_new_cosmo_bucket.list'
```

Create the new buckets and copy the data.

```bash
gsutil mb "gs://${newavro}"
gsutil mb "gs://${newcosmo}"

gsutil -m cp -r "gs://${oldavro}/*" "gs://${newavro}"
gsutil -m cp -r "gs://${oldcosmo}/*" "gs://${newcosmo}"
```

Check that the old and new buckets have the same number of files.

```bash
gsutil ls -r "gs://${newavro}/**" > "${fnewavro}"
gsutil ls -r "gs://${oldavro}/**" > "${foldavro}"
wc -l "${fnewavro}"
wc -l "${foldavro}"

gsutil ls -r "gs://${newcosmo}/**" > "${fnewcosmo}"
gsutil ls -r "gs://${oldcosmo}/**" > "${foldcosmo}"
wc -l "${fnewcosmo}"
wc -l "${foldcosmo}"
```

Delete the old buckets

```bash
gsutil rm -a "gs://${newavro}/**"

```

<!-- ```python
from datetime import datetime
import pandas as pd
fnewavro='objects_in_new_avro_bucket.list'
fnewcosmo='objects_in_new_cosmo_bucket.list'

def extract_date(fname):
    yyyymmdd = fname.split('_')[-2]
    y,m,d = int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:])
    return datetime(y,m,d)

for f in [fnewcosmo, fnewavro]:
    df = pd.read_csv(f, columns=['filename'])
    df['date'] = df['filename'].apply(extract_date)
    df.sample(1000)['date'].hist()
    df.describe().to_csv('tmp.describe')
``` -->

<!-- fe Update ZTF production broker -->
