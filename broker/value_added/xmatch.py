#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

""" The ``xmatch`` module provides cross matching services between observed
    targets and external surveys.

    Helpful links:
    https://astroquery.readthedocs.io/en/latest/#using-astroquery
    https://astroquery.readthedocs.io/en/latest/xmatch/xmatch.html#module-astroquery.xmatch
"""

from warnings import warn as _warn

import pandas as pd
from astropy import units as u
from astroquery.xmatch import XMatch

from broker.ztf_archive import _parse_data as psd
from . import redshift as red


def get_xmatches(alert_list, survey='ZTF', sg_thresh=0.5):
    """ Finds alert cross matches in all available catalogs.

    Args:
        alert_list (list): list of alert dicts

        survey      (str): name of survey generating the alerts

        sg_thresh (float): sgscore threshold (maximum) for calling it a galaxy.
                           (sgscore -> 1 implies star)

    Returns:
        Dictionaries of cross match info, formatted for BigQuery.
        One dictionary per unique alert-xmatch pair.
        [ {<column name (str)>: <value (str or float)>} ]

    """
    _warn('The ZTF/Pan-STARRS photo-z calculation needs to be updated. '
          'It uses a random forest model trained on DECaLS data '
          'for photo-z estimation on Pan-STARRS data. '
          '\nThe result should not be trusted!')

    xmatches = []

    for alert in alert_list:

        if survey == 'ZTF':
            # get xmatches included in alert packet
            cand = alert['candidate']
            for s in ['1', '2', '3']:  # for each PS1 source in alert
                sgscore = cand['sgscore'+s]

                # calculate redshift
                zdict = { 'gmag': cand['sgmag'+s],
                          'rmag': cand['srmag'+s],
                          'zmag': cand['simag'+s],  # note this is imag
                          'w1mag': cand['szmag'+s],  # note this is zmag
                          'w2mag': 0.0,
                          'radius': 0.0,
                          'q': 0.0,
                          'p': 0.0
                        }
                # if source is likely a galaxy, calculate redshift
                # else set it to -1
                redshift = red.calcz_rongpuRF(zdict) if sgscore < sg_thresh \
                                                     else -1

                # collect the xmatch data
                xmatches.append({ 'objectId': alert['objectId'],
                                  'xobjId': cand['objectidps'+s],
                                  'xcatalog': 'PS1',
                                  'redshift': redshift,
                                  'dist2d': cand['distpsnr'+s],
                                  'sgscore': sgscore
                                })

    return xmatches


def get_astroquery_xmatches(fcat1='mock_stream/data/alerts_radec.csv',
                            cat2='vizier:II/246/out'):
    """
    Args:
        fcat1 (string): Path to csv file,
                        as written by get_alerts_ra_dec(fout=fcat1).

        cat2  (string): Passed through to XMatch.query().

    Returns:
        An astropy table with columns
          angDist, alert_id, ra, dec, 2MASS, RAJ2000, DEJ2000,
          errHalfMaj, errHalfMin, errPosAng, Jmag, Hmag, Kmag,
          e_Jmag, e_Hmag, e_Kmag, Qfl, Rfl, X, MeasureJD

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
    """ For use with get_astroquery_xmatches().
        Iterates through alerts and writes RA & DEC info to file with format
        compatible with astroquery.xmatch.query().

    Args:
        fout       (str): Path to save file.
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
