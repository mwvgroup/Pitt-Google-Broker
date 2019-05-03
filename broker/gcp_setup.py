#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""This module sets up a GCP project for use with the `broker` package.

Examples:
>>> # Se a list of changes that will be made to your project
>>> help(setup_gcp)
>>>
>>> # Setup your GCP project
>>> setup_gcp()
>>>
>>> # Export a json copy of the GCP BigQuery schema used by this package
>>> export_schema('./schema.json')
"""

import json
from pathlib import Path

from google.api_core.exceptions import NotFound
from google.cloud import bigquery, logging, storage

_tables = ('alert', 'candidate')
_schema_path = Path(__file__).resolve().parent / 'bigquery_schema.json'


def _setup_big_query(schema_path):
    """Create the necessary Big Query tables if they do not already exist

    Creates:
        Datasets: ztf_alerts
        Tables  : alert, candidate

    Args:
        schema_path (Str): Path to a json file defining DB schema
    """

    bigquery_client = bigquery.Client()
    data_set = bigquery_client.create_dataset('ztf_alerts', exists_ok=True)

    with open(schema_path) as ofile:
        db_schema = json.load(ofile)

    for table_name in _tables:
        table_id = f'{data_set.project}.{data_set.dataset_id}.{table_name}'
        try:
            bigquery_client.get_table(table_id)

        except NotFound:
            table_schema = [bigquery.SchemaField(**kwargs) for kwargs in
                            db_schema[table_name]]
            table = bigquery.Table(table_id, schema=table_schema)
            bigquery_client.create_table(table)


def _setup_logging_sinks():
    """Create sinks for exporting log entries to GCP

    Creates:
        Buckets: broker_logging_bucket
        Sinks  : broker_logging_sink
    """

    storage_client = storage.Client()
    logging_bucket_name = 'broker_logging_bucket'

    # Create storage bucket if not exist
    try:
        storage_client.get_bucket(logging_bucket_name)

    except NotFound:
        storage_client.create_bucket(logging_bucket_name)

    # Define logging sink
    logging_client = logging.Client()
    logging_sink_name = 'broker_logging_sink'
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
    """Setup a GCP environment

    Creates:
        Datasets: ztf_alerts
        Tables  : alert, candidate
        Buckets : broker_logging_bucket
        Sinks   : broker_logging_sink
    """

    _setup_big_query(_schema_path)
    _setup_logging_sinks()


def export_schema(path, client=None, tables=_tables, data_set='ZTF'):
    """Export the current backend schema to file

    By Default export the schema for all tables used by this package

    Args:
        path         (str): Path of output .json file
        client    (Client): A BigQuery client (Optional)
        tables (list[str]): Table names to export schemas for (Optional)
        data_set     (str): Name of the GCP data set (Optional)
    """

    if client is None:
        client = bigquery.Client()

    data_set = client.get_dataset(data_set)

    schema_json = {}
    for table_name in tables:
        table = client.get_table(
            f'{data_set.project}.{data_set.dataset_id}.{table_name}')
        table_schema = []
        for field in table.schema:
            field_dict = {
                'name': field.name,
                'field_type': field.field_type,
                'mode': field.mode,
                'description': field.description
            }

            table_schema.append(field_dict)

        schema_json[table_name] = table_schema

    if not path.endswith('.json'):
        path += '.json'

    with open(path, 'w') as ofile:
        json.dump(schema_json, ofile, indent=2, sort_keys=True)
