# Setup a Broker Instance

- [Prerequisites](#prerequisites)
- [Setup a Broker Instance](#setup-a-broker-instance)
    - [Upload Kafka Authentication Files](#upload-kafka-authentication-files)
    - [Shutdown the VMs](#shutdown-the-vms)
- [What does `setup_broker.sh` do?](#what-does-setup_brokersh-do)

---

## Prerequisites
First, complete the [Initial Setup](initial-setup.md) to setup your Google Cloud project and install the SDKs. Make sure your environment variables are set:

```bash
# If you installed the SDKs to a Conda environment, activate it.
export GOOGLE_CLOUD_PROJECT=ardent-cycling-243415
export GOOGLE_APPLICATION_CREDENTIALS=<path/to/GCP/credentials.json>
```

---

## Setup a Broker Instance
```bash
# Clone the repo and navigate to the setup directory
git clone https://github.com/mwvgroup/Pitt-Google-Broker
cd Pitt-Google-Broker/broker/setup_broker

# Setup a broker instance
survey=ztf  # ztf or decat
testid=mytest  # replace with your choice of testid
teardown=False
./setup_broker.sh "$testid" "$teardown" "$survey"
```

See [What does `setup_broker.sh` do?](#what-does-setup_brokersh-do) for details.


### Upload Kafka Authentication Files

Note: Do this before the consumer VM finishes its install and shuts itself down.
Else, you'll need to start it again (see [here](view-resources.md#ce)).

The consumer VM requires two __authorization files__ to connect to the ZTF stream.
_These must be obtained independently and uploaded to the VM manually, stored at the following locations:_
    1. `krb5.conf`, at VM path `/etc/krb5.conf`
    2. `pitt-reader.user.keytab`, at VM path `/home/broker/consumer/pitt-reader.user.keytab`

You can use the `gcloud compute scp` command for this:
```bash
survey=ztf  # use the same survey used in broker setup
testid=mytest  # use the same testid used in broker setup

gcloud compute scp krb5.conf "${survey}-consumer-${testid}:/etc/krb5.conf" --zone="$CE_ZONE"
gcloud compute scp pitt-reader.user.keytab "${survey}-consumer-${testid}:/home/broker/consumer/pitt-reader.user.keytab" --zone="$CE_ZONE"
```

### Shutdown the VMs

1. Wait for VM install scripts to complete; they will take 15-20 minutes. You'll know they're done with the install scripts when the CPU utilization falls to >1% (see [View and Access Resources](view-resources.md), Dashboard or Compute Engine).

~2. Shutdown ("stop") both VMs using:~ Both VMs will now shut themselves down when they are done.

```bash
# survey=ztf  # use the same survey used in broker setup
# testid=mytest  # use the same testid used in broker setup
#
# zone=us-central1-a
# consumerVM="${survey}-consumer-${testid}"
# nconductVM="${survey}-night-conductor-${testid}"
#
# gcloud compute instances stop "$consumerVM" "$nconductVM" --zone="$zone"
```

Both VMs must be stopped before triggering `night-conductor` to run the broker, else it will not work.
Generally, stop the VMs when they're not actively in use so they don't incur charges.

---

## What does `setup_broker.sh` do?

Resource name stubs are given below in brackets [].
See [Broker Instance Keywords](../broker-design/broker-instance-keywords.md) for details.

1. Create and configure GCP resources in BigQuery, Cloud Storage, Dashboard, and Pub/Sub. Print a URL to the instance's Dashboard for the user. (You may be asked to authenticate yourself using `gcloud auth login`; follow the instructions. If you don't have a `bigqueryrc` config file setup yet it will walk you through creating one.)

2. Upload the directors broker/beam, broker/broker_utils/schema_maps, broker/consumer, and broker/night_conductor to the Cloud Storage bucket [`broker_files`].

3. Create and configure the Compute Engine instances [`night-conductor`] and [`consumer`].

4. Create Cloud Scheduler cron jobs [`cue_night_conductor_START`] and [`cue_night_conductor_END`] to put [`night-conductor`] on an auto-schedule. Print the schedule and the code needed to change it. If this is a Testing instance, pause the jobs and print the code needed to resume them.

5. Configure Pub/Sub notifications (topic [`alert_avros`]) on the Cloud Storage bucket [`alert_avros`] that stores the alert Avro.

6. Create a VM firewall rule to open the port used by ZTF's Kafka stream.
This step will _fail_ because the rule already exists and we don't need a separate rule for testing resources.
_You can ignore it._

7. Deploy Cloud Functions [`upload_bytes_to_bucket`], [`cue_night_conductor`], and [`check_cue_response`].
