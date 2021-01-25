# Pitt-Google LSST Broker

## Table of Contents
- [Broker Architecture](#broker-architecture)
- [Setup the Broker for the First Time](#setup-the-broker-for-the-first-time)
- [Run Nightly Broker](#run-nightly-broker)
- [original README](#ogread)

## Other useful reference docs
- [broker/consumer/__kafka-console-connect__.md](broker/consumer/kafka_console_connect.md)
- [broker/beam/__beam_dataflow_primer__.md](broker/beam/beam_dataflow_primer.md)

---

# Broker Architecture
<!-- fs -->
In short:

There are 4 main components:
- The __consumer__ ingests the ZTF Kafka stream and republishes it as a Pub/Sub stream.
- The __data storage__ (x2) and __processing__ (x1) components ingest the consumer's Pub/Sub stream and proceed with their function. These components store their output data to Cloud Storage and/or BigQuery, and publish it to a dedicated Pub/Sub topic/stream.

In addition, there is a "__night conductor__" (running on a VM) that
orchestrates the broker,
starting up resources and jobs at night (and will shut them down in the morning, but that script isn't written yet).

You can monitor the broker at the [__ZTF Stream Monitoring Dashboard__](https://console.cloud.google.com/monitoring/dashboards/builder/d8b7db8b-c875-4b93-8b31-d9f427f0c761?project=ardent-cycling-243415&dashboardBuilderState=%257B%2522editModeEnabled%2522:false%257D&timeDomain=1w).

Details:

1. __ZTF Alert Stream Consumer__ (ZTF Alert: Kafka -> Pub/Sub)
    - __Compute Engine VM:__  [`ztf-consumer`](https://console.cloud.google.com/compute/instancesMonitoringDetail/zones/us-central1-a/instances/ztf-consumer?project=ardent-cycling-243415&tab=monitoring&duration=PT1H)
    - __Running__  Kafka Connect [`CloudPubSubConnector`](https://github.com/GoogleCloudPlatform/pubsub/tree/master/kafka-connector)
    - __Publishes to__ Pub/Sub topic:  [`ztf_alert_data`](https://console.cloud.google.com/cloudpubsub/topic/detail/ztf_alert_data?project=ardent-cycling-243415)

2. __Avro File Storage__ (ZTF Alert -> Fix Schema -> GCS bucket)
    - __Cloud Function:__
 [`upload_ztf_bytes_to_bucket`](https://console.cloud.google.com/functions/details/us-central1/upload_ztf_bytes_to_bucket?project=ardent-cycling-243415&pageState=%28%22functionsDetailsCharts%22:%28%22groupValue%22:%22P1D%22,%22customValue%22:null%29%29)
    - __Listens to__ PS topic: [`ztf_alert_data`](https://console.cloud.google.com/cloudpubsub/topic/detail/ztf_alert_data?project=ardent-cycling-243415)
    - __Stores in__ GCS bucket: [`ztf_alert_avro_bucket`](https://console.cloud.google.com/storage/browser/ardent-cycling-243415_ztf_alert_avro_bucket;tab=objects?forceOnBucketsSortingFiltering=false&project=ardent-cycling-243415&prefix=&forceOnObjectsSortingFiltering=false)
    - __GCS bucket triggers__ Pub/Sub topic: [`ztf_alert_avro_bucket`](https://console.cloud.google.com/cloudpubsub/topic/detail/ztf_alert_avro_bucket?project=ardent-cycling-243415)

3. __BigQuery Database Storage__ (ZTF Alert -> BigQuery)
    - __Dataflow job:__ [`production-ztf-ps-bq`](https://console.cloud.google.com/dataflow/jobs?project=ardent-cycling-243415)
    - __Listens to__ PS topic: [`ztf_alert_data`](https://console.cloud.google.com/cloudpubsub/topic/detail/ztf_alert_data?project=ardent-cycling-243415)
    - __Stores in__ BQ table: [`ztf_alerts.alerts`](https://console.cloud.google.com/bigquery?project=ardent-cycling-243415) (ZTF alert data)

4. __Data Processing (value-added products)__ (ZTF Alert -> Extragalactic Transients Filter -> Salt2 Fit)
    - __Dataflow job:__ [`production-ztf-ps-exgal-salt2`](https://console.cloud.google.com/dataflow/jobs?project=ardent-cycling-243415)
    - __Listens to__ PS topic: [`ztf_alert_data`](https://console.cloud.google.com/cloudpubsub/topic/detail/ztf_alert_data?project=ardent-cycling-243415)
    - __Stores in__ BQ table: [`ztf_alerts.salt2`](https://console.cloud.google.com/bigquery?project=ardent-cycling-243415) (Salt2 fit params)
    - __Stores in__ GCS bucket: [`ztf-sncosmo/salt2/plot_lc`](https://console.cloud.google.com/storage/browser/ardent-cycling-243415_ztf-sncosmo/salt2/plot_lc?pageState=%28%22StorageObjectListTable%22:%28%22f%22:%22%255B%255D%22%29%29&project=ardent-cycling-243415&prefix=&forceOnObjectsSortingFiltering=false) (lightcurve + Salt2 fit, png)
    - __Publishes to__ PS topics:
        - [ `ztf_exgalac_trans`](https://console.cloud.google.com/cloudpubsub/topic/detail/ztf_exgalac_trans?project=ardent-cycling-243415) (alerts passing extragalactic transient filter)
        - [`ztf_salt2`](https://console.cloud.google.com/cloudpubsub/topic/detail/ztf_salt2?project=ardent-cycling-243415) (Salt2 fit params)

5. __Night Conductor__ (orchestrates GCP resources and jobs to run the broker each night)
    - __Compute Engine VM:__  [`night-conductor`](https://console.cloud.google.com/compute/instancesDetail/zones/us-central1-a/instances/night-conductor?tab=details&project=ardent-cycling-243415)

<!-- fe Broker Architecture -->

---

# Setup the Broker for the First Time
<!-- fs -->
[Note:] Please don't actually try to setup the broker right now. A test-setup hasn't been configured yet, and the real resources already exist.

1. Setup and configure a new Google Cloud Platform (GCP) project.
    - [Instructions in our current docs](https://pitt-broker.readthedocs.io/en/latest/installation_setup/installation.html). We would need to follow pieces of the "Installation" and "Defining Environmental Variables" sections. Our project is already setup, so leaving out most of the details for now.
    - [ToDo] Update this section.

2. Install GCP tools:
    - [Google Cloud SDK](https://cloud.google.com/sdk/docs/install): Follow the instructions at the link. (This installs `gcloud`, `gsutil` and `bq` command line tools)
    - [Cloud Client Libraries for Python](https://cloud.google.com/python/docs/reference): Each service requires a different library; the ones we need are (I hope) all listed in the `requirements.txt` in this directory. Install them with (e.g., ) `pip install -r requirements.txt`.

3. Clone the repo and run the broker's setup script.
The script will:
    1. Create and configure GCP resources in BigQuery, Cloud Storage, and Pub/Sub)
    2. Upload some broker files to the Cloud Storage bucket [ardent-cycling-243415-broker_files](https://console.cloud.google.com/storage/browser/ardent-cycling-243415-broker_files?project=ardent-cycling-243415&pageState=%28%22StorageObjectListTable%22:%28%22f%22:%22%255B%255D%22%29%29&prefix=&forceOnObjectsSortingFiltering=false). The VMs will fetch a new copy of these files before running the relevant process. This provides us with the flexibility to update individual broker processes/components by simply uploading a new version of the relevant file(s) to the bucket, avoiding the need to re-deploy the broker or VM to make an update.
    3. Setup the Pub/Sub stream that announces a new file in the [`ztf_alert_avro_bucket`]((https://console.cloud.google.com/storage/browser/ardent-cycling-243415_ztf_alert_avro_bucket;tab=objects?forceOnBucketsSortingFiltering=false&project=ardent-cycling-243415&prefix=&forceOnObjectsSortingFiltering=false)).
    4. Deploys the Cloud Function [`upload_ztf_bytes_to_bucket`](https://console.cloud.google.com/functions/details/us-central1/upload_ztf_bytes_to_bucket?project=ardent-cycling-243415&pageState=%28%22functionsDetailsCharts%22:%28%22groupValue%22:%22P1D%22,%22customValue%22:null%29%29) which stores alerts as Avro files in Cloud Storage.
    5. Create and configure the Compute Engine instances ([`night-conductor`](https://console.cloud.google.com/compute/instancesDetail/zones/us-central1-a/instances/night-conductor?tab=details&project=ardent-cycling-243415) and [`ztf-consumer`](https://console.cloud.google.com/compute/instancesMonitoringDetail/zones/us-central1-a/instances/ztf-consumer?project=ardent-cycling-243415&tab=monitoring&duration=PT1H&pageState=%28%22duration%22:%28%22groupValue%22:%22P7D%22,%22customValue%22:null%29%29))

```bash
# If you used a virtual environment to complete the previous setup steps,
# activate it.

# GOOGLE_CLOUD_PROJECT env variable should have been defined/set in step 1.
# Set it now if needed:
export GOOGLE_CLOUD_PROJECT=ardent-cycling-243415
# The Compute Engine VMs (instances) must be assigned to a specific zone.
# We use the same zone for all instances:
export CE_zone=us-central1-a

# Clone the broker repo
git clone https://github.com/mwvgroup/Pitt-Google-Broker

# Run the broker's setup script
cd Pitt-Google-Broker/setup_broker
# ./setup_broker.sh  
# Please don't actually run the setup right now.
```

4. The `ztf-consumer` VM (created in `setup_broker.sh`) requires two auth files (not included with the broker) to connect to the ZTF stream.
_These must be uploaded manually and stored at the following locations:_
    1. `krb5.conf`, at VM path `/etc/krb5.conf`
    2. `pitt-reader.user.keytab`, at VM path `/home/broker/consumer/pitt-reader.user.keytab`
You can use the `gcloud compute scp` command for this:

```bash
gcloud compute scp \
    /path/to/local/file \
    ztf-consumer:/path/to/vm/file \
    --zone=${CE_zone}
```

<!-- fe Setup the Broker -->

---

# Run Nightly Broker
<!-- fs -->
[[__ZTF Stream Monitoring Dashboard__](https://console.cloud.google.com/monitoring/dashboards/builder/d8b7db8b-c875-4b93-8b31-d9f427f0c761?project=ardent-cycling-243415&dashboardBuilderState=%257B%2522editModeEnabled%2522:false%257D&timeDomain=1w)]

The set of scripts in [night_conductor](broker/night_conductor/) orchestrates the tasks required to start up the broker at night and shut it down in the morning.
We run these scripts on a dedicated Compute Engine instance, [__`night-conductor`__](https://console.cloud.google.com/compute/instancesDetail/zones/us-central1-a/instances/night-conductor?tab=details&project=ardent-cycling-243415).
These scripts were uploaded, along with other files that run the nightly broker (e.g., Consumer and Beam jobs), to the Cloud Storage bucket [`broker_files`](https://console.cloud.google.com/storage/browser/ardent-cycling-243415-broker_files?project=ardent-cycling-243415) upon initial setup (see [Setup the Broker for the First Time](#setup-the-broker-for-the-first-time)) and are updated as the broker evolves.
The `night-conductor` VM is configured with a startup script that downloads these scripts and other files from the bucket and executes them.
We use Compute Engine __metadata attributes__ to pass variables to `night-conductor`'s startup script which determine the specific behavior.
(See [Storing and retrieving instance metadata](https://cloud.google.com/compute/docs/storing-retrieving-metadata) and [Setting custom metadata](https://cloud.google.com/compute/docs/storing-retrieving-metadata#custom).)
Then, __to start or stop the broker for the night, we simply set the metadata attribute(s) and start the `night-conductor` VM__:

```bash
instancename=night-conductor
zone=us-central1-a

# start the night
NIGHT=START
KAFKA_TOPIC=ztf_20210120_programid1
gcloud compute instances add-metadata ${instancename} --zone=${zone} \
      --metadata NIGHT=${NIGHT},KAFKA_TOPIC=${KAFKA_TOPIC}
gcloud compute instances start ${instancename} --zone ${zone}
# `night-conductor` shuts down automatically when broker startup is complete

# end the night
NIGHT=END
gcloud compute instances add-metadata ${instancename} --zone=${zone} \
      --metadata NIGHT=${NIGHT}
gcloud compute instances start ${instancename} --zone ${zone}
# `night-conductor` shuts down automatically when broker teardown is complete
```

Metadata attributes are cleared before `night-conductor` shuts down so that no unexpected behavior occurs on the next startup.

You can monitor the ingestion and processing at the [__ZTF Stream Monitoring Dashboard__](https://console.cloud.google.com/monitoring/dashboards/builder/d8b7db8b-c875-4b93-8b31-d9f427f0c761?project=ardent-cycling-243415&dashboardBuilderState=%257B%2522editModeEnabled%2522:false%257D&timeDomain=1w).

__Start/End Night Details:__

Currently, `night-conductor` executes the following to start the night:
1. Clears the messages from Pub/Sub subscriptions that we use to count the number of elements received and processed each night.
2. Starts the two Dataflow jobs.
3. Starts the [`ztf-consumer`](https://console.cloud.google.com/compute/instancesMonitoringDetail/zones/us-central1-a/instances/ztf-consumer?project=ardent-cycling-243415&tab=monitoring&duration=PT1H&pageState=%28%22duration%22:%28%22groupValue%22:%22P7D%22,%22customValue%22:null%29%29) VM (which is configured to connect to ZTF and begin ingesting upon startup).

And the following to end the night:
1. Stop the [`ztf-consumer`](https://console.cloud.google.com/compute/instancesMonitoringDetail/zones/us-central1-a/instances/ztf-consumer?project=ardent-cycling-243415&tab=monitoring&duration=PT1H&pageState=%28%22duration%22:%28%22groupValue%22:%22P7D%22,%22customValue%22:null%29%29) VM (which stops the ingestion).
2. Stop and drain the Dataflow jobs.

__Note on staging files:__

Staging the startup scripts and other files in a Cloud Storage bucket means that we can update these broker components simply by uploading a new file to the bucket; we do not have to build a new Docker image, repackage, or redeploy.
All VMs pull down a fresh copy of any required file(s) before executing the relevant process.
(Cloud Functions are different and must be re-deployed to be updated. Once deployed, they are always "on"; `night-conductor` does not manage them.)

__Note on triggering `night-conductor` to start/end the night:__

[Start Night] The consumer's connection to ZTF will fail if there is not as least 1 alert in the topic (ZTF publishes to a new topic nightly).
Even though the connection fails, the terminal/shell is not released,
so we can't simply keep trying until the connection succeeds.
Therefore I am still manually triggering `night-conductor` to start the night after ZTF issues its first alert.
There _should_ be a programatic way to check whether a topic is available, but I haven't been able to find it yet.
I have a new lead, so I'll work on it more.

[End Night] There is no programatic way to check whether ZTF has sent its last alert for the night,
or to check whether we have received all the alerts ZTF has sent.
Christopher Phillips at ZTF says we can assume that ZTF has sent out all of its alerts by shortly after sunrise ZTF time.
I am still manually triggering `night-conductor` to end the night.
Over the last ~2 months (today is 1/19/21), ZTF has consistently been done issuing alerts by 9:30am ET, and our broker does not have a significant lag.
I plan to automate triggering `night-conductor` to end the night at 10am ET, but this will need to be adjusted seasonally.

<!-- fe Run Nightly Broker -->


---
<a name="ogread"></a>
The following is the original README:
<!-- fs -->

[![python](https://img.shields.io/badge/python-3.7-g.svg)]()
[![Build Status](https://travis-ci.com/mwvgroup/Pitt-Google-Broker.svg?branch=master)](https://travis-ci.com/mwvgroup/Pitt-Google-Broker)
[![Documentation Status](https://readthedocs.org/projects/pitt-broker/badge/?version=latest)](https://pitt-broker.readthedocs.io/en/latest/?badge=latest)

Data from the Large Synoptic Survey Telescope ([LSST](https://www.lsst.org)) will be distributed through three distinct avenues. The first is a real-time stream of alerts that provides information on transient targets within 60 seconds of observation. The second is a daily data release, which contains the same information as the 60-second alerts plus some additional information. The last data product will be a yearly data release.

The 60-second alert stream will not be made available to the public (at least not in its entirety). Instead, LSST will rely on a small number of (~7) community developed *broker* systems to publically relay the information. This repo represents the construction of an LSST broker designed to run on the Google Cloud Platform ([GCP](https://cloud.google.com)) using alerts from the Zwicky Transient Facility ([ZTF](https://www.ztf.caltech.edu)) as a testing ground.

Full online documentation is available online via [Read the Docs](https://pitt-broker.readthedocs.io/en/latest/index.html).

<!-- fe OG readme -->
