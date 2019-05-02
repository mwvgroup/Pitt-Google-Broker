#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""This script sets up your GCP environment for the `broker` package."""

import json

from google.cloud import bigquery, logging, storage

_tables = ('alert', 'candidate')


def setup_big_query(schema_path):
    """Create the necessary Big Query tables if they do not already exist

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

        except ValueError:
            table_schema = db_schema['table_name']
            table = bigquery.Table(table_id, schema=table_schema)
            bigquery_client.create_table(table)


def setup_logging_sinks():
    """Create sinks for exporting log entries to GCP"""

    storage_client = storage.Client()
    logging_bucket_name = 'broker_logging_bucket'

    # Create storage bucket if not exist
    try:
        storage_client.get_bucket(logging_bucket_name)

    except:
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


if __name__ == '__main__':
    setup_big_query('./bq_schema.json')
    setup_logging_sinks()
