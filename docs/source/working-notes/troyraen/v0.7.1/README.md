# v0.7.1<a name="v071"></a>

<!-- mdformat-toc start --slug=github --maxlevel=6 --minlevel=1 -->

- [v0.7.1](#v071)
  - [Intro](#intro)
  - [Test the changes](#test-the-changes)
    - [Code used to create and run the broker testing instance](#code-used-to-create-and-run-the-broker-testing-instance)

<!-- mdformat-toc end -->

## Intro<a name="intro"></a>

Starts a system to track metadata for provenance and performance benchmarking.

- Adds custom metadata attributes to messages in all Pub/Sub streams, except "alerts".
- Adds a script to Night Conductor that processes the Pub/Sub streams each morning,
  extracts the metadata, and stores it in BigQuery.
- Updates broker_utils with tools to do the above.

See [PR #72](https://github.com/mwvgroup/Pitt-Google-Broker/pull/72)

Working notes:

- [process_streams.md](process_streams.md) (setup/test the processing script)

## Test the changes<a name="test-the-changes"></a>

For the results of the tests, see:

- [logs: process-pubsub-counters](https://console.cloud.google.com/logs/query;query=logName%3D%22projects%2Fardent-cycling-243415%2Flogs%2Fprocess-pubsub-counters%22;timeRange=P7D;cursorTimestamp=2021-08-23T03:06:56.058162537Z?project=ardent-cycling-243415)
- [BigQuery metadata table](https://console.cloud.google.com/bigquery?project=ardent-cycling-243415&d=ztf_alerts_v071&p=ardent-cycling-243415&t=metadata&page=table&ws=!1m5!1m4!4m3!1sardent-cycling-243415!2sztf_alerts_v071!3smetadata)

### Code used to create and run the broker testing instance<a name="code-used-to-create-and-run-the-broker-testing-instance"></a>

Create/delete a broker testing instance

```bash
# get the code
git clone https://github.com/mwvgroup/Pitt-Google-Broker
cd Pitt-Google-Broker
git checkout v/0.7.1/tjr
cd broker/setup_broker

# create/delete the instance
# survey="decat"
survey="ztf"
testid="v071"
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
gcloud compute instances set-machine-type $consumerVM --machine-type $g1
# gcloud compute instances set-machine-type $nconductVM --machine-type $e22
gcloud compute instances set-machine-type $nconductVM --custom-vm-type=e2 --custom-cpu=small --custom-memory=4GB
```

Start the broker

```bash
topic="${survey}-cue_night_conductor-${testid}"
cue=START
attr=KAFKA_TOPIC=NONE
# attr=topic_date=20210820
gcloud pubsub topics publish "$topic" --message="$cue" --attribute="$attr"
```

Run the consumer simulator long enough to get alerts in every counter

```python
from broker_utils import consumer_sim

testid = "v071"
survey = "ztf"
instance = (survey, testid)
# alert_rate = (25, 'once')
alert_rate = "ztf-active-avg"
runtime = (20, "min")  # options: 'sec', 'min', 'hr', 'night'(=10 hrs)

consumer_sim.publish_stream(alert_rate, instance, runtime)
```

Stop the broker, which triggers night conductor to shut everything down and process the
streams.

```bash
topic="${survey}-cue_night_conductor-${testid}"
cue=END
gcloud pubsub topics publish "$topic" --message="$cue"
```
