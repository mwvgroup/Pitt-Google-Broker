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
    map_to_schema

broker.data_upload
------------------

.. automodule:: broker.data_upload

.. py:currentmodule:: broker.data_upload

.. autosummary::

   batch_ingest
   stream_ingest

broker.xmatch
-------------

.. automodule:: broker.xmatch

.. py:currentmodule:: broker.xmatch

.. autosummary::

    get_alerts_ra_dec
    get_xmatches

broker.ztf_archive
------------------

.. automodule:: broker.ztf_archive

.. py:currentmodule:: broker.ztf_archive

.. autosummary::

    download_data_date
    download_recent_data
    get_remote_release_list
    get_local_release_list
    get_local_alert_list
    get_alert_data
    iter_alerts
    plot_stamps
