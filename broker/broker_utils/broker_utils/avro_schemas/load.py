#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``avro_schemas.load`` module loads and returns Avro schemas."""

from importlib.resources import path as rpath
import fastavro


REGISTERED_SCHEMAS = [
    "elasticc.v0_9.alert.avsc",
    "elasticc.v0_9.brokerClassification.avsc",
]


def all():
    """Load all schemas in SCHEMAS and return as a dictionary."""
    return dict(
        [
            (schema, fastavro.schema.load_schema(_path(schema)))
            for schema in REGISTERED_SCHEMAS
        ]
    )


def _path(schema):
    """Return the actual file system path of ``schema``."""
    with rpath(__package__, schema) as fin:
        return fin
