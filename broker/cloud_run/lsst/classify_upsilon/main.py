#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Classify alerts using UPSILoN (Kim & Bailer-Jones 2015)."""

import os
import flask
import pandas as pd
import numpy as np
import pittgoogle
import upsilon
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
TOPIC = pittgoogle.Topic.from_cloud("upsilon", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID)

app = flask.Flask(__name__)

# load UPSILoN's classification model
rf_model = upsilon.load_rf_model()


@app.route(ROUTE_RUN, methods=["POST"])
def run() -> tuple[str, int]:
    """Classify alert with UPSILoN; publish and store results.

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
        alert_lite = pittgoogle.Alert.from_cloud_run(envelope, "default")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    upsilon_dict = _classify_with_upsilon(alert_lite)

    TOPIC.publish(
        pittgoogle.Alert.from_dict(
            {"alert_lite": alert_lite.dict, "upsilon": upsilon_dict},
            attributes={
                **alert_lite.attributes,
                "pg_upsilon_u_label": upsilon_dict["u_label"],
                "pg_upsilon_u_flag": upsilon_dict["u_flag"],
                "pg_upsilon_g_label": upsilon_dict["g_label"],
                "pg_upsilon_g_flag": upsilon_dict["g_flag"],
                "pg_upsilon_r_label": upsilon_dict["r_label"],
                "pg_upsilon_r_flag": upsilon_dict["r_flag"],
                "pg_upsilon_i_label": upsilon_dict["i_label"],
                "pg_upsilon_i_flag": upsilon_dict["i_flag"],
                "pg_upsilon_z_label": upsilon_dict["z_label"],
                "pg_upsilon_z_flag": upsilon_dict["z_flag"],
                "pg_upsilon_y_label": upsilon_dict["y_label"],
                "pg_upsilon_y_flag": upsilon_dict["y_flag"],
            },
            schema_name="default",
        )
    )

    return "", HTTP_204


def _classify_with_upsilon(alert_lite: pittgoogle.Alert) -> dict:
    # extract the alert
    alert_lite_dict = alert_lite.dict["alert_lite"]
    alert_df = _create_dataframe(alert_lite_dict)
    bands = ["u", "g", "r", "i", "z", "y"]
    outgoing_dict = {
        "diaObjectId": alert_lite_dict["diaObject"]["diaObjectId"],
        "diaSourceId": alert_lite_dict["diaSource"]["diaSourceId"],
    }

    for band in bands:
        # define parameters for feature extractions
        filter_diaSources = alert_df[alert_df["band"] == band]
        flux_gt_zero = filter_diaSources["psfFlux"].to_numpy() > 0

        # set output to None if data is absent or there are too few data points for this band; limit set by UPSILoN
        if filter_diaSources.empty or flux_gt_zero.sum() < 7:
            outgoing_dict[f"{band}_label"] = None
            outgoing_dict[f"{band}_probability"] = None
            outgoing_dict[f"{band}_flag"] = None
            continue

        flux = filter_diaSources["psfFlux"].to_numpy()[flux_gt_zero]
        flux_err = filter_diaSources["psfFluxErr"].to_numpy()[flux_gt_zero]

        # UPSILoN requires three features to make a prediction, define them below:
        date = filter_diaSources["midpointMjdTai"].to_numpy()[flux_gt_zero]
        mag = _convert_flux_to_mag(flux)
        mag_err = _calculate_mag_err(flux, flux_err)

        # extract features
        e_features = upsilon.ExtractFeatures(date, mag, mag_err)
        e_features.run()
        features = e_features.get_features()

        # classify
        label, probability, flag = upsilon.predict(rf_model, features)
        outgoing_dict[f"{band}_label"] = label
        outgoing_dict[f"{band}_probability"] = probability
        outgoing_dict[f"{band}_flag"] = flag

    return outgoing_dict


def _create_dataframe(alert_dict: pittgoogle.Alert) -> pd.DataFrame:
    """Return a pandas DataFrame containing the source detections."""

    # sources and previous sources are expected to have the same fields
    sources_df = pd.DataFrame(
        [alert_dict.get("diaSource")] + (alert_dict.get("prvDiaSources") or [])
    )
    # sources and forced sources may have different fields
    forced_df = pd.DataFrame(alert_dict.get("prvDiaForcedSources") or [])

    # use nullable integer data type to avoid converting ints to floats
    # for columns in one dataframe but not the other
    sources_ints = [c for c, v in sources_df.dtypes.items() if v == int]
    sources_df = sources_df.astype(
        {c: "Int64" for c in set(sources_ints) - set(forced_df.columns)}
    )
    forced_ints = [c for c, v in forced_df.dtypes.items() if v == int]
    forced_df = forced_df.astype({c: "Int64" for c in set(forced_ints) - set(sources_df.columns)})

    _dataframe = pd.concat([sources_df, forced_df], ignore_index=True)
    return _dataframe


def _convert_flux_to_mag(flux: np.ndarray) -> np.ndarray:
    """Adapted from:
    https://github.com/lsst/tutorial-notebooks/blob/044219c9ae5521edcc816af88e4b341e19326dbf/DP0.2/01_Introduction_to_DP02.ipynb#L511

    Converts flux [nJy] to AB magnitude.
    """
    return -2.5 * np.log10(flux) + 31.4


def _calculate_mag_err(flux: np.ndarray, flux_err: np.ndarray) -> np.ndarray:
    """Calculates magnitude uncertainty."""
    return abs(-2.5 / (flux * np.log(10))) * flux_err
