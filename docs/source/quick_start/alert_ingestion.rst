Ingesting Data to GCP
=====================

Alert ingestion is handled by the ``alert_acquisition`` and ``data_upload``
modules. This includes saving alert data to file and uploading data into
BigQuery.

To File / Bucket Storage
------------------------

The ``save_to_avro`` and ``upload_to_bucket`` functions handle file storage of
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

The ``data_upload`` module also supports uploading alert data to BigQuery using
the ``upload_to_bigquery`` function. By default data is ingested as a batch
upload, however stream uploading is also available via the ``method='stream'``
argument.

.. important:: See `here`_ for an overview of options and pricing models.

    # An example of a batch upload.
    # If an error occures, try twice before giving up.
    data_upload.upload_to_bigquery(alert_df, 'ztf_alerts', 'alert', max_tries=2)


.. _BigQuery: https://cloud.google.com/bigquery/
.. _here: https://cloud.google.com/bigquery/docs/loading-data
