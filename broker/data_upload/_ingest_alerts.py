#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module handles the uploading of generic data into bigquery."""

import os
from tempfile import NamedTemporaryFile

import pandavro as pdx

from ..utils import RTDSafeImport, setup_log

with RTDSafeImport():
    from google.cloud import error_reporting, bigquery, storage

    error_client = error_reporting.Client()
    log = setup_log('data_upload')


def _get_table_id(data_set, table):
    """Return the ID for a BigQuery table

    Args:
        data_set (str): The name of the data set
        table    (str): The name of the table

    Returns:
        The name of the specified table as a string
    """

    bq_client = bigquery.Client()
    table_ref = bq_client.dataset(data_set).table(table)
    return f'{table_ref.dataset_id}.{table_ref.table_id}'


def _stream_ingest(data, data_set, table):
    """Stream ingest a Pandas DataFrame into a BigQuery table

    If the table does not exist, create it.

    Args:
        data (DataFrame): Data to upload to table
        data_set   (str): The name of the data set
        table      (str): The name of the table
    """

    project_id = os.environ['BROKER_PROJ_ID']
    table_id = _get_table_id(data_set, table)
    data.to_gbq(
        table_id,
        project_id,
        if_exists='append',
        progress_bar=False
    )


def _batch_ingest(data, data_set, table):
    """Batch upload a Pandas DataFrame into a BigQuery table

    Alert data may be temporarily written to disk. If the table does not
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
    table_id = _get_table_id(data_set, table)

    bq_client = bigquery.Client()
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


def upload_to_bigquery(data, data_set, table_name, method='batch',
                       max_tries=1, verbose=True):
    """Batch upload a Pandas DataFrame into a BigQuery table

    If the upload fails, retry until success or until max_tries is reached.

    Args:
        data (DataFrame): Data to upload to table
        data_set   (str): The name of the data set
        table_name (str): The name of the table
        method     (str): The method upload name ('batch' or 'stream')
        max_tries  (int): Maximum number of tries until error (Default: 1)
    """

    if method == 'batch':
        upload_func = _batch_ingest

    elif method == 'stream':
        upload_func = _stream_ingest

    else:
        raise ValueError(f'Invalid upload method: {method}')

    for i in range(max_tries):
        if i >= max_tries:
            raise RuntimeError('Could not upload data. Max tries exceeded.')

        try:
            upload_func(data, data_set, table_name)

        except KeyboardInterrupt:
            raise

        except Exception as e:
            if verbose:
                print(f'Error uploading to table {table_name}: {str(e)}')
                print('Trying again...')

            continue


def upload_to_bucket(bucket_name, source_path, destination_name):
    """Uploads a file to a GCP storage bucket

    Args:
        bucket_name      (str): Name of the bucket to upload into
        source_path      (str): Path of the file to upload
        destination_name (str): Name of the file to be created
    """

    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_name)
    blob.upload_from_filename(source_path)
