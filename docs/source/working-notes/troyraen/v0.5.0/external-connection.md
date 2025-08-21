# docs/source/working-notes/troyraen/v0.5.0/external-connection.md

## external-connection

Goal: Try to listen to and process one of our Pub/Sub streams as an outside user.


### GCP and local setup for external account
<!-- fs -->
Following [initial-setup.md](initial-setup.md)
```bash
PROJECT_ID=my-pgb-project-3  # through account raen.troy@gmail.com
ZONE=us-central1-a

conda create -n mypgb python=3.7
conda activate mypgb

gcloud auth login
gcloud config set project $PROJECT_ID

# create gcp service account and download key file
NAME=mypgb-raentroy-service-account
KEY_PATH=/Users/troyraen/Documents/broker/repo/GCP_auth_key-mypgb-raentroy.json
gcloud iam service-accounts create $NAME
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$NAME@$PROJECT_ID.iam.gserviceaccount.com" --role="roles/owner"
gcloud iam service-accounts keys create $KEY_PATH --iam-account=$NAME@$PROJECT_ID.iam.gserviceaccount.com


# enable APIs
gcloud services list --available  # check what's available
gcloud services enable pubsub.googleapis.com  # enable pubsub

# setup environment
cd $CONDA_PREFIX
mkdir -p ./etc/conda/activate.d
mkdir -p ./etc/conda/deactivate.d
touch ./etc/conda/activate.d/env_vars.sh
touch ./etc/conda/deactivate.d/env_vars.sh
echo "export GOOGLE_CLOUD_PROJECT=$PROJECT_ID" >> ./etc/conda/activate.d/env_vars.sh
echo "export GOOGLE_APPLICATION_CREDENTIALS=$KEY_PATH" >> ./etc/conda/activate.d/env_vars.sh
echo "export CLOUDSDK_COMPUTE_ZONE=$ZONE" >> ./etc/conda/activate.d/env_vars.sh
echo "unset GOOGLE_CLOUD_PROJECT" >> ./etc/conda/deactivate.d/env_vars.sh
echo "unset GOOGLE_APPLICATION_CREDENTIALS" >> ./etc/conda/deactivate.d/env_vars.sh
echo "unset CLOUDSDK_COMPUTE_ZONE" >> ./etc/conda/deactivate.d/env_vars.sh

# install pgb-utils in development mode
cd /Users/troyraen/Documents/broker/repo2/pgb_utils
python -m pip install -e .

```

<!-- fe GCP and local setup -->

### Setup IAM permissions on the Pub/Sub topic
<!-- fs -->
Allow any GCP user to attach a subscription to our topic.
- https://cloud.google.com/pubsub/docs/access-control#setting_a_policy
- https://cloud.google.com/iam/docs/creating-custom-roles#creating_a_custom_role

```bash
PROJECT=$GOOGLE_CLOUD_PROJECT

# create a new Role specifically for this purpose
roleid="pubsub.topics.attachSubscription"
roleyaml="PS_attachSubscription_role.yaml"
gcloud iam roles create $roleid --project=$PROJECT --file=$roleyaml

# set a policy on the topic that grants allUsers this role
TOPIC="test"
topic_path="projects/${PROJECT}/topics/${TOPIC}"
fname="topic_policy.yaml"
# download the topic to get the etag
gcloud pubsub topics get-iam-policy $topic_path --format yaml > $fname
# update the file with the new policy
# set the new policy
gcloud pubsub topics set-iam-policy $topic_path $fname
```

<!-- fe IAM permissions -->

### Create subscription and pull
<!-- fs -->
__Command line:__
- [Quickstart using the gcloud command-line tool](https://cloud.google.com/pubsub/docs/quickstart-cli)
- [gcloud pubsub subscriptions pull](https://cloud.google.com/sdk/gcloud/reference/pubsub/subscriptions/pull)

```bash
# create the subscription
# gcloud pubsub topics create TOPIC_ID
gcloud pubsub subscriptions create SUBSCRIPTION_ID --topic=TOPIC_ID

# pull messages
limit=1  # default=1
gcloud pubsub subscriptions pull my-sub --auto-ack --limit=$limit
```

__Python:__
```python
from google.cloud import pubsub_v1
import os

my_project = os.getenv('GOOGLE_CLOUD_PROJECT')
pgb_project = 'ardent-cycling-243415'

subscription = 'test'
topic = 'test'

subscriber = pubsub_v1.SubscriberClient()
publisher = pubsub_v1.PublisherClient()

sub_path = subscriber.subscription_path(my_project, subscription)
topic_path = publisher.topic_path(pgb_project, topic)
subscriber.create_subscription(sub_path, topic_path)

# test it
from pgb_utils import pubsub as pgbps
msg = b'TESTmsg'
pgbps.publish(topic, msg)  # EXECUTE FROM PGB ACCOUNT
smsg = pgbps.pull(subscription, project_id=my_project)  # EXECUTE FROM EXTERNAL ACCOUNT

```
<!-- fe subscription -->

### Setup stream-looper VM and topic

see [stream-looper.md](stream-looper.md)
