# `pgb_utils`: Tools for interacting with Pitt-Google Broker

See [Pitt-Google-Tutorial-Code-Samples.ipynb](https://colab.research.google.com/github/broker-workshop/tutorials/blob/main/Pitt-Google/Pitt-Google-Tutorial-Code-Samples.ipynb) for an intro on using this package to access the data.

`pgb_utils` is a collection of helper functions to facilitate interaction with Pitt-Google Broker data. The tutorial will demonstrate its use. The package is essentially a set of:

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
