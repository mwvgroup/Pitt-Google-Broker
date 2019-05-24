Ingesting Data to GCP
=====================

Alert ingestion is handled by the ``alert_acquisition`` and ``data_upload``
modules. This includes saving alert data to file and uploading data into
BigQuery.

To File / Bucket Storage
------------------------

The ``save_to_avro`` and ``upload_to_bucket`` functions handel file storage of
alert data:

.. code:: python

    from broker import data_upload
    from broker.alert_acquisition import ztf

    # Get a maximum of 10 alerts from ZTF
    # Returns a list of dictionaries
    alert_list = ztf.get_alerts(10)

    # Save alerts to a file
    data_upload.save_to_avro(alert_list, 'demo.avro', schemavsn='3.2')

    # Upload the file to GCP bucket storage
    data_upload.upload_to_bucket(
        bucket_name='my_bucket_name,
        source_path='demo.avro',
        destination_name='demo.avro')


To Big Query
------------

The ``data_upload`` module also supports uploading alert data to BigQuery by
either the stream or batch uploading interfaces.

.. important:: See `here`_ for an overview of options and pricing models.




    # An example of a batch upload
    data_upload.batch_ingest(alert_df, 'ztf_alerts', 'alert')

    # An example of a stream upload
    data_upload.stream_ingest(candidate_df, 'ztf_alerts', 'candidate')


.. _BigQuery: https://cloud.google.com/bigquery/
.. _here: https://cloud.google.com/bigquery/docs/loading-data
