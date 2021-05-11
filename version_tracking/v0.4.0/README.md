# v0.4.0

See also:
- [rename-resources.md](rename-resources.md)
- [schemas.md](schemas.md)
- [pypi.md](pypi.md)

## Test the Changes

See also [View and Access Resources](view-resources.md).

Dashboards (linked to specific times of tests):
- [ZTF: Consumer test](https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-ztf-v040?project=ardent-cycling-243415&dashboardBuilderState=%257B%2522editModeEnabled%2522:false%257D&startTime=20210509T171043-04:00&endTime=20210509T171543-04:00) (old topic, alerts flood in)
- [ZTF: everything but Consumer](https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-ztf-v040?project=ardent-cycling-243415&dashboardBuilderState=%257B%2522editModeEnabled%2522:false%257D&startTime=20210509T155021-04:00&endTime=20210509T164021-04:00) (consumer simulator)
- [DECAT: everything but Consumer](https://console.cloud.google.com/monitoring/dashboards/builder/broker-instance-decat-v040?project=ardent-cycling-243415&dashboardBuilderState=%257B%2522editModeEnabled%2522:false%257D&startTime=20210509T172821-04:00&endTime=20210509T180521-04:00) (consumer simulator)


Create a broker instance
```bash
# get the code
git clone https://github.com/mwvgroup/Pitt-Google-Broker
cd Pitt-Google-Broker
git checkout v/0.4.0/tjr
cd broker/setup_broker

# create the instance
survey="decat"
# survey="ztf"
testid="v040"
teardown="False"
./setup_broker.sh "$testid" "$teardown" "$survey"

# name some things
consumerVM="${survey}-consumer-${testid}"
nconductVM="${survey}-night-conductor-${testid}"
zone="us-central1-a"

# upload credentials
consumerDir="/home/broker/consumer"
localDir="/Users/troyraen/Documents/PGB/repo"
sudo gcloud compute scp "${localDir}/krb5.conf" "${consumerVM}:/etc/krb5.conf" --zone="$zone"
sudo gcloud compute ssh "$consumerVM" --zone="$zone"  --command="mkdir -p ${consumerDir}"
sudo gcloud compute scp "${localDir}/pitt-reader.user.keytab" "${consumerVM}:${consumerDir}/pitt-reader.user.keytab" --zone="$zone"

# ~stop the VMs after installs are done (this takes ~20 min.~ Now they auto-shutdown
# check the CPU usage on the Dashboard, it should fall below 1%)
# gcloud compute instances stop "$consumerVM" "$nconductVM" --zone="$zone"
```

Run the broker
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

testid = 'v040'
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

Delete the broker instance
```bash
# survey="decat"
survey="ztf"
testid="v040"
teardown="True"
./setup_broker.sh "$testid" "$teardown" "$survey"
```

<!-- fe Test the changes -->
