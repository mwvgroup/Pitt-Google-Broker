#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module produces "value-added" lite alerts containing J indices on the DIA point source fluxes."""

import os
from typing import Dict
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

    j_dict = _classify(alert_lite)
    pg_variable = {"pg_variable": "unlikely"}

    for band in ["g", "r", "u"]:
        if (
            j_dict.get(f"n_detections_{band}_band", 0) >= 30
            and j_dict.get(f"{band}_psfFluxStetsonJ", 0) > 20
        ):
            pg_variable = {"pg_variable": "likely"}
            break

    TOPIC.publish(
        pittgoogle.Alert.from_dict(
            {"alert_lite": alert_lite.dict["alert_lite"], "variability": j_dict},
            attributes={**alert_lite.attributes, **pg_variable},
            schema_name="default",
        )
    )

    return "", HTTP_204


def _classify(alert_lite: pittgoogle.Alert) -> Dict:
    """Adapted from:
    https://github.com/lsst/meas_base/blob/e5cf12406b54a6312b9d6fa23fbd132cd7999387/python/lsst/meas/base/diaCalculationPlugins.py#L904

    Compute the StetsonJ statistics on the DIA point source fluxes for each band.
    """

    alert_df = _create_dataframe(alert_lite.dict["alert_lite"])
    bands = alert_df["band"].unique()
    outgoing_dict = {}

    # filter diaSource(s) in alert_df based on the filter(s) used
    for band in bands:
        filter_diaSources = alert_df[alert_df["band"] == band]
        tmp_df = filter_diaSources[
            ~np.logical_or(
                np.isnan(filter_diaSources["psfFlux"]),
                np.isnan(filter_diaSources["psfFluxErr"]),
            )
        ]

        if len(tmp_df) < 2:
            outgoing_dict[f"n_detections_{band}_band"] = len(tmp_df)
            outgoing_dict[f"{band}_psfFluxStetsonJ"] = np.nan
            continue

        fluxes = tmp_df["psfFlux"].to_numpy()
        errors = tmp_df["psfFluxErr"].to_numpy()
        outgoing_dict[f"n_detections_{band}_band"] = len(tmp_df)
        outgoing_dict[f"{band}_psfFluxStetsonJ"] = _stetson_J(fluxes, errors)

    return outgoing_dict


def _create_dataframe(alert_lite_dict: dict) -> pd.DataFrame:
    """Create a DataFrame object from the alert lite dictionary."""

    required_cols = [
        "band",
        "psfFlux",
        "psfFluxErr",
    ]  # columns required by to compute J index

    # extract fields and create filtered DataFrames
    sources = [alert_lite_dict.get("diaSource")] + (alert_lite_dict.get("prvDiaSources") or [])
    forced_sources = alert_lite_dict.get("prvDiaForcedSources") or []
    sources_df = pd.DataFrame(filter_columns(sources, required_cols))
    forced_df = pd.DataFrame(filter_columns(forced_sources, required_cols))

    # concatenate diaSource, prvDiaSources, and prvDiaForcedSources into a single DataFrame
    df = pd.concat([sources_df, forced_df], ignore_index=True)

    return df


def filter_columns(field_list, required_cols):
    """Extract only relevant columns if they exist."""

    return [
        {k: field.get(k) for k in required_cols if k in field}
        for field in field_list
        if field is not None
    ]


def _stetson_J(fluxes: np.ndarray, errors: np.ndarray) -> float:
    """Adapted from:
    https://github.com/lsst/meas_base/blob/013ef565331c896a3fd73aefec294de42bc66371/python/lsst/meas/base/diaCalculationPlugins.py#L1279

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


def _stetson_mean(
    values: np.ndarray, errors: np.ndarray, mean=None, alpha=2.0, beta=2.0, n_iter=20, tol=1e-6
) -> float:
    """Adapted from:
    https://github.com/lsst/meas_base/blob/013ef565331c896a3fd73aefec294de42bc66371/python/lsst/meas/base/diaCalculationPlugins.py#L1309

    Compute the stetson mean of the fluxes which down-weights outliers. Weighted biased on an error weighted difference
    scaled by a constant (1/``a``) and raised to the power beta. Higher betas more harshly penalize outliers and ``a``
    sets the number of sigma where a weighted difference of 1 occurs.

    Parameters
    ----------
    values : `numpy.dnarray`, (N,)
        Input values to compute the mean of.
    errors : `numpy.ndarray`, (N,)
        Errors on the input values.
    mean : `float`
        Starting mean value or None.
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

    n_points = len(values)
    n_factor = np.sqrt(n_points / (n_points - 1))
    inv_var = 1 / errors**2
    if mean is None:
        mean = np.average(values, weights=inv_var)

    for _ in range(n_iter):
        chi = np.fabs(n_factor * (values - mean) / errors)
        tmp_mean = np.average(values, weights=inv_var / (1 + (chi / alpha) ** beta))
        diff = np.fabs(tmp_mean - mean)
        mean = tmp_mean
        if diff / mean < tol and diff < tol:
            break

    return mean
