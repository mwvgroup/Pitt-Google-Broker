API Reference
=============

broker
------

.. automodule:: broker

.. py:currentmodule:: broker

.. autosummary::

   setup_gcp


broker.alert_ingestion
----------------------


.. automodule:: broker.alert_acquisition

broker.alert_ingestion.ztf
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: broker.alert_acquisition.ztf

.. py:currentmodule:: broker.alert_acquisition.ztf

.. autosummary::

    get_alerts
    map_alert_list_to_schema

broker.data_upload
------------------

.. automodule:: broker.data_upload

.. py:currentmodule:: broker.data_upload

.. autosummary::

   _batch_ingest
   _stream_ingest
   upload_to_bucket
   get_schema
   save_to_avro

broker.xmatch
-------------

.. automodule:: broker.xmatch

.. py:currentmodule:: broker.xmatch

.. autosummary::

    get_alerts_ra_dec
    get_xmatches
    upload_to_bucket_file_

broker.ztf_archive
------------------

.. automodule:: broker.ztf_archive

.. py:currentmodule:: broker.ztf_archive

.. autosummary::

   archive_url
   create_ztf_sync_table
   delete_local_data
   download_data_date
   download_recent_data
   get_alert_data
   get_local_alert_list
   get_local_release_list
   get_remote_md5_table
   iter_alerts
   plot_stamps
