Ingesting Data to GCP
=====================

The ``alert_ingestion`` module handles the insertion of ZTF alert data
into `BigQuery`_. Eventually this module will ingest data directly from the
live ZTF stream, but for now, it relies on the ZTF Alert Archive
described in the previous section. Data can be ingested into BigQuery
through multiple avenues (see `here`_ for an overview of options and
pricing models) but the ``alert_ingestion`` module only provides
options to *stream* or *bulk insert* methods.

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
