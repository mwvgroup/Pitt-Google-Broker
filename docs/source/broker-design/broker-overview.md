# Broker Overview

- [Broker Components](#broker-components)
    - [Details and Name Stubs](#details-and-name-stubs)
- [Broker Files](#broker-files)
- [`broker_utils` Package](#broker_utils-package)

---

## Broker Components

The __consumer__ (1, see list below) ingests a survey's Kafka stream and republishes it as a Pub/Sub stream.
The __data storage__ (2 and 3) and __science processing__ (4) components subscribe to the consumer's Pub/Sub stream. These components store their output data in Cloud Storage and/or BigQuery, and publish to dedicated Pub/Sub topics.
The __night conductor__ (5) orchestrates the broker, starting up resources and jobs at night and shutting them down in the morning.

To view the resources, see [View and Access Resources](../run-a-broker-instance/view-resources.md).

### Details and Name Stubs

Resource name stubs are given below in brackets [].
For a given broker instance, the actual resource names will have the survey keyword prepended, and the testid keyword appended.
The character `-` separates the stub from the keywords (unless it is restricted by GCP naming rules, in which case `_` is used).
For example, a broker instance set up with `survey=ztf` and `testid=mytestid` will have a consumer VM named `ztf-consumer-mytestid`.
See [Broker Instance Keywords](broker-instance-keywords.md) for details.
Note that Cloud Storage buckets also have the project ID prepended, for uniqueness across GCP.

1. __Consumer__ (Kafka -> Pub/Sub)
    - __Compute Engine VM__  [`consumer`]
        - __Runs__  the Kafka plugin [`CloudPubSubConnector`](https://github.com/GoogleCloudPlatform/pubsub/tree/master/kafka-connector)
        - __Publishes to__ Pub/Sub topic  [`alerts`]

2. __Avro File Storage__ (alert -> fix schema if needed -> Cloud Storage bucket)
    - __Cloud Function__ [`upload_bytes_to_bucket`]
        - __Listens to__ PS topic [`alerts`]
        - __Stores in__ GCS bucket [`alert_avros`]
        - __GCS bucket triggers__ Pub/Sub topic [`alert_avros`]

3. __BigQuery Database Storage__ (alert -> BigQuery)
    - __Dataflow job__ [`bq-sink`]
        - __Listens to__ PS topic [`alerts`]
        - __Stores in__ BQ dataset [`alerts`] in tables [`alerts`] and [`DIASource`]

4. __Data Processing Pipeline__ (alert -> {filters, fitters, classifiers} -> {Cloud Storage, BigQuery, Pub/Sub})
    - __Dataflow job__ [`value-added`]
        - __Listens to__ PS topic [`alerts`]
        - __Stores in__ BQ dataset [`alerts`] in table [`salt2`] (Salt2 fit params)
        - __Stores in__ GCS bucket [`sncosmo`] (lightcurve + Salt2 fit, png)
        - __Publishes to__ PS topics
            - [`alerts_pure`] (alerts passing the purity filter)
            - [`exgalac_trans`] (alerts passing extragalactic transient filter)
            - [`salt2`] (Salt2 fit params)

5. __Night Conductor__ (orchestrates GCP resources and jobs to run the broker each night)
    - __Compute Engine VM__  [`night-conductor`]
        - __Auto-Scheduled with__ (Cloud Scheduler -> Pub/Sub -> Cloud Function -> start VM):
            - Cloud Scheduler cron jobs [`cue_night_conductor_START`] and [`cue_night_conductor_END`]
            - Pub/Sub topic [`cue_night_conductor`]
            - Cloud Function [`cue_night_conductor`]
        - Broker's __response to the auto-scheduler's cue__ is checked by:
            - Cloud Function [`check_cue_response`]

---

## Broker Files

All scripts and config files used by the broker are stored in the Cloud Storage bucket [`broker_files`].
Fresh copies are downloaded/accessed prior to use each night.
This is mostly handled by the VMs (`night-conductor` and `consumer`), but the `broker_utils` package also uses this bucket (e.g., for schema maps).
This allows us to update most components of the broker by simply replacing the relevant files in the bucket, which is particularly useful for development and testing.

See [View and Access Resources](../run-a-broker-instance/view-resources.md) to find the `broker_files` bucket.

---

## `broker_utils` Package

The `broker_utils` Python package contains tools used throughout the broker, and tools useful for broker development and testing.
Of particular note is the `schema_maps` module, which components use to load the schema map stored in the Cloud Storage bucket `broker_files`.

To install:

`pip install pgb-broker-utils`

To import:

`import broker_utils`

Includes the following modules:
1) `beam_transforms`: custom transforms used in Beam jobs
2) `consumer_simulator`: tool to pull alerts from a Pub/Sub "reservoir" and publish them to the `alerts` topic
3) `data_utils`: generally useful functions for dealing with the data (`alert_avro_to_dict()`, `mag_to_flux()`, etc.)
4) `gcp_utils`: common interactions with GCP (download a file from Cloud Storage, load a row to BigQuery)
5) `schema_maps`: retrieve a schema map from Cloud Storage, used to translate field names of a particular survey into generic names used in the broker
