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

Pipeline Architecture and Resource Names
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Resource name stubs are given below in brackets []. For a given broker
instance, the actual resource names will have the survey keyword
prepended, and the testid keyword appended (not shown in the list below). The character "-"
separates the stub from the keywords (unless it is restricted by GCP
naming rules, in which case "_" is used). For example, a broker
instance set up with ``survey=ztf`` and ``testid=mytestid`` will have a
consumer VM named `ztf-consumer-mytestid`. See :doc:`broker-instance-keywords` for details.

A `versiontag` representing the Avro-schema version of the incoming alerts is appended to names of
the BigQuery table and Cloud Storage bucket housing the raw alert data.
If the schema version is "3.3", the versiontag will be "v3_3".
The reason for the "_" is that the naming rules of some GCP resources prohibit the use of ".".

Cloud Storage bucket names must be unique across GCP, so the project ID is prepended
(before `survey`; not shown below).

1. **Consumer** (Kafka -> Pub/Sub)

   -  Compute Engine VM [`consumer`]

      -  Runs the Kafka plugin
         `CloudPubSubConnector <https://github.com/GoogleCloudPlatform/pubsub/tree/master/kafka-connector>`__.
         This passes the bytes from the Kafka message packet straight through to a Pub/Sub message,
         and attaches the Kafka metadata (e.g., topic, partition, offset, timestamp) as Pub/Sub
         message attributes.
         It does not open the message packet or transform the data in any way.
      -  Publishes to Pub/Sub topic [`alerts_raw`]

2. **Avro File Storage** (alert -> fix schema if needed -> Cloud Storage
   bucket)

   -  Cloud Function [`upload_bytes_to_bucket`]

      -  Listens to PS topic [`alerts_raw`]
      -  Stores in GCS bucket [`alerts_{versiontag}`]
      -  Publishes to Pub/Sub topic [`alerts`]

         - This module effectively de-duplicates the Consumer's stream for the rest of the
           pipeline. It does this by first attempting to upload to the GCS bucket using a
           keyword arg that throws an error if an object with the same name already exists
           in the bucket. Alerts are then published to the [`alerts`] topic only if that error
           is not encountered.

   -  GCS bucket triggers Pub/Sub topic [`alert_avros`]

      - This is a light-weight notification stream announcing that a new object (Avro file) is
        in the bucket. The messages include the object metadata but not the alert packet/data itself.

3. **BigQuery Database Storage** (alert -> BigQuery)

   -  Cloud Function [`store_in_BigQuery`]

      -  Listens to PS topic [`alerts`]
      -  Stores in BQ dataset [`survey`] in tables
         [`alerts_{versiontag}`] and [`DIASource`]
      -  Publishes to Pub/Sub topic [`BigQuery`]

4. **Lite** (alert -> semantic compression -> Pub/Sub)

      -  Cloud Function [`lite`]

         -  Listens to PS topic [`alerts`]
         -  Performs semantic compression producing a more lite-weight stream which contains
            the subset of original data deemed "most useful". The field names in the resulting
            "lite" alert packet are also transformed to a standard naming scheme,
            allowing the downstream modules to be more survey-agnostic.
         -  Publishes to PS topic [`lite`]

4. **Tag** (lite alert -> basic categorizations -> {BigQuery, Pub/Sub})

      -  Cloud Function [`tag`]

         -  Listens to PS topic [`lite`]
         -  Produces basic categorizations such as "is pure" and
            "is likely extragalactic transient". These are attached as message attributes
            to the outgoing Pub/Sub message so that they are easily accessible and can be
            used to filter the alert stream without opening the data packet.
         -  Stores in BigQuery tables [`classifications`] and [`tags`]
         -  Publishes to PS topic [`tagged`]

4. **SuperNNova Classifier** (lite alert -> SuperNNova classifier -> {BigQuery, Pub/Sub})

      -  Cloud Function [`classify_with_SuperNNova`]

         -  Listens to PS topic [`tagged`]
         -  Produces a Type Ia supernova classification probability using
            `SuperNNova <https://supernnova.readthedocs.io/en/latest/>`__
         -  Stores in BigQuery tables [`classifications`] and [`SuperNNova`]
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
