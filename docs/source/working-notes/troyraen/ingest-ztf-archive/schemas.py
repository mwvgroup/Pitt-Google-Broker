#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import fastavro
from pathlib import Path
import json
import pickle


ROOTDIR = Path(__file__).parent / "schemas"
ROOTDIR.mkdir(exist_ok=True)


def FPATH(version="3.3", nocutouts=True):
    """Return path to .avsc schema file for this version."""
    if nocutouts:
        return ROOTDIR / f"ztf_v{version}_nocutouts.avsc"
    return ROOTDIR / f"ztf_v{version}.avsc"


def loadavsc(version="3.3", nocutouts=True):
    """Load Avro schema from file."""
    with open(FPATH(version, nocutouts), "rb") as f:
        return json.load(f)


def alert2avsc(falert, *, version='3.3', fixschema=True):
    """Create .avsc schemas from alert Avro file."""
    with open(falert, "rb") as f:
        schema = fastavro.reader(f).writer_schema

    if fixschema:
        schema = fix_schema(schema)

    # write schema with cutouts
    with open(FPATH(version, nocutouts=False), "w") as f:
        json.dump(schema, f)

    # write schema without cutouts
    flds = schema.pop("fields")
    schema["fields"] = [f for f in flds if not f["name"].startswith("cutout")]
    spath = FPATH(version, nocutouts=True)
    with open(spath, "w") as f:
        json.dump(schema, f)


def fix_schema_deprecated(schema: dict):
    """Reorder types so "null" is first if the default value is null or doesn't exist, else last."""
    newschema = {k: v for k, v in schema.items() if k != "fields"}
    # fields = [f for f in schema["fields"] if not f["name"].startswith("cutout")]
    fields = [f for f in schema["fields"]]
    newfields = []
    for fld in fields:
        newfields.append(_do_one_field(fld))
    newschema["fields"] = newfields
    return newschema


def fix_schema(schema: dict):
    """Reorder types so "null" is first if the default value is null or doesn't exist, else last."""
    newschema = {k: v for k, v in schema.items() if k != "fields"}
    fields = [f for f in schema["fields"]]

    # do nested fields first, then top-level fields
    for fld in fields:

        if fld['name'] == "candidate":
            # fld['type'] is a record (dict with fields)
            # for cfld in fld['type']['fields']:
            #     newcandfields.append(_fix_field(cfld))
            # fld['type']['fields'] = _do_record(fld)
            newcandfields = []
            for cfld in fld['type']['fields']:
                newcandfields.append(_fix_field(cfld))
            fld['type']['fields'] = newcandfields

        if fld['name'] == "prv_candidates":
            # fld['type'] is a list, and one item is a record (dict with items and fields)
            for fd in fld['type']:
                if not isinstance(fd, dict):
                    continue

                # fd['items']['fields'] = _do_record(fd['type']['items'])
                newcandfields = []
                for cfld in fd['items']['fields']:
                    newcandfields.append(_fix_field(cfld))
                fd['items']['fields'] = newcandfields

    newfields = []
    for fld in fields:
        newfields.append(_fix_field(fld))
    newschema["fields"] = newfields

    return newschema


def _do_record_deprecated(fld: dict) -> dict:
    newfields = []
    for cfld in fld['type']['fields']:
        newfields.append(_fix_field(cfld))
    return newfields


def _do_one_field_deprecated(field: dict) -> dict:
    """Fix one field. Descend tree if necessary."""
    ftyp = field["type"]
    if isinstance(field["type"], str):
        return field

    newfield = {k: v for k, v in field.items() if k != "type"}

    if isinstance(ftyp, dict):
        newftyp = {k: v for k, v in ftyp.items() if k != "fields"}
        flds = []
        for fld in ftyp["fields"]:
            flds.append(_do_one_field(fld))
        newftyp["fields"] = flds
        newfield["type"] = newftyp
        return newfield

    if isinstance(ftyp, list):
        # fix top level
        newfield = _fix_field(field)

        # fix individual items that are themselves records
        newitems = []
        for item in newfield["type"]:
            if isinstance(item, dict) and ("items" in item):
                newitem = {k: v for k, v in item["items"].items() if k != "fields"}
                newflds = []
                for fld in item["items"]["fields"]:
                    newflds.append(_do_one_field(fld))
                newitem["fields"] = newflds
                newitems.append(newitem)
            else:
                newitems.append(item)

        newfield["type"] = newitems
        return newfield


def _fix_field(field: dict) -> dict:
    """Reorder field['type'] to match field['default'].

    Args:
        `field`:    Avro field (dict) with a 'type' key
    """
    if not isinstance(field["type"], list):
        return field

    ftyp = [t for t in field["type"]]
    if "null" not in ftyp:
        return field

    ftyp.remove("null")
    newfield = {k: v for k, v in field.items() if k != "type"}

    if field.get("default") is None:
        # 'null' should appear first
        newfield["type"] = ["null"] + ftyp
        return newfield

    newfield["type"] = ftyp + ["null"]
    return newfield


def pkl2avsc():
    """Create .avsc schemas from .pkl, with cutouts and without."""
    SURVEY, version = "ztf", "3.3"
    fpkl = f"valid_schemas/{SURVEY}_v{version}.pkl"
    with open(fpkl, "rb") as infile:
        valid_schema = pickle.load(infile)

    # write schema with cutouts
    with open(fpkl.replace(".pkl", ".avsc"), "w") as f:
        json.dump(valid_schema, f)

    # write schema without cutouts
    flds = valid_schema.pop("fields")
    valid_schema["fields"] = [f for f in flds if not f["name"].startswith("cutout")]
    with open(fpkl.replace(".pkl", "_nocutouts.avsc"), "w") as f:
        json.dump(valid_schema, f)


def _fix_schema_ZTF_v3_3_deprecated(schema: dict) -> dict:
    """ Corrects the ZTF version 3.3 schema to comply with the strict Avro
    validation requirements of BigQuery.

    Args:
        schema : Avro schema header, as returned by _load_Avro()

    Returns:
        schema : updated schema
    """

    for l1, l1_field in enumerate(schema['fields']):  # l1_field is a dict

        # do the top level fields
        schema['fields'][l1] = _fix_field(l1_field)

    for l1, l1_field in enumerate(schema['fields']):  # l1_field is a dict
        # do the nested candidate fields
        if l1_field['name'] == 'candidate':
            for l2, l2_field in enumerate(l1_field['type']['fields']):
                schema['fields'][l1]['type']['fields'][l2] = _fix_field(l2_field)

        # do the nested prv_candidate fields
        if l1_field['name'] == 'prv_candidates':
            # try:
            for l2, l2_field in enumerate(l1_field['type'][1]['items']['fields']):
                schema['fields'][l1]['type'][1]['items']['fields'][l2] = _fix_field(l2_field)
                # if isinstance(l2_field['type'], list):
                #     schema['fields'][l1]['type'][1]['items']['fields'][l2] = _fix_field(l2_field)
            # except TypeError:
            #     print("fail")
            #     print(l2, l2_field)

    # fastavro removes the top level doc item (I don't know why)
    # add it back in:
    schema['doc'] = 'avro alert schema for ZTF (www.ztf.caltech.edu)'

    return schema


def _reverse_types_deprecated(field: dict) -> dict:
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
