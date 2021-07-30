#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``data_utils`` module contains common functions used to manipulate
survey and broker data.
"""

from astropy.time import Time
import fastavro
import numpy as np
import pandas as pd
from typing import Tuple


def alert_avro_to_dict(filename: str) -> dict:
    """Load an alert Avro file to a dictionary.

    Args:
        filename:   Path of Avro file to load.
    """
    with open(filename, 'rb') as fin:
        alert_list = [r for r in fastavro.reader(fin)]  # list of dicts

    # we expect the list to contain exactly 1 entry
    if len(alert_list)==0:
        raise ValueError('The alert Avro contains 0 valid entries.')
    if len(alert_list)>1:
        raise ValueError('The alert Avro contains >1 entry.')

    alert_dict = alert_list[0]
    return alert_dict

def alert_dict_to_dataframe(alert_dict: dict, schema_map: dict) -> pd.DataFrame:
    """ Packages an alert into a dataframe.
    Adapted from: https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    dfc = pd.DataFrame(alert_dict[schema_map['source']], index=[0])
    df_prv = pd.DataFrame(alert_dict[schema_map['prvSources']])
    dflc = pd.concat([dfc,df_prv], ignore_index=True)

    # we'll attach some metadata--not this may not be preserved after all operations
    # https://stackoverflow.com/questions/14688306/adding-meta-information-metadata-to-pandas-dataframe
    dflc.objectId = alert_dict[schema_map['objectId']]
    dflc.sourceId = alert_dict[schema_map['sourceId']]
    return dflc

def mag_to_flux(mag: float, zeropoint: float, magerr: float) -> Tuple[float,float]:
    """ Converts an AB magnitude and its error to fluxes.
    """
    flux = 10 ** ((zeropoint - mag) / 2.5)
    fluxerr = flux * magerr * np.log(10 / 2.5)
    return flux, fluxerr

def jd_to_mjd(jd: float) -> float:
    """ Converts Julian Date to modified Julian Date.
    """
    return Time(jd, format='jd').mjd
