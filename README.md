# Pitt-Google Broker

Pitt-Google Broker is an astronomical alert broker that is being developed for large scale surveys of the night sky, particularly the upcoming [Vera Rubin Observatory's Legacy Survey of Space and Time](https://www.lsst.org/) (LSST).
We currently process and serve the [Zwicky Transient Facility](https://www.ztf.caltech.edu/)'s (ZTF) nightly alert stream.

## Query, Download, and Process the Data

[Pitt-Google-Tutorial-Code-Samples.ipynb](pgb_utils/tutorials/Pitt-Google-Tutorial-Code-Samples.ipynb)

All data is public and is hosted in the [Google Cloud](https://cloud.google.com/).
It can be accessed using Google's [Cloud SDK](https://cloud.google.com/sdk) in many languages, including Python and from the command-line.
In addition, Pitt-Google Broker offers the Python package `pgb_utils` which contains wrappers of Cloud SDK methods for some common use cases, and other helper functions.
We view this package as a collection of examples demonstrating the use of the underlying methods.
The Cloud SDK is well developed and documented, and we intend for `pgb_utils` to be an entry point to learning the methods.
You are encouraged to view its source code and adapt/extend it for your specific use cases.
The [`pgb_utils`](pgb_utils) directory contains tutorial notebooks that will walk you through using the available tools to access and process the data.
Please open an Issue on GitHub or contact troy.raen@pitt.edu if you run into problems.

---
## Alert Broker Intro and Setup

What follows is instructions for running the broker. Users do NOT need to run the broker in order to access the data, and should instead proceed directly to the tutorial in [`pgb_utils`](pgb_utils).

- [Broker Architecture](#broker-architecture)
- [Setup the Broker for the First Time](#setup-the-broker-for-the-first-time)
- [Run Nightly Broker](#run-nightly-broker)
- [Note on Resources for Test Runs](#note-on-resources-for-test-runs)
- [original README](#ogread)

__Useful tutorial/reference docs__
- [__broker/README__.md](broker/README.md)
- [broker/consumer/__kafka_console_connect__.md](broker/consumer/kafka_console_connect.md)
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

You can monitor the production broker at the [__ZTF Stream Monitoring Dashboard__](https://console.cloud.google.com/monitoring/dashboards/builder/d8b7db8b-c875-4b93-8b31-d9f427f0c761?project=ardent-cycling-243415&dashboardBuilderState=%257B%2522editModeEnabled%2522:false%257D&timeDomain=1w).

Details:

1. __ZTF Alert Stream Consumer__ (ZTF Alert: Kafka -> Pub/Sub)
    - __Compute Engine VM:__  [`ztf-consumer`](https://console.cloud.google.com/compute/instancesMonitoringDetail/zones/us-central1-a/instances/ztf-consumer?project=ardent-cycling-243415&tab=monitoring&duration=PT1H)
    - __Running__  Kafka Connect [`CloudPubSubConnector`](https://github.com/GoogleCloudPlatform/pubsub/tree/master/kafka-connector)
    - __Publishes to__ Pub/Sub topic:  [`ztf_alerts`](https://console.cloud.google.com/cloudpubsub/topic/detail/ztf_alerts?project=ardent-cycling-243415)

2. __Avro File Storage__ (ZTF Alert -> Fix Schema -> GCS bucket)
    - __Cloud Function:__
 [`upload_ztf_bytes_to_bucket`](https://console.cloud.google.com/functions/details/us-central1/upload_ztf_bytes_to_bucket?project=ardent-cycling-243415&pageState=%28%22functionsDetailsCharts%22:%28%22groupValue%22:%22P1D%22,%22customValue%22:null%29%29)
    - __Listens to__ PS topic: [`ztf_alerts`](https://console.cloud.google.com/cloudpubsub/topic/detail/ztf_alerts?project=ardent-cycling-243415)
    - __Stores in__ GCS bucket: [`ztf_alert_avros`](https://console.cloud.google.com/storage/browser/ardent-cycling-243415_ztf_alert_avros;tab=objects?forceOnBucketsSortingFiltering=false&project=ardent-cycling-243415&prefix=&forceOnObjectsSortingFiltering=false)
    - __GCS bucket triggers__ Pub/Sub topic: [`ztf_alert_avros`](https://console.cloud.google.com/cloudpubsub/topic/detail/ztf_alert_avros?project=ardent-cycling-243415)

3. __BigQuery Database Storage__ (ZTF Alert -> BigQuery)
    - __Dataflow job:__ [`production-ztf-ps-bq`](https://console.cloud.google.com/dataflow/jobs?project=ardent-cycling-243415)
    - __Listens to__ PS topic: [`ztf_alerts`](https://console.cloud.google.com/cloudpubsub/topic/detail/ztf_alerts?project=ardent-cycling-243415)
    - __Stores in__ BQ table: [`ztf_alerts.alerts`](https://console.cloud.google.com/bigquery?project=ardent-cycling-243415) (ZTF alert data)

4. __Data Processing (value-added products)__ (ZTF Alert -> Extragalactic Transients Filter -> Salt2 Fit)
    - __Dataflow job:__ [`production-ztf-ps-exgal-salt2`](https://console.cloud.google.com/dataflow/jobs?project=ardent-cycling-243415)
    - __Listens to__ PS topic: [`ztf_alerts`](https://console.cloud.google.com/cloudpubsub/topic/detail/ztf_alerts?project=ardent-cycling-243415)
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
1. Setup and configure a new Google Cloud Platform (GCP) project.
    - [Instructions in our current docs](https://pitt-broker.readthedocs.io/en/latest/installation_setup/installation.html). We would need to follow pieces of the "Installation" and "Defining Environmental Variables" sections. Our project is already setup, so leaving out most of the details for now.

2. Install GCP tools on your machine:
    - [Google Cloud SDK](https://cloud.google.com/sdk/docs/install): Follow the instructions at the link. (This installs `gcloud`, `gsutil` and `bq` command line tools). I use a minimum version of Google Cloud SDK 323.0.0.
    - [Cloud Client Libraries for Python](https://cloud.google.com/python/docs/reference): Each service requires a different library; the ones we need are (I hope) all listed in the `requirements.txt` in this directory. Install them with (e.g., ) `pip install -r requirements.txt`.

3. Follow instructions in [broker/README.md](broker/README.md) to complete the setup.
<!-- fe Setup the Broker -->

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
