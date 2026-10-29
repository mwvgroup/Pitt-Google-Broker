# Connect Pitt-Google to the IceCube Neutrino Observatory Alert Stream

Updated October 2026 - Author: Christopher Hernández

- [Overview](#overview)
- [Setup](#setup)
- [Deploy broker instance](#deploy-broker-instance)
- [Ingest the IceCube alert stream](#ingest-the-icecube-alert-stream)
- [Delete broker instance](#delete-broker-instance)

## Overview

Astrophysical neutrinos detected by the IceCube Neutrino Observatory are distributed publicly as
machine-readable alerts through
[General Coordinates Network (GCN) Notices](https://gcn.nasa.gov/docs/notices#gcn-notices).
Here are some links which were used as a reference to set this up:

- [Start streaming GCN Notices quick start quide](https://gcn.nasa.gov/quickstart)
- [Kafka Client Setup using Java](https://gcn.nasa.gov/docs/client#java)

Below is the code I used to set up the necessary resources in GCP to ingest the IceCube alert stream.

## Setup

The following assumes that you have:

- Completed the [GCN Notices quick start guide](https://gcn.nasa.gov/quickstart) and identified your client
credentials. This includes a client ID and client secret
- Set the environment variables `GOOGLE_CLOUD_PROJECT` and `GOOGLE_APPLICATION_CREDENTIALS` to appropriate values for
your GCP project and service account credentials
- Authenticated the service account to make `gcloud` calls through the project
- [Enabled the Secret Manager API](https://cloud.google.com/secret-manager/docs/configuring-secret-manager#enable_api)
in your Google Cloud Project

You may want to
[activate a service account for `gcloud` calls](https://pitt-broker.readthedocs.io/en/u-tjr-workingnotes/working-notes/troyraen/service-account.html#switch-the-service-account-your-api-calls-use)
or
[set up a GCP project from scratch](https://pitt-broker.readthedocs.io/en/latest/broker/run-a-broker-instance/initial-setup.html#setup-local-environment).

### Use GCP's Secret Manager

[Secret Manager](https://cloud.google.com/secret-manager/docs/overview) is a service that allows users to manage and
store sensitive data. Use the following code snippet to
[create secrets](https://cloud.google.com/secret-manager/docs/creating-and-accessing-secrets#create) for your client ID
and client secret. This information will be used to deploy a broker instance with your client credentials.

```bash
# define parameters
survey="icecube"
REGION="us-central1" # UPDATE ME
PROJECT_ID=$GOOGLE_CLOUD_PROJECT

# define secret names
client_id="${survey}-${PROJECT_ID}-client-id"
client_secret="${survey}-${PROJECT_ID}-client-secret"

# create secret(s)
gcloud secrets create "${client_id}" \
    --location="${REGION}"
gcloud secrets create "${client_secret}" \
    --location="${REGION}"
```

Select one of the following options to add a secret version. Note that adding a version directly on the command line is
discouraged by Google Cloud, see
[add a secret version documentation](https://cloud.google.com/secret-manager/docs/add-secret-version#add-secret-version)
for details.

```bash
# add a secret version from the contents of a file on disk
gcloud secrets versions add "${client_id}" --data-file="/path/to/file.txt"
gcloud secrets versions add "${client_secret}" --data-file="/path/to/file.txt"

# add a secret version directly on the command line
client_id_value="enter the client id provided by GCN" # UPDATE ME
client_secret_value="enter the client secret provided by GCN" # UPDATE ME
echo -n "${client_id_value}" | \
   gcloud secrets versions add "${client_id}" \
   --location="${REGION}" \
   --data-file=-
echo -n "${client_secret_value}" | \
    gcloud secrets versions add "${client_secret}" \
    --location="${REGION}" \
    --data-file=-
```

Access the [IAM & Admin page](https://console.cloud.google.com/iam-admin) and grant the default compute service account
the role of `Secret Manager Secret Accessor`.

```bash
user="[enter compute service account prefix]@developer.gserviceaccount.com"
roleid="roles/secretmanager.secretAccessor"
gcloud secrets add-iam-policy-binding "${client_id}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --member="serviceAccount:${user}" \
    --role="${roleid}"
gcloud secrets add-iam-policy-binding "${client_secret}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --member="serviceAccount:${user}" \
    --role="${roleid}"
```

### BigQuery subscriptions

Our broker uses [BigQuery subscriptions](https://cloud.google.com/pubsub/docs/bigquery) to write alert data directly to
a BigQuery table. Messages receieved by BigQuery subscriptions that fail to write data to BigQuery are negatively
acknowledged and re-sent. If the messages fail enough times (default number of attempts = 5), then the message is
subsequently moved to a [dead letter topic](https://cloud.google.com/pubsub/docs/handling-failures#dead_letter_topic).
A subscription to this dead letter topic is automatically made, allowing the user to identify which messages failed to
write data to BigQuery and why the write operation failed.

## Deploy broker instance

Clone the repo and cd into the directory:

```bash
git clone https://github.com/mwvgroup/Pitt-Google-Broker.git
cd Pitt-Google-Broker/broker/setup_broker/icecube
```

Initialize parameters and call the deployment script:

```bash
testid="mytest"
teardown="False"
survey="icecube"
schema_version="7.2.3"
region="us-central1"

./setup_broker.sh "${testid}" "${teardown}" "${survey}" "${schema_version}" "${region}"
```

This will create all of the necessary GCP resources. Allow the consumer VM to finish its installation process. Once
complete, the VM will shut down automatically. You can check the status of the VM in the
[Google Cloud Console](https://console.cloud.google.com/compute).
This entire process should take less than 10 minutes.

## Start the Consumer VM to ingest the IceCube alert stream

```bash
zone="${region}-a"
consumerVM="${survey}-consumer-${testid}"

# Set the VM metadata
KAFKA_TOPIC="gcn.notices.icecube.lvk_nu_track_search"
PS_TOPIC="${survey}-alerts-${testid}"
gcloud compute instances add-metadata "${consumerVM}" --zone "$zone" \
    --metadata="PS_TOPIC_FORCE=${PS_TOPIC},KAFKA_TOPIC_FORCE=${KAFKA_TOPIC}"

# Start the VM
gcloud compute instances start "${consumerVM}" --zone ${zone}
# this launches the startup script which configures and starts the
# Kafka -> Pub/Sub connector
```

You can also stop the VM by executing:

```bash
gcloud compute instances stop "${consumerVM}" --zone="${zone}"
```

## Delete broker instance

Similar to [deploy broker instance](#deploy-broker-instance). Initialize parameters and call the deployment script:

```bash
testid="mytest"
teardown="True"
survey="icecube"
schema_version="7.2.3"
region="us-central1"

./setup_broker.sh "${testid}" "${teardown}" "${survey}" "${schema_version}" "${region}"
```
