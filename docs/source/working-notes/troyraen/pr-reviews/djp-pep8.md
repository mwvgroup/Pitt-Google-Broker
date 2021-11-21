## djp-pep8: Summary

The value_added Dataflow job fails because I have made a backwards incompatible change to `broker_utils`.
Everything else in the pipeline looks like it runs fine.

I did not test the changes to `broker_utils`... the components get it from PyPI, not from this repo.


### Code used to create and run the broker testing instance

Create/delete a broker testing instance
```bash
# get the code
git clone https://github.com/mwvgroup/Pitt-Google-Broker
cd Pitt-Google-Broker
git checkout dfperrefort/pep8
cd broker/setup_broker

# create/delete the instance
# survey="decat"
survey="ztf"
testid="pep8"
teardown="False"
# teardown="True"
./setup_broker.sh "$testid" "$teardown" "$survey"


# name some things
nconductVM="${survey}-night-conductor-${testid}"
```


Start the broker
```bash
topic="${survey}-cue_night_conductor-${testid}"
cue=START
attr=KAFKA_TOPIC=NONE
# attr=topic_date=20210820
gcloud pubsub topics publish "$topic" --message="$cue" --attribute="$attr"
```

Run the consumer simulator
```python
from broker_utils import consumer_sim as bcs

testid = 'pep8'
survey = 'ztf'
instance = (survey, testid)
# alert_rate = (5, 'once')
alert_rate = 'ztf-active-avg'
runtime = (10, 'min')  # options: 'sec', 'min', 'hr', 'night'(=10 hrs)

bcs.publish_stream(alert_rate, instance, runtime=runtime)
```
