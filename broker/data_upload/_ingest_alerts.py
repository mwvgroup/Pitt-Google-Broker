#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Parse ZTF alerts and add them to the project database."""

import os
from tempfile import NamedTemporaryFile

import pandavro as pdx

from .._utils import setup_log

if 'RTD_BUILD' not in os.environ:
    from google.cloud import error_reporting, bigquery

    error_client = error_reporting.Client()
    bq_client = bigquery.Client()
    log = setup_log('data_upload')


def get_table_id(data_set, table):
    """Return the ID for a BigQuery table

    Args:
        data_set (str): The name of the data set
        table    (str): The name of the table

    Returns:
        The name of the specified table as a string
    """

    table_ref = bq_client.dataset(data_set).table(table)
    return f'{table_ref.dataset_id}.{table_ref.table_id}'


def stream_ingest(data, data_set, table):
    """Stream ingest a Pandas DataFrame into a BigQuery table

    If the table does not exist, create it.

    Args:
        data (DataFrame): Data to upload to table
        data_set   (str): The name of the data set
        table      (str): The name of the table
    """

    project_id = os.environ['BROKER_PROJ_ID']
    table_id = get_table_id(data_set, table)
    data.to_gbq(
        table_id,
        project_id,
        if_exists='append',
        progress_bar=False
    )


def batch_ingest(data, data_set, table):
    """Ingest ZTF alerts into BigQuery via the batch upload interface

    Alert data WILL be temporarily written to disk. If the table does not
    exist, create it.

    Args:
        data (DataFrame): Data to upload to table
        data_set   (str): The name of the data set
        table      (str): The name of the table
    """

    # Configure batch loading
    job_config = bigquery.LoadJobConfig()
    job_config.source_format = bigquery.SourceFormat.AVRO

    # Get tables to store data
    table_id = get_table_id(data_set, table)

    with NamedTemporaryFile() as source_file:
        pdx.to_avro(source_file.name, data)

        try:
            # API request
            log.debug('Launching batch upload job.')
            job = bq_client.load_table_from_file(
                source_file,
                table_id,
                location="US",
                job_config=job_config,
            )

        except KeyboardInterrupt:
            job.result()
            raise
