#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Downloads and ingests data from external surveys."""

from astropy.table import Table
from tqdm import tqdm

from ._orm import SDSS, engine


def ingest_sdss(input_path):
    """Populate the sdss table with data from SDSS DR14

    Args:
        input_path (str): Path of file with SDSS data
    """

    input_table = Table.read(input_path)
    data_as_dict = []
    for i, row in enumerate(tqdm(input_table)):
        data_as_dict.append(dict(
            id=row['objid']/1000000,
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
            engine.execute(SDSS.__table__.insert(), data_as_dict)
            data_as_dict = []
    else:
        if data_as_dict:
            engine.execute(SDSS.__table__.insert(), data_as_dict)
