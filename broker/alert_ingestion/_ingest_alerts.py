#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Parse ANTARES alerts and add them to the project database."""

import logging
from tempfile import TemporaryFile

import fastavro
from google.cloud import bigquery, logging as gcp_logging

from ..ztf_archive import iter_alerts

# Connect to GCP
logging_client = gcp_logging.Client()
bq_client = bigquery.Client()
dataset_ref = bq_client.dataset('ztf_alerts')

# Configure logging
handler = logging_client.get_default_handler()
str_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handler.setFormatter(logging.Formatter(str_format))

log = logging.Logger('alert_ingestion')
log.setLevel(logging.INFO)
log.addHandler(handler)


def _format_alert_for_ingestion(alert_packet):
    schemavsn = alert_packet['schemavsn']
    if schemavsn != '3.2':
        log.error(f'Unexpected Schema Version: {schemavsn}')

    data_entry = dict()
    data_entry['alert'] = [
        {'object_id': alert_packet['objectId'],
         'cand_id': alert_packet['candid'],
         'schema_vsn': schemavsn}
    ]

    return data_entry


def ingest_alerts(client=None):
    # Configure batch loading
    job_config = bigquery.LoadJobConfig()
    job_config.source_format = bigquery.SourceFormat.AVRO
    job_config.skip_leading_rows = 1
    job_config.autodetect = True

    table_ref = dataset_ref.table('alert')
    for alert_packet in iter_alerts():
        formatted_alert = _format_alert_for_ingestion(alert_packet)

        with TemporaryFile() as source_file:
            fastavro.writer(source_file, formatted_alert['alert'])

            # API request
            job = client.load_table_from_file(
                source_file,
                table_ref,
                location="US",
                job_config=job_config,
            )

        job.result()  # Wait for table load to complete.
