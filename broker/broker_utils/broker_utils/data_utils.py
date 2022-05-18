#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``data_utils`` module contains common functions used to manipulate
survey and broker data.
"""

from collections import namedtuple
import datetime
from io import BytesIO
import os
from pathlib import Path
from typing import Union

import fastavro
import json
import numpy as np
import pandas as pd

from .gcp_utils import pull_pubsub
from .schema_maps import get_key, get_value


AlertIds = namedtuple("AlertIds", "objectId sourceId")


def get_alert_ids(schema_map, alert_dict=None, attrs=None):
    if not attrs:
        return AlertIds(
            get_value("objectId", alert_dict, schema_map),
            get_value("sourceId", alert_dict, schema_map),
        )
    else:
        id_keys = get_id_keys(schema_map)
        return AlertIds(
            attrs.get(id_keys.objectId),
            attrs.get(id_keys.sourceId),
        )


def get_id_keys(schema_map):
    return AlertIds(
        get_key("objectId", schema_map),
        get_key("sourceId", schema_map),
    )


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


def test_alert_avro_paths(adir=None, survey=None):
    """Return a generator of paths to Avro files in the directory `adir`."""
    if not adir:
        adir = Path(os.getenv(f"ALERT_DIR_{survey.upper()}"))
    return (p for p in adir.glob('**/*.avro'))


class TestAlert:
    """Functions to work with alerts for testing."""

    def __init__(self, path, schema_map):
        """."""
        self.path = path
        self.schema_map = schema_map
        self.data = dict(
            dict=load_alert(path, 'dict', schema_map=schema_map, drop_cutouts=True),
            bytes=load_alert(path, 'bytes'),
        )

        self.objectId_key = get_key("objectId", schema_map)
        self.sourceId_key = get_key("sourceId", schema_map)
        self.ids = get_alert_ids(schema_map, alert_dict=self.data["dict"])
        # self.objectId = get_value("objectId", self.data["dict"], schema_map)
        # self.sourceId = get_value("sourceId", self.data["dict"], schema_map)

    def create_msg_payload(self, publish_as='json', dummy=None):
        """Create a Pub/Sub message payload."""
        atype = {"json": "dict", "avro": "bytes"}  # alert format

        dummy_results = self.create_dummy_results(dummy)

        payload = dict(alert=self.data[atype[publish_as]], **dummy_results)

        return payload

    def create_dummy_results(self, modules=None):
        """Create dummy results for a pipeline module."""
        dummy_results = dict()

        if modules and "SuperNNova" in modules:
            prob_class1 = np.random.uniform()
            dummy_results["SuperNNova"] = {
                self.objectId_key: self.ids.objectId,
                self.sourceId_key: self.ids.sourceId,
                "prob_class0": 1-prob_class1,
                "prob_class1": prob_class1,
                "predicted_class": round(prob_class1),
            }

        return dummy_results

    def create_msg_attrs(self):
        # create int POSIX timestamps in microseconds
        now = datetime.datetime.now(datetime.timezone.utc)
        tkafka = int(now.timestamp() * 1e6)
        # to convert back: datetime.datetime.fromtimestamp(tkafka / 1e6)
        tingest = int((now + datetime.timedelta(seconds=0.345678)).timestamp() * 1e6)
        attrs = {
            self.objectId_key: str(self.ids.objectId),
            self.sourceId_key: str(self.ids.sourceId),
            "kafka.timestamp": str(tkafka),
            "ingest.timestamp": str(tingest),
        }
        return attrs

    @staticmethod
    def guess_publish_format(topic):
        try:
            topic_name_stub = topic.split('-')[1]
        except IndexError:
            topic_name_stub = topic
        publish_as = "avro" if topic_name_stub == "alerts" else "json"
        return publish_as

    @staticmethod
    def pull_and_compare_ids(subscrip, published_alert_ids, schema_map, max_pulls=5):
        # pull the messages
        pulled_msg_ids, i = [], 0
        while len(pulled_msg_ids) < len(published_alert_ids):
            max_messages = len(published_alert_ids) - len(pulled_msg_ids)
            pulled_msg_ids += TestAlert._pull_and_extract_ids(
                subscrip, max_messages, schema_map
            )
            i += 1
            if i > max_pulls:
                break

        # compare with the input list
        # otype = type(published_alert_ids[0].objectId)
        # stype = type(published_alert_ids[0].sourceId)
        # pmsg_ids = [()]
        diff = set(published_alert_ids).difference(set(pulled_msg_ids))
        success = len(diff) == 0
        if success:
            print(f"Success! The message ids pulled from subscription {subscrip} match the input.")
        else:
            print(f"Something went wrong. The message ids pulled from subscription {subscrip} do not match the input.")

        return pulled_msg_ids

    @staticmethod
    def _pull_and_extract_ids(subscrip, max_messages, schema_map):
        msgs = pull_pubsub(
            subscrip, max_messages=max_messages, msg_only=False
        )
        pulled_msg_ids = [
            get_alert_ids(
                schema_map, attrs=msg.message.attributes
            ) for msg in msgs
        ]
        return pulled_msg_ids
