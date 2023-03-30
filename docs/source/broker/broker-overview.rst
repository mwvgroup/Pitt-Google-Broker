Software Overview
========================

-  `Broker Components`_

   -  `Details and Name Stubs`_

-  `Broker Files`_
-  `broker_utils Python package`_

--------------

Broker Components
-----------------

The **consumer** (1, see list below) ingests a survey's Kafka stream and
republishes it as a Pub/Sub stream. The **data storage** (2 and 3) and
**science processing** () components subscribe to the consumer's
Pub/Sub stream. (The SuperNNova classifier (4) is implemented separately.)
These components store their output data in Cloud
Storage and/or BigQuery, and publish to dedicated Pub/Sub topics. The
**night conductor** (5) processes Pub/Sub counter subscriptions to collect metadata.
**Uptime checks** (6) check that VMs start/stop as expected.

To view the resources, see :doc:`../broker/run-a-broker-instance/view-resources`.

Details and Name Stubs
~~~~~~~~~~~~~~~~~~~~~~

Resource name stubs are given below in brackets []. For a given broker
instance, the actual resource names will have the survey keyword
prepended, and the testid keyword appended. The character "-"
separates the stub from the keywords (unless it is restricted by GCP
naming rules, in which case "_" is used). For example, a broker
instance set up with ``survey=ztf`` and ``testid=mytestid`` will have a
consumer VM named `ztf-consumer-mytestid`. See :doc:`broker-instance-keywords` for details. Note that Cloud
Storage buckets also have the project ID prepended, for uniqueness
across GCP.

1. **Consumer** (Kafka -> Pub/Sub)

   -  Compute Engine VM [`consumer`]

      -  Runs the Kafka plugin
         `CloudPubSubConnector <https://github.com/GoogleCloudPlatform/pubsub/tree/master/kafka-connector>`__
      -  Publishes to Pub/Sub topic [`alerts`]

2. **Avro File Storage** (alert -> fix schema if needed -> Cloud Storage
   bucket)

   -  Cloud Function [`upload_bytes_to_bucket`]

      -  Listens to PS topic [`alerts`]
      -  Stores in GCS bucket [`alert_avros`]
      -  GCS bucket triggers Pub/Sub topic [`alert_avros`]

3. **BigQuery Database Storage** (alert -> BigQuery)

   -  Cloud Function [`store_in_BigQuery`]

      -  Listens to PS topic [`alerts`]
      -  Stores in BQ dataset [`alerts`] in tables
         [`alerts`] and [`DIASource`]
      -  Publishes to Pub/Sub topic [`BigQuery`]

4. **SuperNNova Classifier** (extragalactic transient alert -> SuperNNova ->
   {BigQuery, Pub/Sub})

      -  Cloud Function [`classify_with_SuperNNova`]

         -  Listens to PS topic [`exgalac_trans_cf`]

            - this stream is emitted by the Cloud Function [`filter_exgalac_trans`],
              which implements the same extragalactic transient filter as the
              Dataflow job, for comparison.

         -  Stores in BigQuery table [`SuperNNova`]
         -  Publishes to PS topic [`SuperNNova`]

5. **Night Conductor** (collects metadata)

   -  Compute Engine VM [`night-conductor`] running a python script

6. **Uptime checks** (check that VMs start/stop as expected)

   -  Cloud Function [`cue_night_conductor`]

      -  Listens to PS topic [`cue_night_conductor`] which is published by the
         Cloud Scheduler cron jobs [`cue_night_conductor_START`
         and `cue_night_conductor_END`]

--------------

Broker Files
------------

All scripts and config files used by the broker are stored in the Cloud
Storage bucket [`broker_files`]. Fresh copies are
downloaded/accessed prior to use each night. This is mostly accessed by
the VMs [`night-conductor` and `consumer`], but the broker_utils
package also uses this bucket. This allows us to
update most components of the broker by simply replacing the relevant
files in the bucket, which is particularly useful for development and
testing.

See :doc:`../broker/run-a-broker-instance/view-resources` to find the
[`broker_files`] bucket.

--------------

broker_utils Python package
-----------------------------

The broker_utils Python package contains tools used throughout the
broker, and tools useful for broker development and testing. Of
particular note is the schema_maps module, which components use to
load the schema map stored in the Cloud Storage bucket [`broker_files`].

To install:

``pip install pgb-broker-utils``

To import:

``import broker_utils``

Includes the following modules:

1)  `beam_transforms`: custom transforms used in Beam jobs
2)  `consumer_simulator`: tool to pull alerts from a
    Pub/Sub "reservoir" and publish them to the `alerts` topic
3)  `data_utils`: generally useful functions for dealing with the
    data (`alert_avro_to_dict()`, `mag_to_flux()`, etc.)
4)  `gcp_utils`: common interactions with GCP (download a file from Cloud
    Storage, load a row to BigQuery)
5)  `schema_maps`: retrieve a schema
    map from Cloud Storage, used to translate field names of a particular
    survey into generic names used in the broker
