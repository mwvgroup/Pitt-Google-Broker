#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Ingests data from external surveys."""

import pandas as pd
from tqdm import tqdm

from ._orm import SDSS, engine


def ingest_sdss(input_path):
    """Populate the sdss table with data from SDSS DR14

    Args:
        input_path (str): Path of file with SDSS data
    """

    data_as_dicts = []
    input_df = pd.read_csv(input_path, index_col=0)
    generator = enumerate(input_df.iterrows())
    for i, (index, row) in tqdm(generator, total=len(input_df.index)):
        data_as_dicts.append(dict(
            id=index,
            run=row['run'],
            rerun=row['rerun'],
            ra=row['ra'],
            dec=row['dec'],
            u=row['u'],
            g=row['g'],
            r=row['r'],
            i=row['i'],
            z=row['z'],
            u_err=row['Err_u'],
            g_err=row['Err_g'],
            r_err=row['Err_r'],
            i_err=row['Err_i'],
            z_err=row['Err_z'],
        ))

        if not (i + 1) % 1000:
            engine.execute(SDSS.__table__.insert(), data_as_dicts)
            data_as_dicts = []

    else:
        if data_as_dicts:
            engine.execute(SDSS.__table__.insert(), data_as_dicts)
