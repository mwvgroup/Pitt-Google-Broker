#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``filters`` module contains functions for filtering ZTF alerts.

Usage Example
-------------

.. code-block:: python
   :linenos:

   # the Beam pipeline can contain a `Filter` transform like the following:
   beam.Filter(is_extragalactic_transient)


Module Documentation
--------------------
"""

import numpy as np
import pandas as pd
import astropy.units as u


def is_extragalactic_transient(alert):
    """ Checks whether alert is likely to be an extragalactic transient.
    Most of this was taken from
    https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb

    Args:
        alert (dict): dictionary of alert data from ZTF

    Returns:
        is_transient (bool): whether alert is likely to be an extragalactic transient.
    """

    dflc = _is_transient_make_dataframe(alert)
    candidate = dflc.loc[0]

    is_positive_sub = candidate['isdiffpos'] == 't'

    if (candidate['distpsnr1'] is None) or (candidate['distpsnr1'] > 1.5):  # arcsec
        no_pointsource_counterpart = True
            # closest candidate == star < 1.5 arcsec away -> candidate probably star
            # closet candidate == star > 1.5 arcsec away
    else:
        if candidate['sgscore1'] < 0.5:
            no_pointsource_counterpart = True
        else:
            no_pointsource_counterpart = False

    where_detected = (dflc['isdiffpos'] == 't')
    if np.sum(where_detected) >= 2:
        detection_times = dflc.loc[where_detected,'jd'].values
        dt = np.diff(detection_times)
        not_moving = np.max(dt) >= (30*u.minute).to(u.day).value
    else:
        not_moving = False

    no_ssobject = (candidate['ssdistnr'] is None) or (candidate['ssdistnr'] < 0) or (candidate['ssdistnr'] > 5)
    # candidate['ssdistnr'] == -999 is another encoding of None

    return is_positive_sub and no_pointsource_counterpart and not_moving and no_ssobject

def _is_transient_make_dataframe(alert):
    """ Packages an alert into a dataframe.
    Taken from https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    dfc = pd.DataFrame(alert['candidate'], index=[0])
    df_prv = pd.DataFrame(alert['prv_candidates'])
    dflc = pd.concat([dfc,df_prv], ignore_index=True)

    # we'll attach some metadata--not this may not be preserved after all operations
    # https://stackoverflow.com/questions/14688306/adding-meta-information-metadata-to-pandas-dataframe
    dflc.objectId = alert['objectId']
    dflc.candid = alert['candid']
    return dflc
