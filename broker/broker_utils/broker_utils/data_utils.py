#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``data_utils`` module contains common functions used to manipulate
survey and broker data.
"""

from collections import namedtuple
from io import BytesIO
from pathlib import Path
from typing import Union

import fastavro
import json
import pandas as pd

from .schema_maps import get_key, get_value


AlertIds = namedtuple("AlertIds", "objectId sourceId")


class idUtils:
    """Functions to work with AlertIds."""

    def __init__(self, schema_map):
        """Initialize class instance."""
        self.schema_map = schema_map

    def get_ids(self, alert_dict=None, attrs=None):
        """Extract the ids and return an AlertIds object."""
        if not attrs:
            return AlertIds(
                get_value("objectId", alert_dict, self.schema_map),
                get_value("sourceId", alert_dict, self.schema_map),
            )
        else:
            id_keys = self.get_id_keys()
            return AlertIds(
                attrs.get(id_keys.objectId),
                attrs.get(id_keys.sourceId),
            )

    def get_id_keys(self):
        """Return an AlertIds object where the values are the survey's id key names."""
        return AlertIds(
            get_key("objectId", self.schema_map),
            get_key("sourceId", self.schema_map),
        )

    def ids_to_strings(self, alert_ids):
        """Convert values in ``alert_ids`` to strings."""
        return AlertIds(str(alert_ids.objectId), str(alert_ids.sourceId))


def load_alert(
    fin: Union[str, Path],
    return_as: str = "dict",
    **kwargs
) -> Union[bytes, dict, pd.DataFrame]:
    """Load alert from file at ``fin`` and return in format ``return_as``.

    Args:
        fin:        Path to an alert avro file.
        return_as:  Format the alert will be returned in. One of 'bytes' or argument
                    accepted by ``decode_alert``.
        kwargs:     Keyword arguments for ``decode_alert``.
    """
    if return_as == "bytes":
        with open(fin, "rb") as f:
            alert = f.read()
    else:
        alert = decode_alert(fin, return_as=return_as, **kwargs)
    return alert


def decode_alert(
    alert_avro: Union[str, Path, bytes],
    return_as: str = 'dict',
    drop_cutouts: bool = False,
    **kwargs
) -> Union[dict, pd.DataFrame]:
    """Load an alert Avro and return in requested format.

    Wraps `alert_avro_to_dict()` and `alert_dict_to_dataframe()`.

    Args:
        alert_avro:   Either the path of Avro file to load, or
            the bytes encoding the Avro-formated alert.
        return_as: Format the alert will be returned in. One of 'dict' or 'df'.
        drop_cutouts: Whether to drop or return the cutouts (stamps).
                      If `return_as='df'` the cutouts are always dropped.
        kwargs: Keyword arguments passed to ``_drop_cutouts`` and
                ``alert_dict_to_dataframe``.

    Returns:
        alert packet in requested format
    """
    alert_dict = alert_avro_to_dict(alert_avro)

    if return_as == "dict":
        if drop_cutouts:
            return _drop_cutouts(alert_dict, **kwargs)
        else:
            return alert_dict

    elif return_as == "df":
        return alert_dict_to_dataframe(alert_dict, **kwargs)

    else:
        raise ValueError("`return_as` must be one of 'dict' or 'df'.")


def alert_avro_to_dict(alert_avro: Union[str, Path, bytes]) -> dict:
    """Load an alert Avro to a dictionary.

    Args:
        alert_avro:   Either the path of Avro file to load, or
            the bytes encoding the Avro-formated alert.

    Returns:
        alert as a dict
    """
    if isinstance(alert_avro, str) or isinstance(alert_avro, Path):
        with open(alert_avro, 'rb') as fin:
            alert_list = [r for r in fastavro.reader(fin)]  # list of dicts
    elif isinstance(alert_avro, bytes):
        try:
            with BytesIO(alert_avro) as fin:
                alert_list = [r for r in fastavro.reader(fin)]  # list of dicts
        except ValueError:
            try:
                # this function is mis-named because here we accept json encoding.
                # consider re-encoding alert packets using original Avro format
                # throughout broker to give users a consistent end-product.
                # then this except block will be unnecessary.
                alert_list = [json.loads(alert_avro.decode("UTF-8"))]  # list of dicts
            except ValueError:
                msg = (
                    "alert_avro is a bytes object, but does not seem to be either "
                    "json or Avro encoded. Cannot decode."
                )
                raise ValueError(msg)
    else:
        msg = (
            "Unable to open alert_avro. "
            "It must be either the path to a valid Avro file as a string, "
            "or bytes encoding an Avro-formated alert."
        )
        raise TypeError(msg)

    # we expect the list to contain exactly 1 entry
    if len(alert_list) == 0:
        raise ValueError('The alert Avro contains 0 valid entries.')
    if len(alert_list) > 1:
        raise ValueError('The alert Avro contains >1 entry.')

    alert_dict = alert_list[0]
    return alert_dict


def alert_dict_to_dataframe(alert_dict: dict, schema_map: dict) -> pd.DataFrame:
    """ Packages an alert into a dataframe.
    Adapted from: https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    src_df = pd.DataFrame(alert_dict[schema_map['source']], index=[0])
    prvs_df = pd.DataFrame(alert_dict[schema_map['prvSources']])
    df = pd.concat([src_df, prvs_df], ignore_index=True)

    # attach some metadata. note this may not be preserved after all operations
    # https://stackoverflow.com/questions/14688306/adding-meta-information-metadata-to-pandas-dataframe
    # make sure this does not overwrite existing columns
    if "objectId" not in df.keys():
        df.objectId = get_value("objectId", alert_dict, schema_map)
    if "sourceId" not in df.keys():
        df.sourceId = get_value("sourceId", alert_dict, schema_map)

    return df


def _drop_cutouts(alert_dict: dict, schema_map: dict) -> dict:
    """Drop the cutouts from the alert dictionary."""
    cutouts = [
        schema_map['cutoutScience'],
        schema_map['cutoutTemplate'],
        schema_map['cutoutDifference']
    ]

    if schema_map['SURVEY'] == 'decat':
        alert_lite = {k: v for k, v in alert_dict.items()}
        for co in cutouts:
            alert_lite[schema_map['source']].pop(co, None)
            for psource in alert_lite[schema_map['prvSources']]:
                psource.pop(co, None)

    elif schema_map['SURVEY'] in ['ztf',  'elasticc']:
        alert_lite = {k: v for k, v in alert_dict.items() if k not in cutouts}

    return alert_lite
