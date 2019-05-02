#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""This module provides a client for the BigQuery backend."""

import json

from google.cloud import bigquery

client = bigquery.Client()
data_set = client.create_dataset('ztf_alerts', exists_ok=True)


def export_schema(path, tables):
    """Export the current backend schema to file

    Args:
        path         (str): Path of output .json file
        tables (list[str]): Name of tables to export schemas for
    """

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
