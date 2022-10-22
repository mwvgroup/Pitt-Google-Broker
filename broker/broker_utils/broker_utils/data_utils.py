#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``data_utils`` module contains common functions used to manipulate
survey and broker data.
"""

from base64 import b64decode
from io import BytesIO
import os
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Union

import fastavro
import json

# load pandas only when necessary. it hogs memory on Cloud Functions.
if TYPE_CHECKING:
    import pandas as pd

from .avro_schemas.load import all as load_all_schemas
from .types import AlertIds


LOGGER = logging.getLogger(__name__)
# cloud functions use GCP_PROJECT
if "GCP_PROJECT" in os.environ:
    import google.cloud.logging
    google.cloud.logging.Client().setup_logging()
    LOGGER.setLevel(logging.DEBUG)


def load_alert(
    fin: Union[str, Path],
    return_as: str = "dict",
    **kwargs
) -> Union[bytes, dict, "pd.DataFrame"]:
    """***Depreciated. Use open_alert() instead.***

    Load alert from file at ``fin`` and return in format ``return_as``.

    Args:
        fin:        Path to an alert avro file.
        return_as:  Format the alert will be returned in. One of 'bytes' or argument
                    accepted by ``decode_alert``.
        kwargs:     Keyword arguments for ``decode_alert``.
    """
    LOGGER.warn("Depreciated. Use open_alert() instead.")
    return open_alert(fin, return_as=return_as, **kwargs)
    # first, load to bytes
    # if return_as == "bytes":
    #     with open(fin, "rb") as f:
    #         alert = f.read()
    # else:
    #     alert = decode_alert(fin, return_as=return_as, **kwargs)
    # return alert


def decode_alert(
    alert_avro: Union[str, Path, bytes],
    return_as: str = 'dict',
    drop_cutouts: bool = False,
    **kwargs
) -> Union[dict, "pd.DataFrame"]:
    """***Depreciated. Use open_alert() instead.***

    Load an alert Avro and return in requested format."""
    LOGGER.warn("Depreciated. Use open_alert() instead.")
    return open_alert(alert_avro, return_as=return_as, drop_cutouts=drop_cutouts, **kwargs)


def open_alert(
    alert: Union[str, Path, bytes],
    return_as: str = 'dict',
    drop_cutouts: bool = False,
    **kwargs
) -> Union[bytes, dict, "pd.DataFrame"]:
    """Load ``alert``, decode it, and return it in the requested format.

    Background: The broker deals with alert data that can be packaged in many different ways.
    For example:

    -   Files in Avro format
    -   Pub/Sub messages -- the message payload is a bytes object with either Avro or json serialization
    -   Cloud Functions further encodes incoming Pub/Sub messages as base64 strings
    -   Any Avro-serialized object may or may not have its schema attached as a header
        (but we must have the schema in order to deserialize it)

    This function adopts a brute-force strategy.
    It does *not* try to inspect ``alert`` and determine its format.
    Instead, it tries repeatedly to load/decode ``alert`` and return it as requested,
    trying at least one method for each input format listed above.
    It catches nearlly all ``Exception``s along the way.
    Set the logger level to DEBUG for a record of the try/excepts.
    If it runs out of methods to try, it raises the error chain instead of returning None.
    (Every private function it calls behaves the same way.)

    Args:
        alert:
            Either the path of Avro file to load, or the bytes encoding the alert.
        return_as:
            Format the alert will be returned in. One of 'bytes', 'dict' or 'df'.
        drop_cutouts:
            Whether to drop or return the image cutouts.
        kwargs:
            Keyword arguments passed to ``_avro_to_dicts()``,
            ``_drop_cutouts()`` and ``alert_dict_to_dataframe()``.
            Note that if ``alert`` is Avro and schemaless you must pass the keyword argument
            ``load_schema`` (see ``_avro_to_dicts()``) with an appropriate value.

    Returns:
        alert data in the requested format
    """
    # load bytes. we do not need this to load a dict.
    if return_as == "bytes":
        return _alert_to_bytes(alert)

    # load dict. we need this to load a dataframe.
    try:
        alert_dicts = _avro_to_dicts(alert, kwargs.get("load_schema"))

    except Exception:
        # we only expect avro or json, so let an exception raise
        alert_dicts = _json_to_dicts(alert)

    # we expect alerts to have exactly one dict in the list, else raise exception
    alert_dict = alert_dicts[0]

    # now we have the alert loaded as a dict
    # from here on, we're just getting it into the return_as format
    # so, no try/excepts
    # if we can't do it, the user needs to either
    # choose different options or extend the function

    if return_as == "dict":
        if drop_cutouts:
            return _drop_cutouts(alert_dict, kwargs.get("schema_map"))
        else:
            return alert_dict

    # load dataframe
    elif return_as == "df":
        return alert_dict_to_dataframe(alert_dict, kwargs.get("schema_map"))

    else:
        raise ValueError("Unknown value recieved for `return_as`.")


def _alert_to_bytes(alert: Union[str, Path, bytes]):
    """Read and return the bytes in ``alert`` (assumed to point to a file)."""
    excepts = []
    # assume alert points to a file
    try:
        with open(alert, "rb") as f:
            return f.read()

    except Exception as e:
        excepts.append(e)
        LOGGER.debug(f"tried: open(alert, 'rb'). caught error: {e}")

        # maybe alert is already a bytes object
        if isinstance(alert, bytes):
            return alert

        else:
            raise e


def _avro_to_dicts(avroin: Union[str, Path, bytes], load_schema: Union[bool, str, None] = None) -> dict:
    """Convert an Avro-serialized object to a dictionary.

    Args:
        avroin:
            An Avro-serialized bytes-like object, or the path to an Avro file.

        load_schema:
            If True or str, ``avroin`` is assumed to be schemaless
            (as in ELAsTiCC and Rubin alerts)
            and will be deserialized using a schema from the avro_schemas directory.
            If True, all schemas in that directory will be tried.
            If str, it should be the filename of the specific schema to be used.
            If None or False, the Avro schema is assumed to be attached to ``avroin``
            (as in ZTF alerts).

    Returns:
        List[dict]:
            ``avroin`` as a list of dictionaries.
    """
    # define two helper functions to call the fastavro reader
    def _read(fin, load_schema):
        # no try/except. load_schema must be properly defined.
        if not load_schema:
            return [r for r in fastavro.reader(fin)]
        else:
            return _read_schemaless(fin, load_schema)

    def _read_schemaless(fin, load_schema):
        schemas = load_all_schemas()
        if isinstance(load_schema, str):
            # a specific schema was requested so drop everything else
            schemas = {load_schema: schemas.get(load_schema)}

        excepts = []
        for key, val in schemas.items():
            try:
                # wrap the dict in a list to match output of _avro_reader
                return [fastavro.schemaless_reader(fin, val)]
            except Exception as e:
                excepts.append(e)
                LOGGER.debug(f"tried: schemaless_reader(fin, {key}). caught error: {e}")

        # if we get here, raise an error instead of returning None
        raise excepts[0]

    excepts = []

    # assume avroin is bytes
    try:
        with BytesIO(avroin) as fin:
            list_of_dicts = _read(fin, load_schema)

    except Exception as e:
        excepts.append(e)
        LOGGER.debug(f"tried: BytesIO(avroin). caught error: {e}")

        try:
            # cloud fncs adds a base64 encoding. undo it
            with BytesIO(b64decode(avroin)) as fin:
                list_of_dicts = _read(fin, load_schema)

        except Exception as e:
            excepts.append(e)
            LOGGER.debug(f"tried: BytesIO(base64.b64decode(avroin). caught error: {e}")

            # maybe avroin is a local path
            try:
                with open(avroin, 'rb') as fin:
                    list_of_dicts = _read(fin, load_schema)

            except Exception as e:
                # unknown format
                excepts.append(e)
                LOGGER.debug(f"tried: open(avroin, 'rb'). caught error: {e}")
                raise excepts[0]

    return list_of_dicts


def _json_to_dicts(jsonin: str):
    """Convert an json-serialized object to a dictionary.

    Args:
        jsonin:
            A json-serialized string.

    Returns:
        List[dict]:
            ``avroin`` as a list of dictionaries.
    """
    excepts = []
    try:
        # wrap single dict in list for consistency with _avro_to_dicts()
        list_dict = [json.loads(jsonin)]

    except Exception as e:
        LOGGER.debug(f"tried: json.loads(jsonin). caught error:{e}")
        excepts.append(e)

        try:
            # cloud fncs adds a base64 encoding. undo it
            list_dict = [json.loads(b64decode(jsonin))]

        except Exception as e:
            LOGGER.debug(f"tried: json.loads(base64.b64decode(jsonin)). caught error:{e}")
            excepts.append(e)

            # unknown format
            raise e

    return list_dict


def alert_dict_to_dataframe(alert_dict: dict, schema_map: dict) -> "pd.DataFrame":
    """ Packages an alert into a dataframe.
    Adapted from: https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    import pandas as pd
    src_df = pd.DataFrame(alert_dict[schema_map['source']], index=[0])
    prvs_df = pd.DataFrame(alert_dict[schema_map['prvSources']])
    df = pd.concat([src_df, prvs_df], ignore_index=True)

    # attach some metadata. note this may not be preserved after all operations
    # https://stackoverflow.com/questions/14688306/adding-meta-information-metadata-to-pandas-dataframe
    # make sure this does not overwrite existing columns
    ids = AlertIds(schema_map, alert_dict=alert_dict)
    if "objectId" not in df.keys():
        df.objectId = ids.objectId
    if "sourceId" not in df.keys():
        df.sourceId = ids.sourceId

    return df


def alert_lite_to_dataframe(alert_dict: dict) -> "pd.DataFrame":
    """Package an alert into a dataframe.

    Adapted from: https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    import pandas as pd
    src_df = pd.DataFrame(alert_dict['source'], index=[0])
    prvs_df = pd.DataFrame(alert_dict['prvSources'])
    return pd.concat([src_df, prvs_df], ignore_index=True)


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


def ztf_fid_names() -> dict:
    """Return a dictionary mapping the ZTF `fid` (filter ID) to the common name."""
    return {1: "g", 2: "r", 3: "i"}
