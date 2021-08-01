Apache Beam + Google Dataflow Primer
====================================

-  `General Links`_
-  `What are Apache Beam and Google Dataflow?`_  (the very basics)
-  `Apache Beam`_

   -  `Pipeline`_
   -  `PCollection`_
   -  `PTransform`_

      -  `Filter`_
      -  `ParDo`_

         -  `Additional outputs`_

      -  `Composite transforms`_

-  `Dataflow`_

   -  `Setting the DataflowRunner and its configurations`_
   -  `Monitoring Interface`_
   -  `Error and exception handling`_

Note: References in [brackets] indicate PGB-specific examples of the
indicated files/functions/etc. Most of these can be found at code path
broker/beam/value_added/value_added.py or
broker/beam/README.md.

--------------

General Links
-------------

-  Apache Beam

   -  **`Apache Beam
      Overview/Tutorial <https://beam.apache.org/documentation/programming-guide/>`__
      Extremely useful!**
   -  `Apache Beam SDK (2.25.0) for
      Python <https://beam.apache.org/releases/pydoc/2.25.0/>`__

-  Dataflow

   -  `Deploying a
      pipeline <https://cloud.google.com/dataflow/docs/guides/deploying-a-pipeline>`__
   -  Apache Beam
      ```DataflowRunner`` <https://beam.apache.org/documentation/runners/dataflow/>`__

--------------

What are Apache Beam and Google Dataflow?
-----------------------------------------

We use the `Apache Beam <https://beam.apache.org/>`__ Python SDK
(`v2.25 docs <https://beam.apache.org/releases/pydoc/2.25.0/>`__) to run
data processing and storage pipelines. The `Apache Beam
Overview/Tutorial <https://beam.apache.org/documentation/programming-guide/>`__
is very good.

Apache Beam pipelines can be run in a variety of environments;
environment-specific "**runners**\ " handle the pipeline execution. We
use the
`DataflowRunner <https://beam.apache.org/documentation/runners/dataflow/>`__
to execute our pipelines in the Google Cloud using their
`Dataflow <https://cloud.google.com/dataflow>`__ service (see also
`Deploying a
pipeline <https://cloud.google.com/dataflow/docs/guides/deploying-a-pipeline>`__).
You can also use
`DirectRunner <https://beam.apache.org/documentation/runners/direct/>`__
to execute the pipeline on a local machine (useful for testing).

Install the Beam Python SDK (including the Dataflow runner) with:
``pip install apache-beam[gcp]``

--------------

Apache Beam
-----------

Apache Beam runs data processing pipelines. Batch and streaming jobs are
both supported under a single programming model. Which type of job is
run depends only on the initial data source input to the pipeline (and
we must set the pipeline's ``streaming`` option), the rest of the
programming logic and syntax is agnostic.

Here we outline the essential concepts needed to program with Beam.
*Much of it is quoted directly from `Apache Beam
Overview/Tutorial <https://beam.apache.org/documentation/programming-guide/>`__.*

``Pipeline``
~~~~~~~~~~~~~

`Programming guide: Create a pipeline <https://beam.apache.org/documentation/programming-guide/#creating-a-pipeline>`__

-  The ``Pipeline`` abstraction encapsulates all the data and steps in
   the data processing task.
-  The "driver program" [``value_added/value_added.py``\ ] creates a
   ``Pipeline`` object [``pipeline``, within ``run()``] and uses it as
   the basis for creating the pipeline’s data (``PCollection``\ s) and
   its operations (``PTransform``\ s).
-  The general form of a step in the pipeline is (here, brackets
   indicate general Beam objects, not PGB-specific objects):

   -  ``[Output PCollection] = [Input PCollection] | [Transform]``

``PCollection``
~~~~~~~~~~~~~~~~~

`Programming guide: PCollections <https://beam.apache.org/documentation/programming-guide/#pcollections>`__


-  A ``PCollection`` represents a distributed data set that the Beam
   pipeline operates on.
-  ``PCollection``\ s are the inputs and outputs for each step in the
   pipeline.

   -  The exception is the first step of the pipeline, where we must
      pass the ``Pipeline`` object itself to a ``Read`` transform to
      create the initial collection [``PSin``\ ].

-  The elements of a ``PCollection`` may be of any type, but must all be
   of the same type. *Our current pipeline uses dictionaries for the
   alert data and most of its child/downstream collections.*
-  A ``PCollection`` is immutable. A Beam Transform might process each
   element of a PCollection and generate new pipeline data (as a new
   ``PCollection``), *but it does not consume or modify the original
   input collection*.

``PTransform``
~~~~~~~~~~~~~~~~

`Programming guide: PTransform <https://beam.apache.org/documentation/programming-guide/#transforms>`__


-  A ``PTransform`` represents a data processing operation, or a step,
   in the pipeline. I/O (read/write) operations are special cases of
   ``PTransform``\ s.
-  Every ``PTransform`` takes one or more ``PCollection`` objects as
   input, performs some processing with/on the elements of that
   ``PCollection``, and produces zero or more output ``PCollection``
   objects.
-  To invoke a transform, we apply it (using the pipe operator ``|``) to
   the input ``PCollection``. This takes the general form (here,
   brackets indicate general Beam objects, not PGB-specific objects):

   -  ``[Output PCollection] = [Input PCollection] | [Transform]``
   -  We can decorate the transform (using the ``>>`` operator) with a
      name that will show up in Dataflow:

      -  ``"My Transform Name" >> [Transform]``

   -  We can also chain transforms together without explicitly naming
      the output collections.

      -  ``[Final Output PCollection] = ([Initial Input PCollection] | [1st Transform] | [2nd Transform])``

-  How we apply the pipeline’s transforms to its various collections
   determines the structure of our pipeline.

   -  The best way to think of the pipeline is as a directed acyclic
      graph, where ``PTransform`` nodes are subroutines that accept
      ``PCollection`` nodes as inputs and emit ``PCollection`` nodes as
      outputs.
   -  Dataflow provides a "job graph" visualization of the pipeline. See
      `here <https://console.cloud.google.com/dataflow/jobs/us-central1/2020-12-29_19_40_47-16278669788044201622?pageState=%28%22dfTime%22:%28%22s%22:%222020-12-30T14:04:49.951Z%22,%22e%22:%222020-12-30T20:04:49.951Z%22%29%29&project=ardent-cycling-243415>`__
      for the job graph in production [defined in ``ztf-beam.py``] at
      the time of this writing (the interface is described in the
      `Dataflow <#dataflow>`__ section below).

-  Built-in transforms (complete lists):

   -  `Built-in I/O
      Transforms <https://beam.apache.org/documentation/io/built-in/>`__
      (also see `Pipeline I/O
      Overview <https://beam.apache.org/documentation/programming-guide/#pipeline-io>`__)
   -  `Python transform
      catalog <https://beam.apache.org/documentation/transforms/python/overview/>`__

**Two important transforms in our pipeline are:**

``Filter``
^^^^^^^^^^^

`Programming guide: Filter <https://beam.apache.org/documentation/transforms/python/elementwise/filter/>`__


Given a predicate, filter out all elements that don't satisfy the
predicate.

1. We write a function ([``is_extragalactic_transient``\ ]) which
   operates on a single element of the input collection and returns
   ``True`` if the element meets our condition(s) and ``False``
   otherwise.
2. We apply our function as a filter on the pipeline by passing it to
   the ``Filter`` transform:

   -  [``ExgalTrans = alertDicts | apache_beam.Filter(is_extragalactic_transient)``\ ]

``ParDo``
^^^^^^^^^

`Programming guide: ParDo <https://beam.apache.org/documentation/programming-guide/#pardo>`__

See also:

-  `Transforms:
   ParDo <https://beam.apache.org/documentation/transforms/python/elementwise/pardo/>`__

Generic parallel processing.

1. We write a function which:

   -  performs some data processing (e.g., fit the data using Salt2) on
      a single element of the input collection, and
   -  returns a list containing zero or more elements, each of which
      will become an element of the output collection.

2. We name that function ``process`` and wrap it in an arbitrarily-named
   class [``fitSalt2``\ ] (subclass of ``DoFn``).
3. We apply our function to each element of the step's input
   ``PCollection`` by passing the class to the ``ParDo`` transform:

   -  [``salt2Dicts = ExgalTrans | apache_beam.ParDo(fitSalt2())``\ ].

Additional outputs
'''''''''''''''''''

`Programming guide: Additional outputs <https://beam.apache.org/documentation/programming-guide/#additional-outputs>`__

See also:

-  `Example:
   multiple\_output\_pardo.py <https://github.com/apache/beam/blob/master/sdks/python/apache_beam/examples/cookbook/multiple_output_pardo.py>`__

``ParDo`` (or the ``DoFn`` passed to it) can produce more than one
output PCollection. The main output should be returned as normal(\*),
additional outputs should be tagged using
``apache_beam.pvalue.TaggedOutput('tag',element)`` See the examples in
the links above, and [the ``FitSalt2`` (``DoFn``) class in
`beam\_helpers/salt2\_utils.py <beam_helpers/salt2_utils.py>`__].

(\*) We typically use ``return`` statements in our ``DoFn``\ s, but we
also have the option of using ``yield`` statements (making the ``DoFn``
a generator). However, to return *multiple outputs* we must use
``yield`` statements.

Composite transforms
^^^^^^^^^^^^^^^^^^^^^

`Programming guide: Composite transforms <https://beam.apache.org/documentation/programming-guide/#composite-transforms>`__

See also:

-  `Creating composite
   transforms <https://beam.apache.org/get-started/wordcount-example/#creating-composite-transforms>`__
-  Example in:
   `ptransform_fn <https://beam.apache.org/releases/pydoc/2.27.0/apache_beam.transforms.ptransform.html#apache_beam.transforms.ptransform.ptransform_fn>`__

To make the pipeline structure more clear and modular, we can group
multiple transforms into a single composite transform. We do this by
creating a subclass of the ``PTransform`` class and overriding the
``expand`` method to specify the actual processing logic. We can then
use this transform just as we would a built-in transform from the Beam
SDK. See the links above and [the ``Salt2`` composite transform at code path
broker/beam/value_added/value_added.py].

--------------

Dataflow
--------

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

Setting the DataflowRunner and its configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We tell the Beam pipeline to run on Dataflow by setting it as the
"runner". The runner, and its configuration options, are set when
creating the Beam ``Pipeline`` object. We pass them in as command line
arguments when starting the job.
[see the file at code path broker/beam/README.md].

-  ``--runner=DataflowRunner`` runs the job in the Google Cloud via
   Dataflow
-  See `Pipeline options for the Cloud Dataflow
   Runner <https://beam.apache.org/documentation/runners/dataflow/#pipeline-options>`__
   for a complete list of Dataflow runner configuration options.

Monitoring Interface
~~~~~~~~~~~~~~~~~~~~

Dataflow also provides us with a nice `monitoring
interface <https://cloud.google.com/dataflow/docs/guides/using-monitoring-intf>`__
[see
`here <https://console.cloud.google.com/dataflow/jobs/us-central1/2020-12-29_19_40_47-16278669788044201622?pageState=%28%22dfTime%22:%28%22s%22:%222020-12-30T14:04:49.951Z%22,%22e%22:%222020-12-30T20:04:49.951Z%22%29%29&project=ardent-cycling-243415>`__
for the job in production at the time of this writing]. There we can
see:

-  A graphical representation of pipelines.
-  Details about the job's status and execution.
-  Errors, warnings, and additional diagnostics. Links to the complete
   logs.
-  Monitoring charts with job-level and step-level metrics.

Error and exception handling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`GCP docs: Error and exception handling <https://cloud.google.com/dataflow/docs/guides/deploying-a-pipeline#error-and-exception-handling>`__

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
