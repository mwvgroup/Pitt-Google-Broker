#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Classify an alert using SuperNNova (Möller & de Boissière 2019)."""

import os
from pathlib import Path
import flask
import pittgoogle

import google.cloud.logging
import numpy as np
import pandas as pd
from supernnova.validation.validate_onthefly import classify_lcs

# [FIXME] Make this helpful or else delete it.
# Connect the python logger to the google cloud logger.
# By default, this captures INFO level and above.
# pittgoogle uses the python logger.
# We don't currently use the python logger directly in this script, but we could.
google.cloud.logging.Client().setup_logging()

# these environment variables are defined when running the deploy.sh script.
PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# provenance variables
MODULE_VERSION = 0.1

# classifier variables
model_dir_name = "ZTF_DMAM_V19_NoC_SNIa_vs_CC_forFink"
model_file_name = (
    "vanilla_S_0_CLF_2_R_none_photometry_DF_1.0_N_global_lstm_32x2_0.05_128_True_mean.pt"
)
MODEL_PATH = Path(__file__).resolve().parent / model_dir_name / model_file_name

# Variables for incoming data
# A url route is used in setup.sh when the trigger subscription is created.
# It is possible to define multiple routes in a single module and trigger them using different subscriptions.
ROUTE_RUN = "/"  # HTTP route that will trigger run(). Must match setup.sh

# Variables for outgoing data
HTTP_204 = 204  # HTTP code: Success
HTTP_400 = 400  # HTTP code: Bad Request

# GCP resources used in this module
# pittgoogle will construct the full resource names from the module name, SURVEY, and TESTID
TOPIC = pittgoogle.Topic.from_cloud(
    "SuperNNova", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)


app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run():
    """Classify the alert; publish and store results.

    This module is intended to be deployed as a Cloud Run service. It will operate as an HTTP endpoint
    triggered by Pub/Sub messages. This function will be called once for every message sent to this route.
    It should accept the incoming HTTP request and return a response.

    Returns
    -------
    response : tuple(str, int)
        Tuple containing the response body (string) and HTTP status code (int). Flask will convert the
        tuple into a proper HTTP response. Note that the response is a status message for the web server
        and should not contain the classification results.
    """
    # extract the envelope from the request that triggered the endpoint
    # this contains a single Pub/Sub message with the alert to be processed
    envelope = flask.request.get_json()

    # unpack the alert. raises a `BadRequest` if the envelope does not contain a valid message
    try:
        alert_lite = pittgoogle.Alert.from_cloud_run(envelope, "default")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    # classify
    snn_dict = _classify(alert_lite)

    # publish
    TOPIC.publish(
        pittgoogle.Alert.from_dict(
            payload={"alert_lite": alert_lite.dict["alert_lite"], "SuperNNova": snn_dict},
            attributes={
                **alert_lite.attributes,
                "pg_supernnova_class": snn_dict["predicted_class"],
            },
            schema_name="default",
        )
    )

    return "", HTTP_204


def _classify(alert_lite: pittgoogle.Alert) -> dict:
    """Classify the alert using SuperNNova."""
    # init
    snn_df = _format_for_classifier(alert_lite)
    device = "cpu"

    # classify
    _, pred_probs = classify_lcs(snn_df, MODEL_PATH, device)

    # use `.item()` to convert numpy -> python types for later serialization
    pred_probs = pred_probs.flatten()
    snn_dict = {
        "prob_class0": pred_probs[0].item(),
        "prob_class1": pred_probs[1].item(),
        "predicted_class": np.argmax(pred_probs).item(),
    }

    return snn_dict


def _format_for_classifier(alert_lite: pittgoogle.Alert) -> pd.DataFrame:
    """Create a DataFrame for input to SuperNNova."""
    alert_lite_dict = alert_lite.dict["alert_lite"]
    alert_df = _create_dataframe(alert_lite_dict)
    snn_df = pd.DataFrame(
        data={
            # select a subset of columns and rename them for SuperNNova
            # get_key returns the name that the survey uses for a given field
            # for the full mapping, see alert.schema.map
            "SNID": [alert_lite_dict["diaObject"]["diaObjectId"]] * len(alert_df.index),
            "FLT": alert_df["band"],
            "MJD": alert_df["midpointMjdTai"],
            "FLUXCAL": alert_df["psfFlux"],
            "FLUXCALERR": alert_df["psfFluxErr"],
        },
        index=alert_df.index,
    )

    return snn_df


def _create_dataframe(alert_dict: dict) -> "pd.DataFrame":
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
