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
    if schemavsn == '3.2':
        alert_entry = (
            alert_packet['objectId'],
            alert_packet['candid'],
            schemavsn)

        candidate_entry = (
            alert_packet['jd'],
            alert_packet['fid'],
            alert_packet['pid'],
            alert_packet['diffmaglim'],
            alert_packet['pdiffimfilename'],
            alert_packet['programpi'],
            alert_packet['programid'],
            alert_packet['candid'],
            alert_packet['isdiffpos'],
            alert_packet['tblid'],
            alert_packet['nid'],
            alert_packet['rcid'],
            alert_packet['field'],
            alert_packet['xpos'],
            alert_packet['ypos'],
            alert_packet['ra'],
            alert_packet['dec'],
            alert_packet['magpsf'],
            alert_packet['sigmapsf'],
            alert_packet['chipsf'],
            alert_packet['magap'],
            alert_packet['sigmagap'],
            alert_packet['distnr'],
            alert_packet['magnr'],
            alert_packet['sigmagnr'],
            alert_packet['chinr'],
            alert_packet['sharpnr'],
            alert_packet['sky'],
            alert_packet['magdiff'],
            alert_packet['fwhm'],
            alert_packet['classtar'],
            alert_packet['mindtoedge'],
            alert_packet['magfromlim'],
            alert_packet['seeratio'],
            alert_packet['aimage'],
            alert_packet['bimage'],
            alert_packet['aimagerat'],
            alert_packet['bimagerat'],
            alert_packet['elong'],
            alert_packet['nneg'],
            alert_packet['nbad'],
            alert_packet['rb'],
            alert_packet['rbversion'],
            alert_packet['ssdistnr'],
            alert_packet['ssmagnr'],
            alert_packet['ssnamenr'],
            alert_packet['sumrat'],
            alert_packet['magapbig'],
            alert_packet['sigmagapbig'],
            alert_packet['ranr'],
            alert_packet['decnr'],
            alert_packet['ndethist'],
            alert_packet['ncovhist'],
            alert_packet['jdstarthist'],
            alert_packet['jdendhist'],
            alert_packet['scorr'],
            alert_packet['tooflag'],
            alert_packet['objectidps1'],
            alert_packet['sgmag1'],
            alert_packet['srmag1'],
            alert_packet['simag1'],
            alert_packet['szmag1'],
            alert_packet['sgscore1'],
            alert_packet['distpsnr1'],
            alert_packet['objectidps2'],
            alert_packet['sgmag2'],
            alert_packet['srmag2'],
            alert_packet['simag2'],
            alert_packet['szmag2'],
            alert_packet['sgscore2'],
            alert_packet['distpsnr2'],
            alert_packet['objectidps3'],
            alert_packet['sgmag3'],
            alert_packet['srmag3'],
            alert_packet['simag3'],
            alert_packet['szmag3'],
            alert_packet['sgscore3'],
            alert_packet['distpsnr3'],
            alert_packet['nmtchps'],
            alert_packet['rfid'],
            alert_packet['jdstartref'],
            alert_packet['jdendref'],
            alert_packet['nframesref'],
            alert_packet['dsnrms'],
            alert_packet['ssnrms'],
            alert_packet['dsdiff'],
            alert_packet['magzpsci'],
            alert_packet['magzpsciunc'],
            alert_packet['magzpscirms'],
            alert_packet['nmatches'],
            alert_packet['clrcoeff'],
            alert_packet['clrcounc'],
            alert_packet['zpclrcov'],
            alert_packet['zpmed'],
            alert_packet['clrmed'],
            alert_packet['clrrms'],
            alert_packet['neargaia'],
            alert_packet['neargaiabright'],
            alert_packet['maggaia'],
            alert_packet['maggaiabright'],
            alert_packet['exptime'])

    else:
        raise ValueError(f'Unexpected Schema Version: {schemavsn}')

    return alert_entry, candidate_entry


def stream_ingest_alerts(client=None):
    """Stream individual alerts into BigQuery"""

    # Todo: Once connected to kafka, query / insert multiple alerts at once
    alert_table = bq_client.get_table(dataset_ref.table('alert'))
    candidate_table = bq_client.get_table(dataset_ref.table('candidate'))
    for alert_packet in iter_alerts():
        formatted_packet = _format_alert_for_ingestion(alert_packet)
        alert_error = bq_client.insert_rows(alert_table, [formatted_packet[0]])
        cand_error = bq_client.insert_rows(candidate_table, [formatted_packet[1]])

        if alert_error or cand_error:
            raise RuntimeError(
                f'Failed to stream insert alert: {formatted_packet}')


def batch_ingest_alerts(client=None):
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
