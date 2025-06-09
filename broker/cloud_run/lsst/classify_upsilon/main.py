#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Classify alerts using UPSILoN (Kim & Bailer-Jones 2015)."""

import os
from typing import List, Dict, Optional
import flask
import pandas as pd
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
TOPIC_LITE = pittgoogle.Topic.from_cloud(
    "upsilon", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run():
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
        alert = pittgoogle.Alert.from_cloud_run(envelope, "default")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    upsilon_dict = _classify_with_UPSILoN(alert)

    TOPIC_LITE.publish(_create_outgoing_alert(upsilon_dict))

    return "", HTTP_204


def _classify_with_UPSILoN(alert: pittgoogle.Alert) -> Dict:
    # extract the alert
    alert_lite_dict = alert.dict["alert_lite"]
    alert_df = _create_dataframe(alert_lite_dict)
    bands = alert_df["band"].unique()

    # load UPSILoN's classification model
    rf_model = upsilon.load_rf_model()
    for band in bands:
        # read the light curve's date (in days), magnitude, and magnitude errors.
        filter_diaSources = alert_df[alert_df["band"] == band]
        # date = np.array([...])
        # mag = np.array([...])
        # err = np.array([...])

        # # Extract features
        # e_features = upsilon.ExtractFeatures(date, mag, err)
        # e_features.run()
        # features = e_features.get_features()

        # # Classify the light curve
        # label, probability, flag = upsilon.predict(rf_model, features)
        # print label, probability, flag

    return


def _create_dataframe(alert_dict: pittgoogle.Alert) -> "pd.DataFrame":
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


def _create_outgoing_alert(alert: pittgoogle.Alert) -> pittgoogle.Alert:
    """Creates a "lite" alert containing a subset of the fields of the original alert packet."""
    return
