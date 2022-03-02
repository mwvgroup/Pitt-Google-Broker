#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Functions for convenience."""

from broker_utils import data_utils, schema_maps
from pathlib import Path


ztf_schema_map = schema_maps.load_schema_map("ztf", False)

dir = Path(__file__).parent.resolve()
falert = "ztf_20210401_programid1_1617259045383.avro"
fname_test_alert = f"{dir}/{falert}"


def load_alert_file(kwargs={}):
    """Load an alert from disk. Wraps data_utils.decode_alert()."""
    kwargs.setdefault("schema_map", ztf_schema_map)

    return data_utils.decode_alert(alert_avro=fname_test_alert, **kwargs)


# --- General Utilities --- #
class AttributeDict(dict):
    """Class to access dict keys like attributes."""

    def __getattr__(self, attr):
        """getattr."""
        return self[attr]

    def __setattr__(self, attr, value):
        """setattr."""
        self[attr] = value
