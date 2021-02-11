#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

""" The ``gen_valid_schema`` module generates a corrected alert schema from an
Avro file. Used when the schema in the incoming alerts is not a valid schema
under the strict requirements of BigQuery. This only needs to be done once for
each survey version. The corrected schema is stored in a pickle file which is used by the GCS storage module to fix the affected alert packets
before storing them as Avro files.

Usage Example
-------------

Survey versions that have already been configured are registered in the
``format_funcs`` dict in the ``write_valid_schema()`` function. To
configure a new survey version, define a new function that accepts the
schema from the survey's Avro file (the schema to be corrected) as a dict
and returns the corrected schema as a dict. See ``_fix_schema_ZTF_v3_3()``
for an example. Register the new function in the ``format_funcs`` dict.
Then generate the pickle file as follows.

.. code-block:: python
   :linenos:

   from broker.alert_ingenstion import gen_valid_schema as gvs

   fin = <path to Avro file>
   survey, version = 'ztf', 3.3
   valid_schema = gvs.write_valid_schema(fin, survey, version)

Module Documentation
--------------------
"""

from pathlib import Path
import logging
from typing import Tuple, List, BinaryIO, Union
import pickle
import json
import fastavro

log = logging.getLogger(__name__)


def write_valid_schema(fin: str, survey: str, version: float) -> dict:
    """ Corrects an Avro file schema to comply with the strict validation
    requirements of BigQuery. Writes the corrected schema to a pickle file and
    also returns it as a dict.

    Args:
        fin         : Path to alert Avro file.
        survey      : The name of the survey the alert is from.
        version     : The schema version of the alert is from.

    Returns:
        schema  : corrected schema
    """

    format_funcs = {
        'ztf': {
            3.3: _fix_schema_ZTF_v3_3
        }
    }

    fpkl = f'{survey}_v{version}.pkl'
    fout = Path(__file__).resolve().parent / 'valid_schemas' / fpkl

    schema, __ = _load_Avro(fin)  # load the file

    try:
        format_func = format_funcs.get(survey, {})[version]

    except IndexError:
        err_msg = f'Formatting not available for {survey} {version}'
        log.error(err_msg)
        raise RuntimeError(err_msg)

    else:
        valid_schema = format_func(schema)  # get the corrected schema
        _write_dict_to_pickle(valid_schema, fout)

    return valid_schema


def _fix_schema_ZTF_v3_3(schema: dict) -> dict:
    """ Corrects the ZTF version 3.3 schema to comply with the strict Avro
    validation requirements of BigQuery.

    Args:
        schema : Avro schema header, as returned by _load_Avro()

    Returns:
        schema : updated schema
    """

    for l1, l1_field in enumerate(schema['fields']):  # l1_field is a dict

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
    """ Reverses the order of field['type'] if it is a list _and_
    field['default'] is null or is not specified. Otherwise the field is
    returned unchanged. This is intended to move the 'null' element to the
    beginning on the type list, but it is up to the user to make sure 'null'
    is at the end of the list before calling this function.

    Args:
        field : single element of the 'fields' list in the ZTF Avro schema dict

    Returns:
        field : input field with the 'type' list reversed if necessary.
    """

    if isinstance(field['type'], list):

        try:
            if field['default'] is None:  # default is None -> reverse the list
                new_types = field['type'][::-1]
            else:  # default is something other than null -> leave unchanged
                new_types = field['type']
        except KeyError:  # default not specified -> reverse the list
            new_types = field['type'][::-1]

        field['type'] = new_types

    return field


def _load_Avro(fin: Union[Path, BinaryIO]) -> Tuple[dict, List[dict]]:
    """
    Args:
        fin   (str or file-like) : Path to, or file-like object representing,
                                   alert Avro file

    Returns:
        schema (dict) : schema from the Avro file header.
        data   (list) : list of dicts containing the data from the Avro file.
    """

    is_path = isinstance(fin, str)
    f = open(fin, 'rb') if is_path else fin

    avro_reader = fastavro.reader(f)
    schema = avro_reader.writer_schema
    data = [r for r in avro_reader]

    if is_path:
        f.close()

    return schema, data


def _write_dict_to_pickle(schema: dict, fout: str) -> None:
    """ Writes the schema to file as a dictionary"""

    with open(fout, 'wb') as file:
        pickle.dump(schema, file)  # write the dict to a pkl file


def _write_schema_to_bytes_file(schema: dict, valid_schema: dict, fout_stub: str) -> None:
    """ Converts the schema dicts to bytes objects, the writes them to file.

    Args:
        schema      : Original schema
        valid_schema: Corrected schema
        fout_stub   : Path stub to write the corrected schema header (as a
                      bytes object).
                        - Original schema will be written to
                        'fout_stub_original.bytes'.
                        - Corrected schema will be written to
                        'fout_stub_valid.bytes'.
    """

    z = zip(
            [schema, valid_schema],
            [f'{fout_stub}_original.bytes', f'{fout_stub}_valid.bytes']
        )

    for sch, fout in z:
        schema_bytes = json.dumps(sch).encode('utf-8')
        with open(fout, 'wb') as f:
            f.write(schema_bytes)


def _write_Avro(fout: str, schema: dict, data: list) -> None:
    """ Writes the schema and data to an Avro file.
    schema and data as returned by _load_Avro()
    """

    with open(fout, 'wb') as out:
        fastavro.writer(out, schema, data)
