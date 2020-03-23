#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``gcp_setup`` module sets up services on the Google Cloud Platform (GCP
project for use by the parent package. Setup tasks can be run individually or
collectively using the ``auto_setup`` function. Each task should only have to
be run once for a given GCP project.

Usage Example
-------------

.. code-block:: python
   :linenos:

   from broker import gcp_setup

   # Tasks can be run individually
   gcp_setup.setup_big_query
   gcp_setup.setup_buckets
   gcp_setup.setup_logging_sinks

   # Tasks can also be run as a collective set.
   gcp_setup.auto_setup


Module Documentation
--------------------
"""

import os

if not os.getenv('GPB_OFFLINE', False):
    from google.api_core.exceptions import NotFound
    from google.cloud import bigquery, logging, storage

_tables = ('alert', 'candidate')


def setup_big_query() -> None:
    """Create the necessary Big Query datasets if they do not already exist

    New data sets include:
      ``ztf_alerts``
    """

    bigquery_client = bigquery.Client()
    bigquery_client.create_dataset('ztf_alerts', exists_ok=True)


def setup_buckets() -> None:
    """Create new storage buckets

    New buckets include:
      ``<project_id>_alert_avro_bucket
    """

    storage_client = storage.Client()

    # Create bucket names
    project_id = os.environ['GOOGLE_CLOUD_PROJECT']
    alert_avro_name = f'{project_id}_alert_avro_bucket'

    # Create buckets if the do not exist
    for bucket_name in (alert_avro_name,):
        try:
            storage_client.get_bucket(bucket_name)

        except NotFound:
            storage_client.create_bucket(bucket_name)


def setup_logging_sinks() -> None:
    """Create sinks for exporting log entries to GCP

    This function assumes destination buckets have already been created.

    New Sinks include:
      ``broker_logging_sink``
    """

    # Define logging sink
    logging_client = logging.Client()
    logging_sink_name = 'logging_sink'
    sink = logging_client.sink(logging_sink_name)

    # Create sink if not exists
    if not sink.exists():
        sink.create()


def auto_setup() -> None:
    """Create and setup GCP products required by the ``broker`` package

    New data sets include:
      ``ztf_alerts``

    New buckets include:
     ``<project_id>_logging_bucket``
     ``<project_id>_ztf_images``

    New sinks include:
      ``broker_logging_sink``
    """

    setup_big_query()
    setup_buckets()
    setup_logging_sinks()
