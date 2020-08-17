#!/bin/sh

echo "WARNING: Make sure you have updated the values of [IMAGE NAME] and [VERSION] with the values of the current Docker image using this script.\n"
# version number should be most recent commit used to build the image
# git log -1 --format=format:"%H"

# Create 2 instances of the consumer

gcloud compute instances create-with-container consume-ztf-1 --zone=us-central1-a --machine-type=f1-micro --image-project=cos-cloud --container-image=gcr.io/ardent-cycling-243415/consume_ztf:5a1ddf883efa0ad121d0f6584e1e73039b3727e4 --labels=env=consume-ztf-1 --image=cos-stable-81-12871-1185-0 --service-account=591409139500-compute@developer.gserviceaccount.com --scopes=cloud-platform

gcloud compute instances create-with-container consume-ztf-2 --zone=us-central1-a --machine-type=f1-micro --image-project=cos-cloud --container-image=gcr.io/ardent-cycling-243415/consume_ztf:5a1ddf883efa0ad121d0f6584e1e73039b3727e4 --labels=env=consume-ztf-2 --image=cos-stable-81-12871-1185-0 --service-account=591409139500-compute@developer.gserviceaccount.com --scopes=cloud-platform


# Create the Pub/Sub topics to trigger starting and stopping the instance
gcloud pubsub topics create start-instance-event
gcloud pubsub topics create stop-instance-event


# Create the cloud functions to publish to PubSub

cd scheduleinstance/

gcloud functions deploy startInstancePubSub --trigger-topic start-instance-event --runtime nodejs8

gcloud functions deploy stopInstancePubSub --trigger-topic stop-instance-event --runtime nodejs8

# Finally, schedule the PubSub messages that trigger the cloud functions.

# Reset consume-ztf-1 on odd days
gcloud scheduler jobs create pubsub stop-consume-ztf-1 --schedule '0 9 1-31/2 * *' --topic stop-instance-event --message-body '{"zone":"us-west1-b", "label":"env=consume-ztf-1"}' --time-zone 'America/Los_Angeles'

gcloud scheduler jobs create pubsub start-consume-ztf-1 --schedule '0 17 1-31/2 * *' --topic start-instance-event --message-body '{"zone":"us-west1-b", "label":"env=consume-ztf-1"}' --time-zone 'America/Los_Angeles'

# Reset consume-ztf-2 on even days
gcloud scheduler jobs create pubsub stop-consume-ztf-2 --schedule '0 0 2-30/2 * *' --topic stop-instance-event --message-body '{"zone":"us-west1-b", "label":"env=consume-ztf-2"}' --time-zone 'America/Los_Angeles'

gcloud scheduler jobs create pubsub start-consume-ztf-2 --schedule '0 0 2-30/2 * *' --topic start-instance-event --message-body '{"zone":"us-west1-b", "label":"env=consume-ztf-2"}' --time-zone 'America/Los_Angeles'
