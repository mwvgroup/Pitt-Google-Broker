#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""``utils`` contains functions that facilitate interacting with
Pitt-Google Broker's data and services.
"""

from fastavro import reader
from io import BytesIO
import pandas as pd
from pandas import DataFrame
from typing import Union


def ztf_fid_names() -> dict:
    """Return a dictionary mapping the ZTF `fid` (filter ID) to the common name."""
    return {1: "g", 2: "r", 3: "i"}


# --- Decode alert data --- #
def decode_alert(
    alert_bytes: bytes,
    return_format: str = "dict",
    strip_cutouts: bool = False,
    survey: str = "ztf",
) -> Union[dict, DataFrame]:
    """Decode alert bytes using fastavro and return in requested format.

    Args:
        alert_bytes: a single alert
        return_format: One of "dict" or "df". Format for the returned alert.
        strip_cutouts: Whether to drop the cutouts.
        survey: Which survey generated the alert. Currently only "ztf" is supported.
    """
    assert survey == 'ztf'

    # extract the alert data
    with BytesIO(alert_bytes) as fin:
        alert_dicts = [r for r in reader(fin)]  # list of dicts
    # ZTF alerts are expected to contain one dict in this list
    assert len(alert_dicts) == 1
    alert_dict = alert_dicts[0]

    # drop cutouts if requested
    if strip_cutouts:
        alert_dict = strip_cutouts_ztf(alert_dict)

    # return the alert as the requested type
    if return_format == "dict":
        return alert_dict
    elif return_format == "df":
        return alert_dict_to_dataframe(alert_dict)


def strip_cutouts_ztf(alert_dict: dict) -> dict:
    """Drop the cutouts from the alert dictionary.

    Args:
        alertDict (dict): ZTF alert formated as a dict
    Returns:
        alertStripped (dict): ZTF alert dict with the cutouts (postage stamps) removed
    """
    cutouts = ["cutoutScience", "cutoutTemplate", "cutoutDifference"]
    alert_stripped = {k: v for k, v in alert_dict.items() if k not in cutouts}
    return alert_stripped


def alert_dict_to_dataframe(alert_dict: dict) -> DataFrame:
    """Package a ZTF alert dictionary into a dataframe.

    Adapted from:
    https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    dfc = pd.DataFrame(alert_dict["candidate"], index=[0])
    df_prv = pd.DataFrame(alert_dict["prv_candidates"])
    df = pd.concat([dfc, df_prv], ignore_index=True, sort=True)
    df = df[dfc.columns]  # return to original column ordering

    # we'll attach some metadata--note this may not be preserved after all operations
    # https://stackoverflow.com/questions/14688306/adding-meta-information-metadata-to-pandas-dataframe
    df.objectId = alert_dict["objectId"]
    return df
