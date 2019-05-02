#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""This module provides a client for the BigQuery backend."""

import json


def export_schema(client, path, tables, data_set):
    """Export the current backend schema to file

    Args:
        client    (Client): A BigQuery client
        path         (str): Path of output .json file
        tables (list[str]): Name of tables to export schemas for
        data_set     (str): Name of the GCP data set
    """

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
