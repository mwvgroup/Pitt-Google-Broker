#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

""" The ``gen_valid_schema`` module generates (and writes to file) a corrected alert schema from an Avro file. Used when the schema in the incoming alerts is not a valid schema under the strict requirements of BigQuery.


Usage Example
-------------

.. code-block:: python
   :linenos:

   import gen_valid_schema as gvs

   fin = <path to Avro file>
   fout_stub = 'ztf_v3_3'
   schema = gvs.get_write_valid_schema(fin, fout_stub, survey='ZTF', version=3.3)
"""

import logging
import json
import fastavro

log = logging.getLogger(__name__)


def write_valid_schema(fin: str, fout_stub: str, survey: str, version: float) -> dict:
    """ Corrects an Avro file schema to comply with the strict validation requirements of BigQuery. Writes both the original and corrected schemas to a bytes file and returns the corrected schema as a dict.

    Args:
        fin         : Path to alert Avro file.
        fout_stub   : Path stub to write the corrected schema header (as a bytes object).
                        Original schema will be written to 'fout_stub_original.bytes'.
                        Corrected schema will be written to 'fout_stub_valid.bytes'.
        survey      : The name of the survey the alert is from.
        version     : The schema version of the alert is from.

    Returns:
        schema  : corrected schema
    """

    format_funcs = {
        'ZTF': {
            3.3: _fix_schema_ZTF_v3_3
        }
    }

    schema, data = _load_Avro(fin) # load the file

    try:
        format_func = format_funcs.get(survey, {})[version]

    except IndexError:
        err_msg = f'Formatting not available for {survey} {version}'
        log.error(err_msg)
        raise RuntimeError(err_msg)

    else:
        valid_schema = format_func(schema) # get the corrected schema
        _write_schema_to_bytes_file(schema, valid_schema, fout_stub)

    return schema

def _fix_schema_ZTF_v3_3(schema: dict):
    """ Corrects the ZTF version 3.3 schema to comply with the strict Avro validation requirements of BigQuery.

    Args:
        schema : Avro schema header, as returned by _load_Avro()
    Returns:
        schema : updated schema
    """
    for l1, l1_field in enumerate(schema['fields']): # l1_field is a dict

        # do the top level fields
        schema['fields'][l1] = _reverse_types(l1_field)

        # do the nested candidate fields
        if l1_field['name'] == 'candidate':
            for l2, l2_field in enumerate(l1_field['type']['fields']):
                schema['fields'][l1]['type']['fields'][l2] = _reverse_types(l2_field)

        # do the nested prv_candidate fields
        if l1_field['name'] == 'prv_candidates':
            for l2, l2_field in enumerate(l1_field['type'][1]['items']['fields']):
                schema['fields'][l1]['type'][1]['items']['fields'][l2] = _reverse_types(l2_field)

    # fastavro removes the top level doc item (I don't know why)
    # add it back in:
    schema['doc'] = 'avro alert schema for ZTF (www.ztf.caltech.edu)'

    return schema

def _reverse_types(field: dict) -> dict:
    """ Reverses the order of field['type'] if it is a list _and_ field['default'] is null or is not specified. Otherwise the field is returned unchanged. This is intended to move the 'null' element to the beginning on the type list, but it is up to the user to make sure 'null' is at the end of the list before calling this function.

    Args:
        field : a single element of the 'fields' list in the ZTF Avro schema dict

    Returns:
        field : input field with the 'type' list reversed if necessary.
    """

    if isinstance(field['type'],list):

        try:
            if field['default'] is None: # default is None -> reverse the list
                new_types = field['type'][::-1]
            else: # default is something other than null -> leave list unchanged
                new_types = field['type']
        except KeyError: # default not specified -> reverse the list
            new_types = field['type'][::-1]

        field['type'] = new_types

    return field

def _load_Avro(fin: str):
    """
    Args:
        fin   (str) : Path to alert Avro file.

    Returns:
        schema (dict) : schema from the Avro file header.
        data   (dict) : data from the Avro file.
    """

    with open(fin, 'rb') as f:
        avro_reader = fastavro.reader(f)
        schema = avro_reader.writer_schema
        for r in avro_reader:
            data = r
            break
    return schema, data

def _write_Avro(fout: str, schema: dict, data: dict):
    """ Writes the schema and data to an Avro file.
    """
    with open(fout, 'wb') as out:
        fastavro.writer(out, schema, [data])

    return None

def _write_schema_as_dict(schema: dict, fout: str):
    """ Writes the schema to file as a dictionary
    """

def _write_schema_to_bytes_file(schema: dict, valid_schema: dict, fout_stub: str):
    """ Converts the schema dicts to bytes objects, the writes them to file.

    Args:
        schema      : Original schema
        valid_schema: Corrected schema
        fout_stub   : Path stub to write the corrected schema header (as a bytes object).
                        Original schema will be written to 'fout_stub_original.bytes'.
                        Corrected schema will be written to 'fout_stub_valid.bytes'.
    """

    z = zip(
            [schema, valid_schema],
            [f'{fout_stub}_original.bytes', f'{fout_stub}_valid.bytes']
        )

    for sch, fout in z:
        schema_bytes = json.dumps(sch).encode('utf-8')
        with open(fout, 'wb') as f:
            f.write(schema_bytes)

    return None
