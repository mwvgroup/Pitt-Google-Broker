#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module produces "value-added" lite alerts containing StetsonJ statistics on the DIA point source fluxes."""

import os
from typing import Dict, Tuple
import numpy as np
import pandas as pd
import flask
import pittgoogle
from google.cloud import logging

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


@app.route(ROUTE_RUN, methods=["POST"])
def run():
    """Produces a value-added alert stream (${survey}-variability) containing StetsonJ statistics on the DIA point
    source fluxes. Messages in this stream retain fields from the original alert-lite packet.

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

    stetsonj_stats = _calculate_stetsonJ_statistics(alert_lite)
    pg_variable = {}

    if (
        stetsonj_stats.get("n_detections_g_band", 0) >= 30
        and stetsonj_stats.get("g_psfFluxStetsonJ", 0) > 20
    ):
        pg_variable = {"pg_variable": "likely"}
    else:
        pg_variable = {"pg_variable": "unlikely"}

    TOPIC.publish(
        pittgoogle.Alert.from_dict(
            {**alert_lite.dict, "variability": stetsonj_stats},
            attributes={**alert_lite.attributes, **pg_variable},
            schema_name="default",
        )
    )

    return "", HTTP_204


def _calculate_stetsonJ_statistics(alert_lite: pittgoogle.Alert) -> Dict:
    """Adapted from:
    https://github.com/lsst/meas_base/blob/e5cf12406b54a6312b9d6fa23fbd132cd7999387/python/lsst/meas/base/diaCalculationPlugins.py#L904

    Compute the StetsonJ statistics on the DIA point source fluxes for each band.
    """
    alert_lite_dict = alert_lite.dict
    alert_df = _create_dataframe(alert_lite_dict)
    bands = alert_df["fid"].map(pittgoogle.utils.ztf_fid_names()).unique()
    outgoing_dict = {
        "objectId": alert_lite.dict["alertIds"]["objectId"],
        "candid": alert_lite.dict["alertIds"]["candid"],
    }

    # filter diaSource(s) in alert_df based on the filter(s) used
    for band in bands:
        filter_diaSources = alert_df[alert_df["fid"].map(pittgoogle.utils.ztf_fid_names()) == band]
        flux, flux_err = mag_to_flux(
            filter_diaSources["mag"],
            filter_diaSources["magzp"],
            filter_diaSources["magerr"],
        )
        tmp_df = filter_diaSources[
            ~np.logical_or(
                np.isnan(flux),
                np.isnan(flux_err),
            )
        ]

        if len(tmp_df) < 2:
            outgoing_dict[f"n_detections_{band}_band"] = len(tmp_df)
            outgoing_dict[f"{band}_psfFluxStetsonJ"] = np.nan
            continue

        fluxes = tmp_df[flux].to_numpy()
        errors = tmp_df[flux_err].to_numpy()
        outgoing_dict[f"n_detections_{band}_band"] = len(tmp_df)
        outgoing_dict[f"{band}_psfFluxStetsonJ"] = _stetson_J(fluxes, errors)

    return outgoing_dict


def _create_dataframe(alert_dict: dict) -> "pd.DataFrame":
    """Return a pandas DataFrame containing the source detections."""

    # sources and previous sources are expected to have the same fields
    sources_df = pd.DataFrame([alert_dict.get("source")] + (alert_dict.get("prvSources") or []))

    # use nullable integer data type to avoid converting ints to floats
    # for columns in one dataframe but not the other
    sources_ints = [c for c, v in sources_df.dtypes.items() if v == int]
    _dataframe = sources_df.astype({c: "Int64" for c in sources_ints})

    return _dataframe


def mag_to_flux(mag: float, zeropoint: float, magerr: float) -> Tuple[float, float]:
    """Convert an AB magnitude and its error to fluxes."""
    flux = 10 ** ((zeropoint - mag) / 2.5)
    fluxerr = flux * magerr * np.log(10 / 2.5)
    return flux, fluxerr


def _stetson_J(fluxes: np.ndarray, errors: np.ndarray) -> float:
    """Adapted from:
    https://github.com/lsst/meas_base/blob/e5cf12406b54a6312b9d6fa23fbd132cd7999387/python/lsst/meas/base/diaCalculationPlugins.py#L949

    Compute the single band StetsonJ statistic.

    Parameters
    ----------
    fluxes : `numpy.ndarray` (N,)
        Calibrated lightcurve flux values.
    errors : `numpy.ndarray` (N,)
        Errors on the calibrated lightcurve fluxes.

    Returns
    -------
    stetsonJ : `float`
        stetsonJ statistic for the input fluxes and errors.

    References
    ----------
    .. [1] Stetson, P. B., "On the Automatic Determination of Light-Curve Parameters for Cepheid Variables", PASP, 108,
    851S, 1996
    """
    n_points = len(fluxes)
    flux_mean = _stetson_mean(fluxes, errors)
    delta_val = np.sqrt(n_points / (n_points - 1)) * (fluxes - flux_mean) / errors
    p_k = delta_val**2 - 1

    return np.mean(np.sign(p_k) * np.sqrt(np.fabs(p_k)))


def _stetson_mean(values: np.ndarray, errors: np.ndarray) -> float:
    """Adapted from:
    https://github.com/lsst/meas_base/blob/e5cf12406b54a6312b9d6fa23fbd132cd7999387/python/lsst/meas/base/diaCalculationPlugins.py#L979

    Compute the Stetson mean of the fluxes which down-weights outliers.

    Weighted biased on an error weighted difference scaled by a constant (1/``a``) and raised to the power beta. Higher
    betas more harshly penalize outliers and ``a`` sets the number of sigma where a weighted difference of 1 occurs.

    Parameters
    ----------
    values : `numpy.dnarray`, (N,)
        Input values to compute the mean of.
    errors : `numpy.ndarray`, (N,)
        Errors on the input values.
    alpha : `float`
        Scalar down-weighting of the fractional difference. lower->more clipping. (Default value is 2.)
    beta : `float`
        Power law slope of the used to down-weight outliers. higher->more clipping. (Default value is 2.)
    n_iter : `int`
        Number of iterations of clipping.
    tol : `float`
        Fractional and absolute tolerance goal on the change in the mean before exiting early. (Default value is 1e-6)

    Returns
    -------
    mean : `float`
        Weighted stetson mean result.

    References
    ----------
    .. [1] Stetson, P. B., "On the Automatic Determination of Light-Curve Parameters for Cepheid Variables", PASP, 108,
    851S, 1996
    """
    # define values
    alpha = 2.0
    beta = 2.0
    n_iter = 20
    tol = 1e-6

    n_points = len(values)
    n_factor = np.sqrt(n_points / (n_points - 1))
    inv_var = 1 / errors**2
    mean = np.average(values, weights=inv_var)

    for _ in range(n_iter):
        chi = np.fabs(n_factor * (values - mean) / errors)
        tmp_mean = np.average(values, weights=inv_var / (1 + (chi / alpha) ** beta))
        diff = np.fabs(tmp_mean - mean)
        mean = tmp_mean
        if diff / mean < tol and diff < tol:
            break

    return mean
