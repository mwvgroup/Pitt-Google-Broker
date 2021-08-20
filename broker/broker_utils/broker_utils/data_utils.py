#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``data_utils`` module contains common functions used to manipulate
survey and broker data.
"""

from astropy.time import Time
import fastavro
from io import BytesIO
import json
import numpy as np
import pandas as pd
from typing import Optional, Tuple, Union


def decode_alert(
    alert_avro: Union[str, bytes],
    return_as: str = 'dict',
    schema_map: Optional[dict] = None,
) -> Union[dict, pd.DataFrame]:
    """Load an alert Avro and return in requested format.

    Wraps `alert_avro_to_dict()` and `alert_dict_to_dataframe()`.

    Args:
        alert_avro:   Either the path of Avro file to load, or
            the bytes encoding the Avro-formated alert.
        return_as: Format the alert will be returned in.
        schema_map: Mapping between survey schema and broker's generic schema.
            Required if `return_as == 'df'`.

    Returns:
        alert packet in requested format
    """
    alert_dict = alert_avro_to_dict(alert_avro)

    if return_as == "dict":
        return alert_dict
    elif return_as == "df":
        return alert_dict_to_dataframe(alert_dict, schema_map)
    else:
        raise ValueError("`return_as` must be one of 'dict' or 'df'.")


def alert_avro_to_dict(alert_avro: Union[str, bytes]) -> dict:
    """Load an alert Avro to a dictionary.

    Args:
        alert_avro:   Either the path of Avro file to load, or
            the bytes encoding the Avro-formated alert.

    Returns:
        alert as a dict
    """
    if type(alert_avro) == str:
        with open(alert_avro, 'rb') as fin:
            alert_list = [r for r in fastavro.reader(fin)]  # list of dicts
    elif type(alert_avro) == bytes:
        try:
            with BytesIO(alert_avro) as fin:
                alert_list = [r for r in fastavro.reader(fin)]  # list of dicts
        except ValueError:
            try:
                # this function is mis-named because here we accept json encoding.
                # consider re-encoding alert packets using original Avro format
                # throughout broker to give users a consistent end-product.
                # then this except block will be unnecessary.
                alert_list = [json.loads(alert_avro.decode("UTF-8"))]  # list of dicts
            except ValueError:
                msg = (
                    "alert_avro is a bytes object, but does not seem to be either "
                    "json or Avro encoded. Cannot decode."
                )
                raise ValueError(msg)
    else:
        msg = (
            "Unable to open alert_avro. "
            "It must be either the path to a valid Avro file as a string, "
            "or bytes encoding an Avro-formated alert."
        )
        raise ValueError(msg)

    # we expect the list to contain exactly 1 entry
    if len(alert_list) == 0:
        raise ValueError('The alert Avro contains 0 valid entries.')
    if len(alert_list) > 1:
        raise ValueError('The alert Avro contains >1 entry.')

    alert_dict = alert_list[0]
    return alert_dict

def alert_dict_to_dataframe(alert_dict: dict, schema_map: dict) -> pd.DataFrame:
    """ Packages an alert into a dataframe.
    Adapted from: https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    if type(schema_map) != dict:
        raise ValueError("`schema_map` is not a valid dictionary.")

    dfc = pd.DataFrame(alert_dict[schema_map['source']], index=[0])
    df_prv = pd.DataFrame(alert_dict[schema_map['prvSources']])
    dflc = pd.concat([dfc,df_prv], ignore_index=True)

    # attach some metadata. note this may not be preserved after all operations
    # https://stackoverflow.com/questions/14688306/adding-meta-information-metadata-to-pandas-dataframe
    dflc.objectId = alert_dict[schema_map['objectId']]
    # make sure we haven't onboarded a new survey that has a field named "sourceId"
    assert 'sourceId' not in dflc.keys()
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
