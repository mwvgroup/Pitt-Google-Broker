Ingesting Data to GCP
=====================

Alert ingestion is handled by the ``alert_acquisition`` and ``data_upload``
modules. The following provides an example of acquiring and then uploading
data into BigQuery.

.. important:: Data can be ingested into BigQuery through multiple avenues.
   See `here`_ for an overview of options and pricing models.

Stream Ingestion
----------------

.. code:: python

    from broker import data_upload
    from broker.alert_acquisition import ztf

    # Get a maximum of 10 alerts from ZTF
    # Returns a list of dictionaries
    alert_list = ztf.get_alerts(10)

    # Convert data into DataFrames with the same data model as the GCP backend
    # The ZTF backend has two relevant tables here: "alert" and "candidate"
    alert_df, candidate_df = ztf.map_to_schema(map_to_schema)

    # An example of a batch upload
    data_upload.batch_ingest(alert_df, 'ztf_alerts', 'alert')

    # An example of a stream upload
    data_upload.stream_ingest(candidate_df, 'ztf_alerts', 'candidate')


.. _BigQuery: https://cloud.google.com/bigquery/
.. _here: https://cloud.google.com/bigquery/docs/loading-data
