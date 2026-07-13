#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module produces "value-added" lite alerts containing temperature on the DIA point source fluxes and science fluxes."""

import os
from typing import Dict
import numpy as np
import pandas as pd
import flask
import pittgoogle
from google.cloud import logging

import heapq
import mwdust
# Initialize the 2D SFD dust map
sfdMap = mwdust.SFD(filter='E(B-V)')
from astropy.coordinates import SkyCoord
from astropy.stats import sigma_clip
# from astropy.time import Time
from itertools import compress
# from itertools import repeat
from scipy.optimize import curve_fit

# [FIXME] Make this helpful or else delete it.
# Connect the python logger to the google cloud logger.
# By default, this captures INFO level and above.
# pittgoogle uses the python logger.
# We don't currently use the python logger directly in this script, but we could.
logging.Client().setup_logging()

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# Variables for incoming data
# A url route is used in setup.sh when the trigger subscription is created.
# It is possible to define multiple routes in a single module and trigger them using different subscriptions.
ROUTE_RUN = "/"  # HTTP route that will trigger run(). Must match deploy.sh

# Variables for outgoing data
HTTP_204 = 204  # HTTP code: Success
HTTP_400 = 400  # HTTP code: Bad Request

# GCP resources used in this module
TOPIC = pittgoogle.Topic.from_cloud(
    "variability", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)

app = flask.Flask(__name__)

# The LSST bands, wavelength in microns from https://lsstcam.lsst.io/
WL = {'u': 0.3724, 'g': 0.4807, 'r': 0.6221, 'i': 0.7559, 'z': 0.8680, 'y': 0.9753}

# These colour corrections are from Table 6 of 
# Schlafly and Finkbeiner https://iopscience.iop.org/article/10.1088/0004-637X/737/2/103 with RV=3.1
# Multiplier for EBV for magnitude correction
EXTCOEF = {'u': 4.145, 'g': 3.237, 'r': 2.273, 'i': 1.684, 'z': 1.323, 'y': 1.088}


@app.route(ROUTE_RUN, methods=["POST"])
def run():
    """Produces a value-added alert stream (${survey}-temperature). Messages in this stream retain fields
    from the original alert-lite packet.

    This module is intended to be deployed as a Cloud Run service. It will operate as an HTTP endpoint
    triggered by Pub/Sub messages. This function will be called once for every message sent to this route.
    It should accept the incoming HTTP request and return a response.

    Returns
    -------
    response : tuple(str, int)
        Tuple containing the response body (string) and HTTP status code (int). Flask will convert the
        tuple into a proper HTTP response. Note that the response is a status message for the web server.
    """
    # extract the envelope from the request that triggered the endpoint
    # this contains a single Pub/Sub message with the alert to be processed
    envelope = flask.request.get_json()
    try:
        alert_lite = pittgoogle.Alert.from_cloud_run(envelope, schema_name="default")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    ra = alert_lite.dict['alert_lite'].get('diaSource').get('ra')
    dec = alert_lite.dict['alert_lite'].get('diaSource').get('dec')
    c = SkyCoord(ra, dec, unit="deg", frame='icrs')

    # The third argument is a distance
    # It seems to have no affect since SFD is 2D not 3D but it is a required field
    # I pass a large distance (100 kpc) in case it matters at some locations
    ebv = sfdMap(c.galactic.l.deg, c.galactic.b.deg, 100)[0]

    sourceList = _create_dataframe(alert_lite.dict['alert_lite'])

    # select only the last window days
    maxMJD = alert_lite.dict['alert_lite'].get('diaSource').get('midpointMjdTai')
    window = 3
    minMJD = maxMJD - window
    sourceList = sourceList[sourceList['midpointMjdTai'] >= minMJD]
    sourceList.reset_index(drop=True, inplace=True)

    temperature = {
        'differenceFit': _calculateFitTemp(sourceList.rename(columns={'psfFlux': 'flux', 'psfFluxErr': 'fluxErr'}), ebv),
        'scienceFit': _calculateFitTemp(sourceList.rename(columns={'scienceFlux': 'flux', 'scienceFluxErr': 'fluxErr'}), ebv)
    }

    TOPIC.publish(
        pittgoogle.Alert.from_dict(
            {'alert_lite': alert_lite.dict['alert_lite'],
             'difference_temperature': temperature['differenceFit']['temp'],
             'difference_temperature_error': temperature['differenceFit']['tempErr'],
             'science_temperature': temperature['scienceFit']['temp'],
             'science_temperature_error': temperature['scienceFit']['tempErr']},
            attributes={**alert_lite.attributes, **temperature['differenceFit'],  **temperature['scienceFit']},
            schema_name="default",
        )
    )

    return "", HTTP_204


def _create_dataframe(alert_lite_dict: dict) -> pd.DataFrame:
    """Create a DataFrame object from the alert lite dictionary."""

    required_cols = [
        'psfFlux',
        'psfFluxErr',
        'scienceFlux',
        'scienceFluxErr',
        'midpointMjdTai',
        'band'
    ]

    # extract fields and create filtered DataFrames
    # combined current source with previous sources and forced sources
    sources = list(heapq.merge((alert_lite_dict.get('prvDiaSources') + [alert_lite_dict.get('diaSource')] or []),
                                alert_lite_dict.get('prvDiaForcedSources') or [],
                                key = lambda source: source['midpointMjdTai']))
    sources_df = pd.DataFrame(_filter_columns(sources, required_cols))

    return sources_df


def _filter_columns(field_list, required_cols):
    """Extract only relevant columns if they exist."""

    return [
        {k: field.get(k) for k in required_cols if k in field}
        for field in field_list
        if field is not None
    ]

def _calculateFitTemp(sourceList, ebv):
    flux = {key: [] for key in WL}
    fluxErr = {key: [] for key in WL}
    bands = set() # used to make sure enough unique bands are used

    # loop through object list while the mjd is in the desired range
    # while i < len(sourceList) and math.floor(sourceList.midpointMjdTai[i] + mjdOffset) <= mjd + window - 1:
    for i in range(len(sourceList)):
        band = sourceList.band[i]
        bands.add(band)
        flux[band].append(_dustFlux(sourceList.flux[i], band, ebv))
        fluxErr[band].append(_dustFlux(sourceList.fluxErr[i], band, ebv))

    if len(bands) >= 3:
        output = _runFit(flux, fluxErr, bands)
    else:
        output = {'temp': np.nan, 'tempErr': np.nan, 'scale': np.nan, 'scaleErr': np.nan,
              'wavelengths': [], 'fluxs': [], 'fluxErrs': []}

    return output

# Modified from Lasiar Examples
def _scaledBlackbody(wl, T, scale):
    hck = 14.387
    q = np.exp(hck/(wl*T))
    return scale * np.power(wl, -3.0) / (q - 1)

# dustFluxErr would be the same function as dustFlux since the dustFlux is effectively multiplying flux by a constant
def _dustFlux(flux, band, ebv):
    return flux*np.power(10, ebv*EXTCOEF[band]/2.5)

def _weightedMean3Sigma(fluxs, fluxErrs, sqrtAvgCount):
    # get the masked list
    maskedFluxs = sigma_clip(fluxs, sigma=3, cenfunc='median')

    if maskedFluxs.count() == 0:
        return None, None
    
    # an error based on the std and how many points are returned
    error = np.ma.std(maskedFluxs) * (sqrtAvgCount/np.sqrt(maskedFluxs.count()))

    # if std = 0 for example if maskedFluxs only has one element or if all elements are the same
    # use the fluxErrs instead to keep the fit function happy
    error = error if error > 0 else np.average(list(compress(fluxErrs, ~maskedFluxs.mask))) * sqrtAvgCount

    return np.ma.average(maskedFluxs, weights=np.pow(fluxErrs, -2)), error

def _runFit(flux, fluxErr, bands):
    output = {'temp': np.nan, 'tempErr': np.nan, 'scale': np.nan, 'scaleErr': np.nan,
              'wavelengths': [], 'fluxs': [], 'fluxErrs': []}
    
    fluxMean = []
    fluxStd = []
    wavelength = []

    # find a mean value for each filter with measurements excluding points more than 3 sigma from the median
    # and a std modified by a factor of sqrt(average count)/sqrt(count in this filter)
    # this modification should tell the fitting function to pay more attention to filters with more points
    sqrtAvgCount = np.sqrt(np.sum(list(map(len, flux))) / len(bands))
    for band in flux:
        if len(flux[band]) > 0:
            fMean, fStd = _weightedMean3Sigma(flux[band], fluxErr[band], sqrtAvgCount)
            if fMean != None:
                fluxMean.append(fMean)
                fluxStd.append(fStd)
                wavelength.append(WL[band])
    try:
        # fit the black body curve and record the results in addition to the points used in the fit
        fit = curve_fit(_scaledBlackbody, wavelength, fluxMean, [10, 1], bounds=([0, -np.inf], [1000, np.inf]), sigma=fluxStd, absolute_sigma=True)
        output['temp'] = fit[0][0]
        output['scale'] = fit[0][1]
        
        error = np.sqrt(np.diag(fit[1]))
        output['tempErr'] = error[0]
        output['scaleErr'] = error[1]

        output['wavelengths'] = wavelength
        output['fluxs'] = fluxMean
        output['fluxErrs'] = fluxStd
    except:
        # Store nans so that the plotting function still plots the points but skips plotting the line.
        # This is important both so that the points that could not be fitted can be observed and
        # so that the legends line up for both the science and difference versions of the plots.
        output['temp'] = np.nan
        output['scale'] = np.nan
        
        output['tempErr'] = np.nan
        output['scaleErr'] = np.nan

        output['wavelengths'] = wavelength
        output['fluxs'] = fluxMean
        output['fluxErrs'] = fluxStd
        
    return output