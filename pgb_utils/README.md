# Query, download, and process the data

[Pitt-Google-Tutorial-Code-Samples.ipynb](tutorials/Pitt-Google-Tutorial-Code-Samples.ipynb)

All data is public and is hosted in the [Google Cloud](https://cloud.google.com/).
It can be accessed using Google's [Cloud SDK](https://cloud.google.com/sdk) in many languages, including Python and from the command-line.
In addition, Pitt-Google Broker offers the Python package `pgb_utils` which contains wrappers of Cloud SDK methods for some common use cases, and other helper functions.
We view this package as a collection of examples demonstrating the use of the underlying methods.
The Cloud SDK is well developed and documented, and we intend for `pgb_utils` to be an entry point to learning the methods.
You are encouraged to view its source code and adapt/extend it for your specific use cases.
Please open an Issue on GitHub or contact troy.raen@pitt.edu if you run into problems.


## `pgb_utils`

`pgb_utils` is a collection of wrappers and helper functions to facilitate interaction with data. We view it as a set of examples for using the Cloud SDK to access and process the data. The tutorial will demonstrate its use. The package is essentially a set of:

1. Convience wrappers for the [Google Cloud Python SDK](https://cloud.google.com/python/docs/reference)
2. Helper functions for ZTF data decoding and plotting, provided by ZTF (see [Filtering_alerts.ipynb](https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb))
3. Helper functions for running [Apache Beam](https://beam.apache.org/) pipelines

You are encouraged to look at and alter the source code to learn how to use the underlying methods yourself.

Modules and their functionality include:

- `pgb_utils.beam`
    - helper functions for running Apache Beam data pipelines

- `pgb_utils.bigquery`
    - view dataset, table, and schema information
    - query: lightcurves
    - query: cone search
    - cast query results to a `pandas.DataFrame` or `json` formatted string.

- `pgb_utils.figures`
    - plot lightcurves
    - plot cutouts

- `pgb_utils.utils`
    - general utilities such as data type casting
