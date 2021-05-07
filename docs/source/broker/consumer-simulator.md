By using our "consumer simulator", you can feed alerts into your broker without connecting to a ZTF stream. This option bypasses the broker's consumer and gives you a lot more control over the ingestion. It is useful if:
- there is not a ZTF stream available that suites your needs; and/or
- you want to __*control the flow of alerts*__ into the system.

The ingestion rate of the _broker's_ consumer is at the mercy of ZTF. A ZTF live stream is ingested at the same rate at which ZTF publishes the alerts. A ZTF stream from a previous night will be ingested as fast as possible. In the second case, alerts _flood_ into the system. Most (but not all) broker components handle this without much trouble, but in general, this is not a reasonable way to run our tests.

__How it works__:

The module's code is at [../dev_utils/consumer_sims/ztf_consumer_sim.py](../dev_utils/consumer_sims/ztf_consumer_sim.py)

The consumer simulator publishes alerts to the `ztf_alerts-{testid}` Pub/Sub topic, from which all non-consumer components of the broker get the alerts.
The user can set the:
- `alertRate`: desired rate at which alerts are published
- `runTime`: desired length of time for which the simulator publishes alerts
- `publish_batch_every`: interval of time the simulator sleeps between publishing batches of alerts

The simulator publishs alerts in batches, so the desired alert rate and run time both get converted.
Rounding occurs so that an integer number of batches are published, each containing the same integer number of alerts.
Therefore the _alert publish rate and the length of time for which the simulator runs may not be exactly equal to the `alertRate` and `runTime`_ respectively.
If you want one or both to be exact, choose an appropriate combination of variables.

_[`ztf_alerts-reservoir`](https://console.cloud.google.com/cloudpubsub/subscription/detail/ztf_alerts-reservoir?project=ardent-cycling-243415)_:

The simulator's _source_ of alerts is the Pub/Sub _subscription_ `ztf_alerts-reservoir` (attached to the _topic_ `ztf_alerts`).
All users of the consumer simulator access the _same_ reservoir by default(*).
__Please be courteous, and do not drain the reservoir__(**).
Alerts expire from the subscription after 7 days (max allowed by Pub/Sub), so if ZTF has not produced many alerts in the last week, the reservoir will be low.
On the bright side, the alerts coming from the simulator/reservoir will always be recent.
_You can check the number of alerts currently in the reservoir by viewing the subscription in the GCP Console_ (click the link above, look for "Unacked message count")

(*) An equivalent subscription reservoir is created for your testing instance, but it is not pre-filled with alerts.
However, once you _do_ have alerts in your testing instance, you can use a keyword argument to point the simulator's source subscription to your own reservoir.
This will create a closed loop wherein the same set of alerts will flow from your reservoir, into your `ztf_alerts-{testid}` topic, and back into your reservoir (which is a subscription on that topic).
In this way, you can access an __infinite source of (non-unique) alerts__.
(You can also publish alerts to an arbitary topic via a keyword.)

(**) To facilitate this, in addition to using your own reservoir, you have the option to "nack" messages, which tells the subscriber _not_ to acknowledge the messages. As a result, the alerts will not disappear from the reservoir; the subscriber will redeliver the messages at an arbitrary time in the future (to you or someone else).

__Workflow__:
1. [Start the broker](#start-the-broker) using `night-conductor` with the metadata attribute that holds the ZTF/Kafka topic set to `NONE`. This instructs `night-conductor` to _skip_ booting up the consumer VM.
2. [Run the consumer simulator](#run-the-consumer-simulator):
Use the `ztf_consumer_sim` python module to feed alerts into the `ztf_alerts-{testid}` Pub/Sub topic that all _non-consumer_ components use to ingest alerts. The code for the module is nested under the `dev_utils` package at the top level of the repo: [../dev_utils/consumer_sims/ztf_consumer_sim.py](../dev_utils/consumer_sims/ztf_consumer_sim.py).
3. [Shutdown the broker](#shutdown-the-broker) ("end the night") using `night-conductor`. (This stops the broker components so that they are inactive and we do not continue paying for them; it does not delete your broker instance.)

Code follows.

##### Start the broker

```bash
testid=mytest
instancename="night-conductor-${testid}"
zone=us-central1-a
broker_bucket="${GOOGLE_CLOUD_PROJECT}-broker_files-${testid}"

#--- Start the broker without the consumer
# set the attributes
NIGHT="START"
KAFKA_TOPIC="NONE" # tell night-conductor to skip booting up consumer VM
gcloud compute instances add-metadata "$instancename" --zone="$zone" \
        --metadata NIGHT="$NIGHT",KAFKA_TOPIC="$KAFKA_TOPIC"
# night-conductor will get the testid by parsing its own instance name

# the startup script should already be set, but we can make sure
startupscript="gs://${broker_bucket}/night_conductor/vm_startup.sh"
gcloud compute instances add-metadata "$instancename" --zone "$zone" \
        --metadata startup-script-url="$startupscript"

# start the VM to trigger the startup script
gcloud compute instances start "$instancename" --zone "$zone"
# night-conductor shuts down automatically when broker startup is complete

#--- After a few minutes, the broker should be ready to process alerts.
#    Feed alerts into the system using the consumer simulator.

```

For more information, see:
- [View and Access Resources](#view-and-access-resources)
- [Where to look if there's a problem with `night-conductor`'s start/end night routines](#where-to-look-if-theres-a-problem-with-night-conductors-startend-night-routines)

##### Run the consumer simulator
Before starting this section, make sure your Dataflow jobs are running (if desired). Check the
[Dataflow jobs console](https://console.cloud.google.com/dataflow/jobs?project=ardent-cycling-243415).
When deployed, these jobs create _new_ subscriptions to the `ztf_alerts-{testid}` Pub/Sub topic, so _they will miss any alerts published to that topic prior to their deployment_.
(The Cloud Functions, by contrast, are always "on" and listening to the stream.)

You may need to update to the latest version (2.2.0) of the PubSub API: `pip install google-cloud-pubsub --upgrade`

```python
#--- Put the `dev_utils` directory on your path
# I will add this to the broker's setup instructions later.
import sys
# path_to_dev_utils = '/Users/troyraen/Documents/PGB/repo/dev_utils'
path_to_dev_utils = '/home/troy_raen_pitt/Pitt-Google-Broker/dev_utils'
sys.path.append(path_to_dev_utils)

#--- import the simulator
from consumer_sims import ztf_consumer_sim as zcs

#--- set some variables to use later
N = 10
aRate = 600

#--- Set desired alert rate. Examples:
alertRate = (aRate, 'perMin')  # (int, str)
    # unit (str) options: 'perSec', 'perMin', 'perHr', 'perNight'(=per 10 hrs)
alertRate = (N, 'once')
    # publish N alerts simultaneously, one time
alertRate = 'ztf-active-avg'  # = (300000, 'perNight')
    # avg rate for an avg, active night (range 150,000 - 450,000 perNight)
alertRate = 'ztf-live-max'  # = (200, 'perSec')
    # approx max incoming rate seen from live ZTF stream

#--- Set desired amount of time the simulator runs
runTime = (N, 'min')  # (int, str)
    # unit (str) options: 'sec', 'min', 'hr', 'night'(=10 hrs)
    # if alertRate "units" == 'once', setting runTime has no effect

#--- Set the rate at which batches are published (optional)
publish_batch_every = (5, 'sec')  # (int, str)
    # only str option is 'sec'
# In practice: the simulator publishes a batch, then sleeps for a time publish_batch_every.
# If you set a number that is too low, processing time will rival sleep time,
# and the actual publish rate and run time may be quite different than expected.
# I have only tested the default setting, which is (5, 'sec').

#--- Run the simulator (examples)
testid = 'mytest'

# publish N alerts, 1 time
alertRate = (N, 'once')
zcs.publish_stream(testid, alertRate)

# publish alerts for N minutes, at the average rate of an active ZTF night
alertRate = 'ztf-active-avg'
runTime = (N, 'min')
zcs.publish_stream(testid, alertRate, runTime)

# publish for N minutes, at avg rate of 30 alerts/sec, at a publish rate of 1 batch/min
alertRate = (30, 'perSec')
runTime = (N, 'min')
publish_batch_every = (60, 'sec')
zcs.publish_stream(testid, alertRate, runTime, publish_batch_every)

# Connect the simulator to your own reservoir,
# creating a closed loop between your data stream and reservoir.
# (Assumes you previously tapped the main reservoir and ingested at least 1 alert.)
sub_id = f'ztf_alerts-reservoir-{testid}'
zcs.publish_stream(testid, alertRate, runTime, sub_id=sub_id)

# Connect the simulator to a different sink (topic).
# By default, the simulator publishes to the topic `ztf_alerts-{testid}`,
# but you can publish to an arbitrary topic (which must already exist).
topic_id = f'troy_test_topic'
zcs.publish_stream(testid, alertRate, runTime, topic_id=topic_id)

# nack the messages so that they do not disappear from the reservoir
nack = True
zcs.publish_stream(testid, alertRate, runTime, nack=nack)
```
