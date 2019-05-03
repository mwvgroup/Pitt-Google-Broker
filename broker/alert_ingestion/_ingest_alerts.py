#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Parse ANTARES alerts and add them to the project database."""

import logging
from tempfile import TemporaryFile

import fastavro
import numpy as np
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
    """Format a ZTF alert for ingestion into BigQuery tables

    Args:
        alert_packet (dict): A ztf alert packet

    Returns:
        A tuple representing a row in the `alert` table
        A tuple representing a row in the `candidate` table
    """

    schemavsn = alert_packet['schemavsn']
    if schemavsn == '3.2':
        alert_entry = (
            alert_packet['objectId'],
            alert_packet['candid'],
            schemavsn)

        candidate_data = alert_packet['candidate']
        candidate_entry = (
            candidate_data['jd'],
            candidate_data['fid'],
            candidate_data['pid'],
            candidate_data['diffmaglim'],
            candidate_data['pdiffimfilename'],
            candidate_data['programpi'],
            candidate_data['programid'],
            candidate_data['candid'],
            candidate_data['isdiffpos'],
            candidate_data['tblid'],
            candidate_data['nid'],
            candidate_data['rcid'],
            candidate_data['field'],
            candidate_data['xpos'],
            candidate_data['ypos'],
            candidate_data['ra'],
            candidate_data['dec'],
            candidate_data['magpsf'],
            candidate_data['sigmapsf'],
            candidate_data['chipsf'],
            candidate_data['magap'],
            candidate_data['sigmagap'],
            candidate_data['distnr'],
            candidate_data['magnr'],
            candidate_data['sigmagnr'],
            candidate_data['chinr'],
            candidate_data['sharpnr'],
            candidate_data['sky'],
            candidate_data['magdiff'],
            candidate_data['fwhm'],
            candidate_data['classtar'],
            candidate_data['mindtoedge'],
            candidate_data['magfromlim'],
            candidate_data['seeratio'],
            candidate_data['aimage'],
            candidate_data['bimage'],
            candidate_data['aimagerat'],
            candidate_data['bimagerat'],
            candidate_data['elong'],
            candidate_data['nneg'],
            candidate_data['nbad'],
            candidate_data['rb'],
            candidate_data['rbversion'],
            candidate_data['ssdistnr'],
            candidate_data['ssmagnr'],
            candidate_data['ssnamenr'],
            candidate_data['sumrat'],
            candidate_data['magapbig'],
            candidate_data['sigmagapbig'],
            candidate_data['ranr'],
            candidate_data['decnr'],
            candidate_data['ndethist'],
            candidate_data['ncovhist'],
            candidate_data['jdstarthist'],
            candidate_data['jdendhist'],
            candidate_data['scorr'],
            candidate_data['tooflag'],
            candidate_data['objectidps1'],
            candidate_data['sgmag1'],
            candidate_data['srmag1'],
            candidate_data['simag1'],
            candidate_data['szmag1'],
            candidate_data['sgscore1'],
            candidate_data['distpsnr1'],
            candidate_data['objectidps2'],
            candidate_data['sgmag2'],
            candidate_data['srmag2'],
            candidate_data['simag2'],
            candidate_data['szmag2'],
            candidate_data['sgscore2'],
            candidate_data['distpsnr2'],
            candidate_data['objectidps3'],
            candidate_data['sgmag3'],
            candidate_data['srmag3'],
            candidate_data['simag3'],
            candidate_data['szmag3'],
            candidate_data['sgscore3'],
            candidate_data['distpsnr3'],
            candidate_data['nmtchps'],
            candidate_data['rfid'],
            candidate_data['jdstartref'],
            candidate_data['jdendref'],
            candidate_data['nframesref'],
            candidate_data['dsnrms'],
            candidate_data['ssnrms'],
            candidate_data['dsdiff'],
            candidate_data['magzpsci'],
            candidate_data['magzpsciunc'],
            candidate_data['magzpscirms'],
            candidate_data['nmatches'],
            candidate_data['clrcoeff'],
            candidate_data['clrcounc'],
            candidate_data['zpclrcov'],
            candidate_data['zpmed'],
            candidate_data['clrmed'],
            candidate_data['clrrms'],
            candidate_data['neargaia'],
            candidate_data['neargaiabright'],
            candidate_data['maggaia'],
            candidate_data['maggaiabright'],
            candidate_data['exptime'])

    else:
        raise ValueError(f'Unexpected Schema Version: {schemavsn}')

    return alert_entry, candidate_entry


def _parse_alert_vectorized(alert_list):
    """A vectorized version of _parse_alert

    Args:
        alert_list (dict or iterable[dict]): Collection of ZTF alerts
    """

    if isinstance(alert_list, dict):
        parsed_alert = _parse_alert(alert_list)
        return tuple([val] for val in parsed_alert)

    else:
        parsed_alerts = [_parse_alert(alert) for alert in alert_list]
        return np.transpose(parsed_alerts)


def stream_ingest_alerts(client, num_alerts=10):
    """Stream ZTF alerts into BigQuery

    Args:
        client  (Client): A BigQuery client
        num_alerts (int): Maximum alerts to ingest at a time (Default: 10)
    """

    # Get tables to store data
    dataset_ref = client.dataset('ztf_alerts')
    alert_table = client.get_table(dataset_ref.table('alert'))
    candidate_table = client.get_table(dataset_ref.table('candidate'))

    for alert_packet in iter_alerts(num_alerts):
        formatted_packet = _parse_alert_vectorized(alert_packet)

        alert_error = client.insert_rows(alert_table, formatted_packet[0])
        candidate_error = client.insert_rows(
            candidate_table, formatted_packet[1])

        if alert_error or candidate_error:
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
        formatted_alert = _format_alert(alert_packet)

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
