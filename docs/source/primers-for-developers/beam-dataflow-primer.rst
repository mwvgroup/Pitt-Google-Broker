Apache Beam + Google Dataflow
=============================

-  `General Links <#general-links>`__
-  `What are Apache Beam and Google Dataflow? (the very
   basics) <#what-are-apache-beam-and-google-dataflow>`__
-  `Apache Beam <#apache-beam>`__

   -  ```Pipeline`` <#pipeline>`__
   -  ```PCollection`` <#pcollection>`__
   -  ```PTransform`` <#ptransform>`__

      -  ```Filter`` <#filter>`__
      -  ```ParDo`` <#pardo>`__

         -  `Additional outputs <#additional-outputs>`__

      -  `Composite transforms <#composite-transforms>`__

-  `Dataflow <#dataflow>`__

   -  `Setting the ``DataflowRunner`` and its
      configurations <#setting-the-dataflowrunner-and-its-configurations>`__
   -  `Monitoring Interface <#monitoring-interface>`__
   -  `Error and exception handling <#error-and-exception-handling>`__

***Note*: References in [brackets] indicate PGB-specific examples of the
indicated files/functions/etc. Most of these can be found in the value
added Beam job at code path broker/beam/value\_added/value\_added.py or
in the associated README at broker/beam/README.md.**

What are Apache Beam and Google Dataflow?
-----------------------------------------

.. raw:: html

   <!-- fs -->

We use the `**Apache Beam** <https://beam.apache.org/>`__ Python SDK
(`v2.25 docs <https://beam.apache.org/releases/pydoc/2.25.0/>`__) to run
data processing and storage pipelines. The `Apache Beam
Overview/Tutorial <https://beam.apache.org/documentation/programming-guide/>`__
is very good.

Apache Beam pipelines can be run in a variety of environments;
environment-specific "**runners**\ " handle the pipeline execution. We
use the
```DataflowRunner`` <https://beam.apache.org/documentation/runners/dataflow/>`__
to execute our pipelines in the Google Cloud using their
`**Dataflow** <https://cloud.google.com/dataflow>`__ service (see also
`Deploying a
pipeline <https://cloud.google.com/dataflow/docs/guides/deploying-a-pipeline>`__).
You can also use
```DirectRunner`` <https://beam.apache.org/documentation/runners/direct/>`__
to execute the pipeline on a local machine (useful for testing).

Install the Beam Python SDK (including the Dataflow runner) with:
``pip install apache-beam[gcp]``

Dataflow
--------

.. raw:: html

   <!-- fs -->

`Dataflow <https://cloud.google.com/dataflow>`__ is a Google service
that runs Apache Beam pipelines on the Google Cloud Platform (GCP).
`Deploying a
pipeline <https://cloud.google.com/dataflow/docs/guides/deploying-a-pipeline>`__
is a good place to start.

Dataflow handles the provisioning and management of all GCP resources
(e.g., Compute Engine virtual machines or "workers"), and
`autoscales <https://cloud.google.com/dataflow/docs/guides/deploying-a-pipeline#autoscaling>`__
resources based on the (streaming) pipeline's current backlog and the
workers' CPU usage over the last couple of minutes.

Setting the ``DataflowRunner`` and its configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We tell the Beam pipeline to run on Dataflow by setting it as the
"runner". The runner, and its configuration options, are set when
creating the Beam ``Pipeline`` object. We pass them in as command line
arguments when starting the job. see the README at code path
broker/beam/README.md. - ``--runner=DataflowRunner`` runs the job in the
Google Cloud via Dataflow - See `Pipeline options for the Cloud Dataflow
Runner <https://beam.apache.org/documentation/runners/dataflow/#pipeline-options>`__
for a complete list of Dataflow runner configuration options.

Monitoring Interface
~~~~~~~~~~~~~~~~~~~~

Dataflow also provides us with a nice `monitoring
interface <https://cloud.google.com/dataflow/docs/guides/using-monitoring-intf>`__
[see
`here <https://console.cloud.google.com/dataflow/jobs/us-central1/2020-12-29_19_40_47-16278669788044201622?pageState=%28%22dfTime%22:%28%22s%22:%222020-12-30T14:04:49.951Z%22,%22e%22:%222020-12-30T20:04:49.951Z%22%29%29&project=ardent-cycling-243415>`__
for the job in production at the time of this writing]. There we can
see: - A graphical representation of pipelines. - Details about the
job's status and execution. - Errors, warnings, and additional
diagnostics. Links to the complete logs. - Monitoring charts with
job-level and step-level metrics.

`Error and exception handling <https://cloud.google.com/dataflow/docs/guides/deploying-a-pipeline#error-and-exception-handling>`__
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Quoted directly from the link, with emphasis added:

"Your pipeline may throw exceptions while processing data. Some of these
errors are transient (e.g., temporary difficulty accessing an external
service), but some are permanent, such as errors caused by corrupt or
unparseable input data, or null pointers during computation.

**Dataflow processes elements in arbitrary bundles, and retries the
complete bundle when an error is thrown for any element in that
bundle.** When running in batch mode, bundles including a failing item
are retried 4 times. The pipeline will fail completely when a single
bundle has failed 4 times. **When running in streaming mode, a bundle
including a failing item will be retried indefinitely, which may cause
your pipeline to permanently stall.**"

.. raw:: html

   <!-- fe Dataflow -->


