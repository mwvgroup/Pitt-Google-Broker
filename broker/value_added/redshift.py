#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

""" The ``reshift`` module estimates and returns the redshift of a given
    astronomical object.

"""

import numpy as np
from sklearn.externals import joblib
from pathlib import Path

RFpath = Path(__file__).resolve().parent / 'regrf_20181008_0.pkl'


def calcz_rongpuRF(data):
    """ Calculates redshift using a single pre-trained random forest model
        from Rongpu Zhou (2019, in prep.).

    Args:
        data  (dict): keys: 'gmag', 'rmag', 'zmag', 'w1mag', 'w2mag',
                            'radius', 'q', 'p'

    Returns:
        redshift of galaxy associated with data.
    """

    # Load single pre-trained tree
    regrf = joblib.load(RFpath)

    g = data['gmag']
    r = data['rmag']
    z = data['zmag']
    w1 = data['w1mag']
    w2 = data['w1mag']
    radius = data['radius']
    q = data['q']
    p = data['p']

    data1 = np.column_stack((g-r, r-z, z-w1, w1-w2, r, radius, q, p))
    z_phot = regrf.predict(data1)

    return z_phot[0]
