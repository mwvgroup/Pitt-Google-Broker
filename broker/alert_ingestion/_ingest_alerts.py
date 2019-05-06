#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Parse ZTF alerts and add them to the project database."""

import logging
import os
from tempfile import NamedTemporaryFile

import pandas as pd
import pandavro as pdx
from google.cloud import bigquery, logging as gcp_logging

from ..ztf_archive import iter_alerts

# Connect to GCP
logging_client = gcp_logging.Client()

# Configure logging
handler = logging_client.get_default_handler()
str_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handler.setFormatter(logging.Formatter(str_format))

log = logging.Logger('alert_ingestion')
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
        raise ValueError(f'Unexpected Schema Version: {schemavsn}')

    return alert_entry, candidate_entry


def parse_alerts(alert_list):
    """Map ZTF alert to the data model used by the BigQuery backend

    Alert data WILL NOT be temporarily written to disk.

    Args:
        alert_list (iterable[dict]): Iterable of ZTF alert packets

    Returns:
        A Dataframe with data for the BigQuery `alert` table
        A Dataframe with data for the BigQuery `candidate` table
    """

    alert_table, candidate_table = [], []
    for alert in alert_list:
        alert_data, candidate_data = _parse_alert(alert)
        alert_table.append(alert_data)
        candidate_table.append(candidate_data)

    return pd.DataFrame(alert_table), pd.DataFrame(candidate_table)


def stream_ingest_alerts(num_alerts=10):
    """Ingest ZTF alerts into BigQuery via the streaming interface

    Args:
        num_alerts (int): Maximum alerts to ingest at a time (Default: 10)
    """

    project_id = os.environ['BROKER_PROJ_ID']
    for alert_packets in iter_alerts(num_alerts):
        alert_df, candidate_df = parse_alerts(alert_packets)

        alert_df.to_gbq('alert', project_id, if_exists='append')
        candidate_df.to_gbq('candidate', project_id, if_exists='append')


def batch_ingest_alerts(num_alerts=10):
    """Ingest ZTF alerts into BigQuery via the batch upload interface

    Alert data WILL be temporarily written to disk.

    Args:
        num_alerts (int): Maximum alerts to ingest at a time (Default: 10)
    """

    client = bigquery.Client(os.environ['BROKER_PROJ_ID'])

    # Configure batch loading
    job_config = bigquery.LoadJobConfig()
    job_config.source_format = bigquery.SourceFormat.AVRO

    # Get tables to store data
    dataset_ref = client.dataset('ztf_alerts')
    alert_table_ref = dataset_ref.table('alert')
    candidate_table_ref = dataset_ref.table('candidate')

    for alert_packets in iter_alerts(num_alerts):
        alert_df, candidate_df = parse_alerts(alert_packets)

        for table_ref, data in zip(
                (alert_table_ref, candidate_table_ref),
                (alert_df, candidate_df)):
            with NamedTemporaryFile() as source_file:
                pdx.to_avro(source_file.name, data)

                # API request
                job = client.load_table_from_file(
                    source_file,
                    table_ref,
                    location="US",
                    job_config=job_config,
                )

                job.result()  # Wait for table load to complete.
