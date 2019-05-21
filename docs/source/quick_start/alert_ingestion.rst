Ingesting Data to GCP
=====================

Alert ingestion is handled by the ``alert_acquisition`` and ``data_upload``
modules. The following provides an example of acquiring and then uploading
data into BigQuery.

.. important:: Data can be ingested into BigQuery
  through multiple avenues (see `here`_ for an overview of options and
  pricing models).

Stream Ingestion
----------------

.. code:: python

   from broker import alert_ingestion

   # To ingest alerts via the BigQuery streaming interface
   alert_ingestion.stream_ingest_alerts()

   # To ingest 15 alerts at a time through the streaming interface
   # (The default number of alerts is 10)
   alert_ingestion.stream_ingest_alerts(15)

   # The same principles apply for the batch upload interface
   alert_ingestion.batch_ingest_alerts(15)

.. _BigQuery: https://cloud.google.com/bigquery/
.. _here: https://cloud.google.com/bigquery/docs/loading-data
