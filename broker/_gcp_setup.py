#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""The ``gcp_setup`` module sets up a GCP project for use with the ``broker``
package.

This module is used to set up the necessary sinks and BigQuery datasets used by
the parent package. It does not create any BigQuery data tables, as those are
created automatically if / when required.
"""

import os

if not os.environ.get('GPB_OFFLINE', False):
    from google.api_core.exceptions import NotFound
    from google.cloud import bigquery, logging, storage

_tables = ('alert', 'candidate')


def _setup_big_query():
    """Create the necessary Big Query datasets if they do not already exist

    New data sets include:
      ``ztf_alerts``
    """

    bigquery_client = bigquery.Client()
    bigquery_client.create_dataset('ztf_alerts', exists_ok=True)


def _setup_buckets():
    """Create new storage buckets

    New buckets include:
      ``<project_id>_logging_bucket``
      ``<project_id>_ztf_images
    """

    storage_client = storage.Client()

    # Create bucket names
    project_id = os.environ['BROKER_PROJ_ID']
    logging_name = f'{project_id}_logging_bucket'
    alert_avro_name = f'{project_id}_alert_avro_bucket'
    release_tar_name = f'{project_id}_release_tar_bucket'
    buckets = (logging_name, alert_avro_name, release_tar_name)

    # Create buckets if the do not exist
    for bucket_name in buckets:
        try:
            storage_client.get_bucket(bucket_name)

        except NotFound:
            storage_client.create_bucket(bucket_name)


def _setup_logging_sinks():
    """Create sinks for exporting log entries to GCP

    This function assumes destination buckets have already been created.

    New Sinks include:
      ``broker_logging_sink``
    """

    # Create bucket name
    project_id = os.environ['BROKER_PROJ_ID']
    logging_bucket_name = f'{project_id}_logging_bucket'

    # Define logging sink
    logging_client = logging.Client()
    logging_sink_name = 'logging_sink'
    logging_filter = None
    destination = f'storage.googleapis.com/{logging_bucket_name}'
    sink = logging_client.sink(
        logging_sink_name,
        logging_filter,
        destination)

    # Create sink if not exists
    if not sink.exists():
        sink.create()


def setup_gcp():
    """Create and setup GCP products required by the ``broker`` package

    New data sets include:
      ``ztf_alerts``

    New buckets include:
     ``<project_id>_logging_bucket``
     ``<project_id>_ztf_images``

    New sinks include:
      ``broker_logging_sink``
    """

    _setup_big_query()
    _setup_buckets()
    _setup_logging_sinks()
