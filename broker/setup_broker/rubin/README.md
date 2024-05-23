# Connect Pitt-Google to the Rubin-Broker integration test stream

May 2024 - Author: Christopher Hernández

- [Overview](#overview)
- [Setup](#setup)
- [Ingest the Rubin test stream](#ingest-the-rubin-test-stream)
- [Delete broker instance](#delete-broker-instance)

## Overview

During the first week of May 2024, a broker integration exercise was held and focused on the topic of connectivity.
This document outlines my procedure in connecting to the test stream.

For this exercise, the same credentials as the IDF integration exercise were used. Credential information was emailed
to me by Troy Raen, and the credential value (e.g., `kafka_password`) was stored as a
[secret](https://cloud.google.com/secret-manager/docs/overview#secret) using Google Cloud's
[Secret Manager](https://cloud.google.com/secret-manager/docs/overview).

Details on the number of alerts in this exercise from a conversation with Brianna Smart:
"The DC2 finished producing alerts, putting 303,288 new alerts into the stream, for a total of 376,800, the first
76,800 of which are a small subset duplicated 3 times."

## Setup

This section assumes that you have:

- Set the environment variables `GOOGLE_CLOUD_PROJECT` and `GOOGLE_APPLICATION_CREDENTIALS` to appropriate values for
your GCP project and service account credentials
- Authenticated the service account to make `gcloud` calls through the project
- Enabled the [Secret Manager API](https://cloud.google.com/secret-manager/docs/configuring-secret-manager#enable_api)
in your Google Cloud Project
- Granted the default compute service account the role of `Secret Manager Secret Accessor` in the
[IAM & Admin page](https://console.cloud.google.com/iam-admin)

You may want to
[activate a service account for `gcloud` calls](https://pitt-broker.readthedocs.io/en/u-tjr-workingnotes/working-notes/troyraen/service-account.html#switch-the-service-account-your-api-calls-use)
or
[set up a GCP project from scratch](https://pitt-broker.readthedocs.io/en/latest/broker/run-a-broker-instance/initial-setup.html#setup-local-environment).

Create secrets for your access credential:

```bash
# define parameters
survey="rubin"
PROJECT_ID=$GOOGLE_CLOUD_PROJECT

# define secret names
kafka_password="${survey}-${PROJECT_ID}-kafka-password"

# create secret
gcloud secrets create "${kafka_password}" \
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

Clone the repo and cd into the directory:

```bash
git clone https://github.com/mwvgroup/Pitt-Google-Broker.git
cd Pitt-Google-Broker/broker/setup_broker/rubin
```

Define the variables used below.

```bash
testid="enter testid value"
teardown="False"
survey="rubin"
region="us-central1"
```

Execute the `setup_broker.sh` script:

```bash
./setup_broker.sh "${testid}" "${teardown}" "${survey}" "${region}"
```

This will create all of the necessary GCP resources. Allow the consumer VM to finish its installation process. Once
complete, the VM will shut down automatically. You can check the status of the VM in the
[Google Cloud Console](https://console.cloud.google.com/compute). This entire process should take less than 10 minutes.

## Ingest the Rubin test stream

### Setup Consumer VM

```bash
zone="${region}-a"
consumerVM="${survey}-consumer-${testid}"

# Set the VM metadata
KAFKA_TOPIC="alerts-simulated"
PS_TOPIC="${survey}-alerts-${testid}"
gcloud compute instances add-metadata "${consumerVM}" --zone "${zone}" \
    --metadata="PS_TOPIC_FORCE=${PS_TOPIC},KAFKA_TOPIC_FORCE=${KAFKA_TOPIC}"

# Start the VM
gcloud compute instances start "${consumerVM}" --zone ${zone}
# this launches the startup script which configures and starts the
# Kafka -> Pub/Sub connector
```

## Delete broker instance

Initialize parameters and call the deployment script:

```bash
testid="mytest"
teardown="True"
survey="rubin"
region="us-central1"

./setup_broker.sh "${testid}" "${teardown}" "${survey}" "${region}"
```
