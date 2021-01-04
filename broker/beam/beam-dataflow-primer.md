# Apache Beam + Google Dataflow Primer

- [General Links](#general-links)
- [What are Apache Beam and Google Dataflow? (the very basics)](#what-are-apache-beam-and-google-dataflow)
- [Apache Beam](#apache-beam)
    - [`Pipeline`](#pipeline)
    - [`PCollection`](#pcollection)
    - [`PTransform`](#ptransform)
        - [`Filter`](#filter)
        - [`ParDo`](#pardo)  
- [Dataflow](#dataflow)
    - [Setting the `DataflowRunner` and its configurations](#setting-the-dataflowrunner-and-its-configurations)
    - [Monitoring Interface](#monitoring-interface)
    - [Error and exception handling](#error-and-exception-handling)


_Note_: References in [brackets] indicate PGB-specific examples of the indicated files/functions/etc. Most of these are defined in [[`ztf-proc.py`]](./ztf-proc.py) or [[`README.md`]](./README.md).


---
## General Links
- Apache Beam
    - [__Apache Beam Overview/Tutorial__](https://beam.apache.org/documentation/programming-guide/) (__Extremely useful!__)
    - [Apache Beam SDK (2.25.0) for Python](https://beam.apache.org/releases/pydoc/2.25.0/)
- Dataflow
    - [Dataflow console](https://console.cloud.google.com/dataflow/jobs?project=ardent-cycling-243415)
    - [Deploying a pipeline](https://cloud.google.com/dataflow/docs/guides/deploying-a-pipeline)
    - Apache Beam [`DataflowRunner`](https://beam.apache.org/documentation/runners/dataflow/)

---
## What are Apache Beam and Google Dataflow?
<!-- fs -->
We use the [__Apache Beam__](https://beam.apache.org/) Python SDK ([v2.25 docs](https://beam.apache.org/releases/pydoc/2.25.0/)) to run data processing and storage pipelines.
The [Apache Beam Overview/Tutorial](https://beam.apache.org/documentation/programming-guide/) is very good.

Apache Beam pipelines can be run in a variety of environments; environment-specific "__runners__" handle the pipeline execution.
We use the [`DataflowRunner`](https://beam.apache.org/documentation/runners/dataflow/) to execute our pipelines in the Google Cloud using their [__Dataflow__](https://cloud.google.com/dataflow) service
(see also [Deploying a pipeline](https://cloud.google.com/dataflow/docs/guides/deploying-a-pipeline)).
You can also use [`DirectRunner`](https://beam.apache.org/documentation/runners/direct/) to execute the pipeline on a local machine (useful for testing).
<!-- fe What are Apache Beam and Google Dataflow? -->

Install the Beam Python SDK (including the Dataflow runner) with:
`pip install apache-beam[gcp]`

---
## Apache Beam
<!-- fs -->
Apache Beam runs data processing pipelines.
Batch and streaming jobs are both supported under a single programming model.
Which type of job is run depends only on the initial data source input to the pipeline (and we must set the pipeline's `streaming` option), the rest of the programming logic and syntax is agnostic.

Here we outline the essential concepts needed to program with Beam.
Much of it is quoted directly from [__Apache Beam Overview/Tutorial__](https://beam.apache.org/documentation/programming-guide/).

### [`Pipeline`](https://beam.apache.org/documentation/programming-guide/#creating-a-pipeline)
- The `Pipeline` abstraction encapsulates all the data and steps in the data processing task.
- The "driver program" [`ztf-proc.py`] creates a `Pipeline` object [`pipeline`, within `run()`] and uses it as the basis for creating the pipeline’s data (`PCollection`s) and its operations (`PTransform`s).
- The general form of a step in the pipeline is (here, brackets indicate general Beam objects, not PGB-specific objects):
    - `[Output PCollection] = [Input PCollection] | [Transform]`

### [`PCollection`](https://beam.apache.org/documentation/programming-guide/#pcollections)
- A `PCollection` represents a distributed data set that the Beam pipeline operates on.
- `PCollection`s are the inputs and outputs for each step in the pipeline.
    - The exception is the first step of the pipeline, where we must pass the `Pipeline` object itself to a `Read` transform to create the initial collection [`PSin`].
- The elements of a `PCollection` may be of any type, but must all be of the same type.
_Our current pipeline uses dictionaries for the alert data and most of its child/downstream collections._
- A `PCollection` is immutable. A Beam Transform might process each element of a PCollection and generate new pipeline data (as a new `PCollection`), _but it does not consume or modify the original input collection_.

### [`PTransform`](https://beam.apache.org/documentation/programming-guide/#transforms)
- A `PTransform` represents a data processing operation, or a step, in the pipeline. I/O (read/write) operations are special cases of `PTransform`s.
- Every `PTransform` takes one or more `PCollection` objects as input, performs some processing with/on the elements of that `PCollection`, and produces zero or more output `PCollection` objects.
- To invoke a transform, we apply it (using the pipe operator `|`) to the input `PCollection`.
This takes the general form (here, brackets indicate general Beam objects, not PGB-specific objects):
    - `[Output PCollection] = [Input PCollection] | [Transform]`
    - We can decorate the transform (using the `>>` operator) with a name that will show up in Dataflow:
        - `"My Transform Name" >> [Transform]`
    - We can also chain transforms together without explicitly naming the output collections.
        - `[Final Output PCollection] = ([Initial Input PCollection] | [1st Transform] | [2nd Transform])`
- How we apply the pipeline’s transforms to its various collections determines the structure of our pipeline.
    - The best way to think of the pipeline is as a directed acyclic graph, where `PTransform` nodes are subroutines that accept `PCollection` nodes as inputs and emit `PCollection` nodes as outputs.
    - Dataflow provides a "job graph" visualization of the pipeline. See [here](https://console.cloud.google.com/dataflow/jobs/us-central1/2020-12-29_19_40_47-16278669788044201622?pageState=%28%22dfTime%22:%28%22s%22:%222020-12-30T14:04:49.951Z%22,%22e%22:%222020-12-30T20:04:49.951Z%22%29%29&project=ardent-cycling-243415) for the job graph in production [defined in `ztf-beam.py`] at the time of this writing (the interface is described in the [Dataflow](#dataflow) section below).
- Built-in transforms (complete lists):
    - [Built-in I/O Transforms](https://beam.apache.org/documentation/io/built-in/) (also see [Pipeline I/O Overview](https://beam.apache.org/documentation/programming-guide/#pipeline-io))
    - [Python transform catalog](https://beam.apache.org/documentation/transforms/python/overview/)

__Two important transforms in our pipeline are:__

#### [`Filter`](https://beam.apache.org/documentation/transforms/python/elementwise/filter/)
Given a predicate, filter out all elements that don't satisfy the predicate.
1. We write a function ([`is_extragalactic_transient`]) which operates on a single element of the input collection and returns `True` if the element meets our condition(s) and `False` otherwise.
2. We apply our function as a filter on the pipeline by passing it to the `Filter` transform:
    - [`ExgalTrans = alertDicts | apache_beam.Filter(is_extragalactic_transient)`]

#### [`ParDo`](https://beam.apache.org/documentation/programming-guide/#pardo)
Generic parallel processing.
1. We write a function which:
    - performs some data processing (e.g., fit the data using Salt2) on a single element of the input collection, and
    - returns a list containing zero or more elements, each of which will become an element of the output collection.
2. We name that function `process` and wrap it in an arbitrarily-named class ([`fitSalt2`]).
3. We apply our function to each element of the step's input `PCollection` by passing the class to the `ParDo` transform:
    - [`salt2Dicts = ExgalTrans | apache_beam.ParDo(fitSalt2())`].

<!-- fe Apache Beam -->

---
## Dataflow
<!-- fs -->
[Dataflow](https://cloud.google.com/dataflow) is a Google service that runs Apache Beam pipelines on the Google Cloud Platform (GCP). [Deploying a pipeline](https://cloud.google.com/dataflow/docs/guides/deploying-a-pipeline) is a good place to start.

Dataflow handles the provisioning and management of all GCP resources (e.g., Compute Engine virtual machines or "workers"), and [autoscales](https://cloud.google.com/dataflow/docs/guides/deploying-a-pipeline#autoscaling) resources based on the (streaming) pipeline's current backlog and the workers' CPU usage over the last couple of minutes.

### Setting the `DataflowRunner` and its configurations
We tell the Beam pipeline to run on Dataflow by setting it as the "runner".
The runner, and its configuration options, are set when creating the Beam `Pipeline` object.
We pass them in as command line arguments when starting the job.
[see [`README.md`](./README.md)].
- `--runner=DataflowRunner` runs the job in the Google Cloud via Dataflow
- See [Pipeline options for the Cloud Dataflow Runner](https://beam.apache.org/documentation/runners/dataflow/#pipeline-options) for a complete list of Dataflow runner configuration options.

### Monitoring Interface
Dataflow also provides us with a nice [monitoring interface](https://cloud.google.com/dataflow/docs/guides/using-monitoring-intf) [see [here](https://console.cloud.google.com/dataflow/jobs/us-central1/2020-12-29_19_40_47-16278669788044201622?pageState=%28%22dfTime%22:%28%22s%22:%222020-12-30T14:04:49.951Z%22,%22e%22:%222020-12-30T20:04:49.951Z%22%29%29&project=ardent-cycling-243415) for the job in production at the time of this writing]. There we can see:
- A graphical representation of pipelines.
- Details about the job's status and execution.
- Errors, warnings, and additional diagnostics. Links to the complete logs.
- Monitoring charts with job-level and step-level metrics.

### [Error and exception handling](https://cloud.google.com/dataflow/docs/guides/deploying-a-pipeline#error-and-exception-handling)
Quoted directly from the link, with emphasis added:

"Your pipeline may throw exceptions while processing data. Some of these errors are transient (e.g., temporary difficulty accessing an external service), but some are permanent, such as errors caused by corrupt or unparseable input data, or null pointers during computation.

__Dataflow processes elements in arbitrary bundles, and retries the complete bundle when an error is thrown for any element in that bundle.__ When running in batch mode, bundles including a failing item are retried 4 times. The pipeline will fail completely when a single bundle has failed 4 times. __When running in streaming mode, a bundle including a failing item will be retried indefinitely, which may cause your pipeline to permanently stall.__"

<!-- fe Dataflow -->
