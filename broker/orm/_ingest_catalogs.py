#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Ingests data from external surveys."""

import pandas as pd

from ._orm import engine


def ingest_sdss(input_path, if_exists='append'):
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
