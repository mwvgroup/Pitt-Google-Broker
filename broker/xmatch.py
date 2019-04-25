#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""This module provides cross matching services between observed targets and

Helpful links:
  https://astroquery.readthedocs.io/en/latest/#using-astroquery
  https://astroquery.readthedocs.io/en/latest/xmatch/xmatch.html#module-astroquery.xmatch

Example Usage:
  from mock_stream import xmatch as xm

  # Write a CSV file with RA, DEC:
  fradec = 'mock_stream/data/alerts_radec.csv'
  xm.get_alerts_RA_DEC(fout=fradec)

  Query VizieR for cross matches:
  table = xm.get_xmatches(fcat1=fradec, cat2='vizier:II/246/out')
"""

import pandas as pd
from astropy import units as u
from astroquery.xmatch import XMatch
from .mock_ztf_stream import _parse_data as psd


def get_xmatches(
        fcat1='mock_stream/data/alerts_radec.csv', cat2='vizier:II/246/out'):
    """

    Args:
        fcat1 (string): Path to csv file, as written by get_alerts_ra_dec.
        cat2  (string): Passed through to XMatch.query().

    Returns:
        An astropy table with columns:
            'angDist','alert_id','ra','dec','2MASS','RAJ2000','DEJ2000',
            'errHalfMaj','errHalfMin','errPosAng','Jmag','Hmag','Kmag',
            'e_Jmag','e_Hmag','e_Kmag','Qfl','Rfl','X','MeasureJD'
    """

    with open(fcat1) as ofile:
        table = XMatch.query(
            cat1=ofile,
            cat2=cat2,
            max_distance=5 * u.arcsec,
            colRA1='ra',
            colDec1='dec')

    return table


def get_alerts_ra_dec(fout=None, max_alerts=1000):
    """Iterate through alerts and grab RA, DEC.

    Write data to file with format compatible with astroquery.xmatch.query().

    Args:
        fout    (string): Path to save file.
        max_alerts (int): Max number of alerts to grab data from.
                           <= 0 will return all available.

    Returns:
        None, returns the alert data as a Pandas DataFrame.
    """

    # Grab RA, DEC from each alert
    data_list = []  # list containing alert data dicts
    try:
        for a, alert in enumerate(psd.iter_alerts()):
            # Get the alert
            alert_id = alert['candid']
            alert_data = psd.get_alert_data(alert_id)

            # Save the data
            dat = {'alert_id': alert_id,
                   'ra': alert_data['candidate']['ra'],
                   'dec': alert_data['candidate']['dec']}
            data_list.append(dat)

            if (a > max_alerts) & (a > 0):
                break

    except RuntimeError as re:
        print("No local alert data found. "
              "Please run 'mock_stream.download_data' first.")

        raise re

    # Write to file or return as a DataFrame
    df = pd.DataFrame(data_list)
    if fout is not None:
        df.to_csv(fout, sep=',', columns=['alert_id', 'ra', 'dec'],
                  header=True, index=False)

    else:
        return df

    return None
