Software Overview
========================

-  `Broker Components`_

   -  `Details and Name Stubs`_

-  `Broker Files`_

--------------

Broker Components
-----------------

The **consumer** (1, see list below) ingests a survey's Kafka stream and
republishes it as a Pub/Sub stream.

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
