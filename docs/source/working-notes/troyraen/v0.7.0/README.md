# v0.7.0

- Implements SuperNNova as a Cloud Function.
- Adds the extragalactic transients filter as a Cloud Function, emitting the Pub/Sub
  stream that SuperNNova listens to.

See [PR #71](https://github.com/mwvgroup/Pitt-Google-Broker/pull/71)

Working notes:

- [supernnova.md](https://github.com/mwvgroup/Pitt-Google-Broker/tree/troy/troy/SNN/supernnova.md)
  (implementing the pre-trained model provided by Anais)

- [supernnova_train_a_model.md](https://github.com/mwvgroup/Pitt-Google-Broker/tree/troy/troy/SNN/supernnova_train_a_model.md)
  (not necessary for this PR, but good for future reference)

## Test the changes

Note: The best place to see that/how well this is working is the ZTF *production*
instance, not the testing instance created below. The Cloud Function, etc. is isolated
from the rest of the broker pipeline and can't break anything else, so I threw it into
production early on. See:

- Cloud Functions

  - [ztf-filter_exgalac_trans](<https://console.cloud.google.com/functions/details/us-central1/ztf-filter_exgalac_trans?project=ardent-cycling-243415&pageState=(%22functionsDetailsCharts%22:(%22groupValue%22:%22P1D%22,%22customValue%22:null))>)
  - [ztf-classify_with_SuperNNova](<https://console.cloud.google.com/functions/details/us-central1/ztf-classify_with_SuperNNova?project=ardent-cycling-243415&pageState=(%22functionsDetailsCharts%22:(%22groupValue%22:%22P1D%22,%22customValue%22:null))>)

- Pub/Sub topics

  - [ztf-exgalac_trans_cf](https://console.cloud.google.com/cloudpubsub/topic/detail/ztf-exgalac_trans_cf?project=ardent-cycling-243415)
  - [ztf-SuperNNova](https://console.cloud.google.com/cloudpubsub/topic/detail/ztf-SuperNNova?project=ardent-cycling-243415)

- BigQuery table

  - [ztf_alerts.SuperNNova](https://console.cloud.google.com/bigquery?project=ardent-cycling-243415&d=ztf_alerts&p=ardent-cycling-243415&t=SuperNNova&page=table&ws=!1m5!1m4!4m3!1sardent-cycling-243415!2sztf_alerts!3sSuperNNova)

### Code used to create and run the broker testing instance

Create/delete a broker testing instance

```bash
# get the code
git clone https://github.com/mwvgroup/Pitt-Google-Broker
cd Pitt-Google-Broker
git checkout v/0.7.0/tjr
cd broker/setup_broker

# create/delete the instance
# survey="decat"
survey="ztf"
testid="v070"
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

testid = "v070"
survey = "ztf"
instance = (survey, testid)
# alert_rate = (5, 'once')
alert_rate = "ztf-active-avg"
runtime = (10, "min")  # options: 'sec', 'min', 'hr', 'night'(=10 hrs)

bcs.publish_stream(alert_rate, instance, runtime=runtime)
```
