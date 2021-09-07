#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``filters`` module contains functions for filtering ZTF alerts.
Note that filtering functions related to a specific analysis may reside in
the module for that analysis (e.g., see ``salt2_utils.py``).

Usage Example
-------------

.. code-block:: python
   :linenos:

   # the Beam pipeline can contain a `Filter` transform like the following:
   beam.Filter(is_extragalactic_transient)


Module Documentation
--------------------
"""

import astropy.units as u
import numpy as np

from broker_utils import data_utils as bdu


def is_extragalactic_transient(alert, schema_map):
    """ Checks whether alert is likely to be an extragalactic transient.
    Adapted from:
    https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb

    Args:
        alert (dict): dictionary of alert data from ZTF

    Returns:
        is_extragalactic_transient (bool): whether alert is likely to be an extragalactic transient.
    """

    if schema_map['SURVEY'] == 'decat':
        # No straightforward way to translate this ZTF filter for DECAT.
        # DECAT alert does not include whether the subtraction (sci-ref) is
        # positive, nor SExtractor results,
        # and the included xmatch data is significantly different.
        # However, DECAT is a transient survey.
        # Assume the alert should pass the filter:
        is_extragalactic_transient = True

    elif schema_map['SURVEY'] == 'ztf':
        dflc = bdu.alert_dict_to_dataframe(alert, schema_map)
        candidate = dflc.loc[0]

        is_positive_sub = candidate['isdiffpos'] == 't'

        if (candidate['distpsnr1'] is None) or (candidate['distpsnr1'] > 1.5):  # arcsec
            no_pointsource_counterpart = True
            # closest candidate == star < 1.5 arcsec away -> candidate probably star
        else:
            if candidate['sgscore1'] < 0.5:
                no_pointsource_counterpart = True
            else:
                no_pointsource_counterpart = False

        where_detected = (dflc['isdiffpos'] == 't')
        if np.sum(where_detected) >= 2:
            detection_times = dflc.loc[where_detected, 'jd'].values
            dt = np.diff(detection_times)
            not_moving = np.max(dt) >= (30 * u.minute).to(u.day).value
        else:
            not_moving = False

        no_ssobject = (candidate['ssdistnr'] is None) or (candidate['ssdistnr'] < 0) or (candidate['ssdistnr'] > 5)
        # candidate['ssdistnr'] == -999 is another encoding of None

        is_extragalactic_transient = (is_positive_sub and no_pointsource_counterpart and not_moving and no_ssobject)

    return is_extragalactic_transient


def is_pure(alert, schema_map):
    """Adapted from: https://zwickytransientfacility.github.io/ztf-avro-alert/filtering.html

    Quoted from the source:

    ZTF alert streams contain an nearly entirely unfiltered stream of all
    5-sigma (only the most obvious artefacts are rejected). Depending on your
    science case, you may wish to improve the purity of your sample by filtering
    the data on the included attributes.

    Based on tests done at IPAC (F. Masci, priv. comm), the following filter
    delivers a relatively pure sample.
    """
    source = alert[schema_map['source']]

    rb = (source['rb'] >= 0.65)  # RealBogus score

    if schema_map['SURVEY'] == 'decat':
        is_pure = rb

    elif schema_map['SURVEY'] == 'ztf':
        nbad = (source['nbad'] == 0)  # num bad pixels
        fwhm = (source['fwhm'] <= 5)  # Full Width Half Max, SExtractor [pixels]
        elong = (source['elong'] <= 1.2)  # major / minor axis, SExtractor
        magdiff = (abs(source['magdiff']) <= 0.1)  # aperture - psf [mag]
        is_pure = (rb and nbad and fwhm and elong and magdiff)

    return is_pure
