#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Parse ZTF alerts and add them to the project database."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import fastavro
import pandavro as pdx

from ..utils import setup_log

if 'RTD_BUILD' not in os.environ:
    from google.cloud import error_reporting, bigquery, storage

    error_client = error_reporting.Client()
    bq_client = bigquery.Client()
    log = setup_log('data_upload')

SCHEMA_DIR = Path(__file__).resolve().parent / 'schema'


def _get_table_id(data_set, table):
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
    table_id = _get_table_id(data_set, table)
    data.to_gbq(
        table_id,
        project_id,
        if_exists='append',
        progress_bar=False
    )


def batch_ingest(data, data_set, table):
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


def get_schema(schemavsn):
    """Return the avro schema for a given ZTF schema version

    Args:
        schemavsn (str): ZTF schema version (e.g. '3.2')

    Returns:
        The schema as a dictionary
    """

    schema_path = SCHEMA_DIR / f'ztf_{schemavsn}.json'
    if not schema_path.exists():
        raise ValueError(f'No ZTF schema version found matching "{schemavsn}"')

    with open(schema_path, 'r') as ofile:
        return json.load(ofile)


def save_to_avro(data, schemavsn='3.2', path=None, fileobj=None):
    """Save ZTF alert data to an avro file

    Args:
        data    (DataFrame): Alert data to write to file
        schemavsn     (str): ZTF schema version of output file (Default: '3.2')
        path          (str): Output file path
        fileobj (file-like): Output file object
    """

    if not (path or fileobj):
        raise ValueError('Must specify either `path` or `fileobj`.')

    elif path and fileobj:
        raise ValueError('Cannot specify both `path` and `fileobj`.')

    elif path:
        if not path.endswith('.avro'):
            path += '.avro'

        fileobj = open(path, 'wb')

    schema = get_schema(schemavsn)
    fastavro.writer(fileobj, schema, data.to_dict('records'))

    if path:
        fileobj.close()
