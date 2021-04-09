#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Contains functions used to perform data format conversions for messages in Pitt-Google Broker's Pub/Sub streams.
"""

from io import BytesIO
from fastavro import reader
import pandas as pd


def ztf_alert_data(msg, return_format='dict', strip_cutouts=False):
    """Decode alert bytes using fastavro and return in requested format.
    Args:
        msg (pubsub message): single alert from the 'ztf_alert_data' stream
    """

    # Extract the alert data from msg -> dict
    with BytesIO(msg) as fin:
        alertDicts = [r for r in reader(fin)]  # list of dicts

    # ZTF alerts are expected to contain one dict in this list
    assert (len(alertDicts) == 1)
    alertDict = alertDicts[0]

    if strip_cutouts:
        alertDict = strip_cutouts(alertDict)

    if return_format == 'dict':
        return alertDict
    elif return_format == 'df':
        return pd.DataFrame(alertDict)


def strip_cutouts(alertDict):
    """
    Args:
        alertDict (dict): ZTF alert formated as a dict
    Returns:
        alertStripped (dict): ZTF alert dict with the cutouts (postage stamps) removed
    """
    cutouts = ['cutoutScience', 'cutoutTemplate', 'cutoutDifference']
    alertStripped = {k:v for k, v in alertDict.items() if k not in cutouts}
    return alertStripped
