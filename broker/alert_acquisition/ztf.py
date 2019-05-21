#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Retrieve and parse alerts from ZTF.

This module is currently in progress and relies on the ZTF Public Alerts
Archive, not the live ZTF stream.
"""

import logging
import os

import pandas as pd

from ..ztf_archive import iter_alerts

if 'RTD_BUILD' not in os.environ:
    from google.cloud import error_reporting, logging as gcp_logging

    # Connect to GCP
    logging_client = gcp_logging.Client()
    error_client = error_reporting.Client()

    # Configure logging
    handler = logging_client.get_default_handler()
    log = logging.Logger('ztf_acquisition')
    log.setLevel(logging.INFO)
    log.addHandler(handler)

alert_iterable = iter_alerts(10, raw=False)


def get_alerts(num_alert):
    """Get alerts from the ZTF alert stream

    Todo: Function currently returns 10 alerts from the ZTF archive module
        - Get data from the alert stream instead of the ZTF Archive
        - Actually return ``num_alert`` number of alerts
        - Return bytes instead of dicts

    Args:
        num_alert (int): The number of alerts to fetch

    Returns:
        A list of alert data as bytes objects
    """

    return next(alert_iterable)


def parse_alert(alert_bytes):
    """Convert alert data from a bytes object to a dict

    Todo: Function currently returns the input argument
        - Convert bytes object to dict

    Args:
        alert_bytes (bytes): Alert data from ZTF

    Returns:
        The same alert data as a dictionary object
    """

    return alert_bytes


def _map_to_schema(alert_packet):
    """Map a single ZTF alert to the data model used by the BigQuery backend

    Args:
        alert_packet (dict): A ztf alert packet

    Returns:
        A dictionary representing a row in the BigQuery ``ztf.alert`` table
    """

    schemavsn = alert_packet['schemavsn']
    if schemavsn == '3.2':
        alert_entry = alert_packet['candidate']

    else:
        err_msg = f'Unexpected Schema Version: {schemavsn}'
        log.error(err_msg)
        error_client.report(err_msg)
        raise ValueError(err_msg)

    return alert_entry


def map_to_schema(alert_list):
    """Map ZTF alert metadata to the data model used by the BigQuery backend

    Args:
        alert_list (iterable[dict]): Iterable of ZTF alert packets

    Returns:
        A Dataframe with data for the BigQuery ``ztf.alert`` table
    """

    alert_table = []
    for alert in alert_list:
        alert_data = _map_to_schema(alert)
        alert_table.append(alert_data)

    return pd.DataFrame(alert_table)
