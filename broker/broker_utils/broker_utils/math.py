#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``math`` module contains mathematical transforms for survey data."""
from typing import Tuple

from astropy.time import Time
import numpy as np


def mag_to_flux(mag: float, zeropoint: float, magerr: float) -> Tuple[float, float]:
    """Convert an AB magnitude and its error to fluxes."""
    flux = 10 ** ((zeropoint - mag) / 2.5)
    fluxerr = flux * magerr * np.log(10 / 2.5)
    return flux, fluxerr


def jd_to_mjd(jd: float) -> float:
    """Convert Julian Date to modified Julian Date."""
    return Time(jd, format='jd').mjd
