#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Retrieve and parse alerts from the ZTF."""

import json
import os
from pathlib import Path

import fastavro
import pandas as pd

from ..utils import setup_log
from ..ztf_archive import iter_alerts

if 'RTD_BUILD' not in os.environ:
    from google.cloud import error_reporting

    error_client = error_reporting.Client()
    log = setup_log('ztf_acquisition')

SCHEMA_DIR = Path(__file__).resolve().parent / 'schema'

# Temporary stop gap until the live alert stream is accessible
alert_iterable = None
from warnings import warn

warn('This module is currently in progress and relies on the ZTF Public Alerts'
     'Archive, not the live ZTF stream.')


def get_alerts(num_alert):
    """Fetch alerts from the ZTF alert stream

    Todo:
        Function currently returns alerts from the ZTF archive module.
        Get data from the ZTF Alert Stream instead of the ZTF Archive.

    Args:
        num_alert (int): The number of alerts to fetch

    Returns:
        A list of alert data as dict objects
    """

    global alert_iterable
    if alert_iterable is None:
        alert_iterable = iter_alerts(num_alert, raw=False)

    return next(alert_iterable)


def map_alert_to_schema(alert_packet):
    """Map a single ZTF alert to the data model used by the BigQuery backend

    Args:
        alert_packet (dict): A ztf alert packet

    Returns:
        A dictionary representing a row in the BigQuery ``ztf.alert`` table
        A dictionary representing a row in the BigQuery ``ztf.candidate`` table
    """

    schemavsn = alert_packet['schemavsn']
    if schemavsn == '3.2':
        candidate_data = alert_packet['candidate']

        alert_data = dict(
            objectId=alert_packet['objectId'],
            candID=alert_packet['candid'],
            schemaVSN=schemavsn)

    else:
        err_msg = f'Unexpected Schema Version: {schemavsn}'
        log.error(err_msg)
        error_client.report(err_msg)
        raise ValueError(err_msg)

    return alert_data, candidate_data


def map_alert_list_to_schema(alert_list):
    """Map ZTF alert metadata to the data model used by the BigQuery backend

    Args:
        alert_list (iterable[dict]): Iterable of ZTF alert packets

    Returns:
        A DataFrame with data for the BigQuery ``ztf.alert`` table
        A DataFrame with data for the BigQuery ``ztf.candidate`` table
    """

    alert_table, candidate_table, image_table = [], [], []
    for alert in alert_list:
        alert_data, candidate_data = map_alert_to_schema(alert)
        alert_table.append(alert_data)
        candidate_table.append(candidate_data)
        image_table.append(image_table)

    return pd.DataFrame(alert_table), pd.DataFrame(candidate_table)


def get_schema(schemavsn):
    """Return the avro schema for a given ZTF schema version

    Args:
        schemavsn (str): ZTF schema version (e.g. '3.2')

    Returns:
        The schema as a dictionary
    """

    schema_path = SCHEMA_DIR / f'ztf_{schemavsn}.json'
    if not schema_path.exists():
        raise ValueError(f'No ZTF schema version found matching "{schemavsn}"')

    with open(schema_path, 'r') as ofile:
        return json.load(ofile)


def save_to_avro(data, schemavsn='3.2', path=None, fileobj=None):
    """Save ZTF alert data to an avro file

    Args:
        data    (DataFrame): Alert data to write to file
        schemavsn     (str): ZTF schema version of output file (Default: '3.2')
        path          (str): Output file path
        fileobj (file-like): Output file object
    """

    if not (path or fileobj):
        raise ValueError('Must specify either `path` or `fileobj`.')

    elif path and fileobj:
        raise ValueError('Cannot specify both `path` and `fileobj`.')

    elif path:
        if not path.endswith('.avro'):
            path += '.avro'

        fileobj = open(path, 'wb')

    schema = get_schema(schemavsn)
    fastavro.writer(fileobj, schema, data.to_dict('records'))

    if path:
        fileobj.close()
