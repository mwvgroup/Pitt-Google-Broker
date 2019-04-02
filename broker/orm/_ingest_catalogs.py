#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Ingests data from external surveys."""

import os

import pandas as pd
from tqdm import tqdm

from ._orm import ZTFAlert, ZTFCandidate, engine, upsert
from .. import mock_ztf_stream

sdss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'Skyserver_3e5_stars_mags.csv')


def _ingest_sdss(input_path, if_exists='fail'):
    """Populate the sdss table with data from SDSS DR14

    Default behavior is to append data if 'sdss' table already exists.

    Args:
        input_path (str): Path of file with SDSS data
        if_exists  (str): Behavior if sdss table already exists
            (‘fail’, ‘replace’, ‘append’)
    """

    input_df = pd.read_csv(input_path, index_col=0)
    input_df.rename(index=str,
                    inplace=True,
                    columns={
                        'Err_u': 'u_err',
                        'Err_g': 'g_err',
                        'Err_r': 'r_err',
                        'Err_i': 'i_err',
                        'Err_z': 'z_err'
                    })

    input_df.to_sql('sdss', engine, if_exists=if_exists)


def _ingest_ztf():
    """Ingest a subset of ZTF alert data"""

    num_iters = mock_ztf_stream.get_number_local_alerts()
    for alert_packet in tqdm(mock_ztf_stream.iter_alerts(), total=num_iters):
        alert = dict(
            objectId=alert_packet['objectId'],
            candid=alert_packet['candid'],
            schemavsn=alert_packet['schemavsn']
        )

        # Add foreign keys for relationships
        alert_packet['candidate']['alert_id'] = alert_packet['objectId']
        for d in alert_packet['prv_candidates']:
            d['alert_id'] = alert_packet['objectId']

        candidates = alert_packet['prv_candidates']
        candidates.append(alert_packet['candidate'])

        upsert(ZTFAlert, [alert], [ZTFAlert.objectId])
        upsert(ZTFCandidate, candidates, [ZTFCandidate.jd])


def populate_backend():
    """Populate the backend data base with data from SDSS and ZTF"""

    print('Ingesting SDSS data')
    _ingest_sdss(sdss_path, 'replace')

    print('Checking for local ZTF data')
    if mock_ztf_stream.get_number_local_alerts() == 0:
        print('No data found. Downloading:')
        mock_ztf_stream.download_data()

    print('Ingesting ZTF')
    _ingest_ztf()
