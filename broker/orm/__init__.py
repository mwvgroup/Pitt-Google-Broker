import json
from google.cloud import bigquery

client = bigquery.Client()
data_set = client.create_dataset('ztf_alerts', exists_ok=True)
_tables = ('alert', 'candidate')


def setup(client, schema_path):
    """Create any tables if they do not already exist

    Args:
        client   (Client): A Google BigQuery client
        schema_path (Str): Path to a json file defining DB schema
    """

    with open(schema_path) as ofile:
        db_schema = json.load(ofile)

    for table_name in _tables:
        table_id = f'{data_set.project}.{data_set.dataset_id}.{table_name}'
        try:
            client.get_table(table_id)

        except ValueError:
            table_schema = db_schema['table_name']
            table = bigquery.Table(table_id, schema=schema)
            table = client.create_table(table)


def export_schema(path):
    """Export the current backend schema to file

    Args:
        path (str): Path of output .json file
    """

    schema_json = {}
    for table_name in _tables:
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
