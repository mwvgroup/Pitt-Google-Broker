#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Parse ZTF alerts and add them to the project database."""

import logging
import os
from tempfile import NamedTemporaryFile

import pandavro as pdx

if 'RTD_BUILD' not in os.environ:
    from google.cloud import error_reporting, logging as gcp_logging

    # Connect to GCP
    logging_client = gcp_logging.Client()
    error_client = error_reporting.Client()

    # Configure logging
    handler = logging_client.get_default_handler()
    log = logging.Logger('data_upload')
    log.setLevel(logging.INFO)
    log.addHandler(handler)


def _stream_ingest_meta(num_alerts=10, verbose=False):
    """Ingest ZTF alerts into BigQuery via the streaming interface

    Alert data WILL NOT be temporarily written to disk.

    Args:
        num_alerts (int): Maximum alerts to ingest at a time (Default: 10)
        verbose   (bool): Display progress bar for each table (Default: False)
    """

    log.info('Beginning stream ingestion')
    project_id = os.environ['BROKER_PROJ_ID']
    client = bigquery.Client(project_id)

    # Get table IDs
    dataset_ref = client.dataset('ztf_alerts')
    alert_table_ref = dataset_ref.table('alert')
    alert_table_id = f'{alert_table_ref.dataset_id}.{alert_table_ref.table_id}'
    candidate_table_ref = dataset_ref.table('candidate')
    candidate_table_id = \
        f'{candidate_table_ref.dataset_id}.{candidate_table_ref.table_id}'

    for alert_packets in iter_alerts(num_alerts):
        alert_df, candidate_df = parse_alerts(alert_packets)
        alert_df.to_gbq(
            alert_table_id,
            project_id,
            if_exists='append',
            progress_bar=verbose)
        candidate_df.to_gbq(
            candidate_table_id,
            project_id,
            if_exists='append',
            progress_bar=verbose)


def _batch_ingest_alerts(num_alerts=10):
    """Ingest ZTF alerts into BigQuery via the batch upload interface

    Alert data WILL be temporarily written to disk.

    Args:
        num_alerts (int): Maximum alerts to ingest at a time (Default: 10)
    """

    log.info('Beginning batch ingestion.')
    project_id = os.environ['BROKER_PROJ_ID']
    client = bigquery.Client(project_id)

    # Configure batch loading
    log.debug('Configuring batch jobs')
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

                try:
                    # API request
                    log.debug('Launching batch upload job.')
                    job = client.load_table_from_file(
                        source_file,
                        table_ref,
                        location="US",
                        job_config=job_config,
                    )

                except KeyboardInterrupt:
                    job.result()
                    raise


def ingest_alerts(alerts_df):
    pass
