#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Retrieve and parse alerts from ZTF.

This module is currently in progress and relies on the ZTF Public Alerts
Archive, not the live ZTF astream.
"""

import logging
import os

import pandas as pd

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


def _parse_alert(alert_packet):
    """Map ZTF alert to the data model used by the BigQuery backend

    Args:
        alert_packet (dict): A ztf alert packet

    Returns:
        A dictionary representing a row in the BigQuery `alert` table
        A dictionary representing a row in the BigQuery `candidate` table
    """

    schemavsn = alert_packet['schemavsn']
    if schemavsn == '3.2':
        alert_entry = dict(
            objectId=alert_packet['objectId'],
            candID=alert_packet['candid'],
            schemaVSN=schemavsn)

        candidate_entry = alert_packet['candidate']

    else:
        err_msg = f'Unexpected Schema Version: {schemavsn}'
        log.error(err_msg)
        error_client.report(err_msg)
        raise ValueError(err_msg)

    return alert_entry, candidate_entry


def parse_alerts(alert_list):
    """Map ZTF alert to the data model used by the BigQuery backend

    Args:
        alert_list (iterable[dict]): Iterable of ZTF alert packets

    Returns:
        A Dataframe with data for the BigQuery ``alert`` table
        A Dataframe with data for the BigQuery ``candidate`` table
    """

    alert_table, candidate_table = [], []
    for alert in alert_list:
        alert_data, candidate_data = _parse_alert(alert)
        alert_table.append(alert_data)
        candidate_table.append(candidate_data)

    return pd.DataFrame(alert_table), pd.DataFrame(candidate_table)
