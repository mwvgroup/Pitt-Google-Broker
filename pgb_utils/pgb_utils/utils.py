#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""``utils`` contains functions that facilitate interacting with
Pitt-Google Broker's data and services.
"""


from astropy.table import Table
import pandas as pd


def ztf_fid_names() -> dict:
    """Return a dictionary mapping the ZTF `fid` (filter ID) to the common name."""
    return {1: "g", 2: "r", 3: "i"}


# --- Work with alert dictionaries
def alert_dict_to_dataframe(alert_dict: dict) -> pd.DataFrame:
    """Package a ZTF alert dictionary into a dataframe.

    Adapted from:
    https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    dfc = pd.DataFrame(alert_dict["candidate"], index=[0])
    df_prv = pd.DataFrame(alert_dict["prv_candidates"])
    df = pd.concat([dfc, df_prv], ignore_index=True, sort=True)
    df = df[dfc.columns]  # return to original column ordering

    # we'll attach some metadata--note this may not be preserved after all operations
    # https://stackoverflow.com/questions/14688306/adding-meta-information-metadata-to-pandas-dataframe
    df.objectId = alert_dict["objectId"]
    return df


def alert_dict_to_table(alert_dict: dict) -> Table:
    """Package a ZTF alert dictionary into an Astopy Table."""
    rows = [alert_dict["candidate"]] + alert_dict["prv_candidates"]
    table = Table(rows=rows)
    table.meta["comments"] = f"ZTF objectId: {alert_dict['objectId']}"
    return table


def _strip_cutouts_ztf(alert_dict: dict) -> dict:
    """Drop the cutouts from the alert dictionary.

    Args:
        alert_dict: ZTF alert formated as a dict
    Returns:
        `alert_data` with the cutouts (postage stamps) removed
    """
    cutouts = ["cutoutScience", "cutoutTemplate", "cutoutDifference"]
    alert_stripped = {k: v for k, v in alert_dict.items() if k not in cutouts}
    return alert_stripped
