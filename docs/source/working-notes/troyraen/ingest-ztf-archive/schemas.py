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


def alert2avsc(falert, *, version="3.3", fixschema=True):
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


def fix_schema(schema: dict):
    """Reorder types so "null" is first if the default value is null or doesn't exist, else last."""
    newschema = {k: v for k, v in schema.items() if k != "fields"}
    fields = [f for f in schema["fields"]]

    # do nested fields first, then top-level fields
    for fld in fields:

        if fld["name"] == "candidate":
            # fld['type'] is a record (dict with fields)
            # for cfld in fld['type']['fields']:
            #     newcandfields.append(_fix_field(cfld))
            # fld['type']['fields'] = _do_record(fld)
            newcandfields = []
            for cfld in fld["type"]["fields"]:
                newcandfields.append(_fix_field(cfld))
            fld["type"]["fields"] = newcandfields

        if fld["name"] == "prv_candidates":
            # fld['type'] is a list, and one item is a record (dict with items and fields)
            for fd in fld["type"]:
                if not isinstance(fd, dict):
                    continue

                # fd['items']['fields'] = _do_record(fd['type']['items'])
                newcandfields = []
                for cfld in fd["items"]["fields"]:
                    newcandfields.append(_fix_field(cfld))
                fd["items"]["fields"] = newcandfields

    newfields = []
    for fld in fields:
        newfields.append(_fix_field(fld))
    newschema["fields"] = newfields

    return newschema


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

