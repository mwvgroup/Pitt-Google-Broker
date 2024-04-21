# Connect Pitt-Google to the LIGO/Virgo/KAGRA (LVK) Gravitational Wave Alert Stream

April 2024 - Author: Christopher Hernandez

- [Overview](#overview)
- [Setup](#setup)
- [Deploy broker instance](#deploy-broker-instance)
- [Ingest the LVK alert stream](#ingest-the-lvk-alert-stream)
- [Delete broker instance](#delete-broker-instance)

## Overview
Gravitational-wave transients detected by the LIGO, Virgo, and KAGRA network are distributed publicly as
machine-readable alerts through 
[General Coordinates Network (GCN) Notices](https://gcn.nasa.gov/docs/notices#gcn-notices).
Here are some links which were used as a reference to set this up:

- [Start streaming GCN Notices quick start quide](https://gcn.nasa.gov/quickstart)
- [Kafka Client Setup using Java](https://gcn.nasa.gov/docs/client#java)

Below is the code I used to set up the necessary resources in GCP to ingest the LVK alert stream.

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


[Create secrets](https://cloud.google.com/secret-manager/docs/creating-and-accessing-secrets#create) for your client ID
and client secret

```bash
# define parameters
survey="lvk"
PROJECT_ID=$GOOGLE_CLOUD_PROJECT

# define secret names
client_id="${survey}-${PROJECT_ID}-client-id"
client_secret="${survey}-${PROJECT_ID}-client-secret"

# create secret(s)

gcloud secrets create "${client_id}" \
    --replication-policy="automatic"
gcloud secrets create "${client_secret}" \
    --replication-policy="automatic"
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
echo -n "enter the client id provided by GCN" | \
    gcloud secrets versions add "${client_id}" --data-file=-
echo -n "enter the client secret provided by GCN" | \
    gcloud secrets versions add "${client_secret}" --data-file=-
```

## Deploy broker instance
Clone the repo and cd into the directory:

```bash
git clone https://github.com/mwvgroup/Pitt-Google-Broker.git
cd Pitt-Google-Broker/broker/setup_broker/lvk
```

Initialize parameters and call the deployment script:

```bash
testid="mytest"
teardown="False"
survey="lvk"
region="us-central1"

./setup_broker.sh "${testid}" "${teardown}" "${survey}" "${region}"
```

This will create all of the necessary GCP resources. Allow the consumer VM to finish its installation process. Once
complete, the VM will shut down automatically. You can check the status of the VM in the
[Google Cloud Console](https://console.cloud.google.com/compute). 
This entire process should take less than 10 minutes.

## Start the Consumer VM to ingest the LVK alert stream

```bash
zone="${region}-a"
consumerVM="${survey}-consumer-${testid}"

# Set the VM metadata
KAFKA_TOPIC="igwn.gwalert"
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
survey="lvk"
region="us-central1"

./setup_broker.sh "${testid}" "${teardown}" "${survey}" "${region}"
```
