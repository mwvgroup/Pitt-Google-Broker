#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Classify alerts using SuperNNova (Möller & de Boissière 2019)."""
import os
from pathlib import Path

import flask
import google.cloud.logging
import numpy as np
import pandas as pd
import pittgoogle
from supernnova.validation.validate_onthefly import classify_lcs
from broker_utils import math

# [FIXME] Make this helpful or else delete it.
# Connect the python logger to the google cloud logger.
# By default, this captures INFO level and above.
# pittgoogle uses the python logger.
# We don't currently use the python logger directly in this script, but we could.
google.cloud.logging.Client().setup_logging()

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# classifier variables
CLASSIFIER_VERSION = 1.3
model_dir_name = "ZTF_DMAM_V19_NoC_SNIa_vs_CC_forFink"
model_file_name = (
    "vanilla_S_0_CLF_2_R_none_photometry_DF_1.0_N_global_lstm_32x2_0.05_128_True_mean.pt"
)
MODEL_PATH = Path(__file__).resolve().parent / model_dir_name / model_file_name
MODULE_NAME = "SuperNNova"

# variables for incoming data
# a url route is used in setup.sh when the trigger subscription is created.
# it is possible to define multiple routes in a single module and trigger them using different subscriptions.
ROUTE_RUN = "/"  # HTTP route that will trigger run(). Must match setup.sh

# variables for outgoing data
HTTP_204 = 204  # HTTP code: Success
HTTP_400 = 400  # HTTP code: Bad Request
TABLE_SUPERNNOVA = pittgoogle.Table.from_cloud(MODULE_NAME, survey=SURVEY, testid=TESTID)
TABLE_CLASSIFICATIONS = pittgoogle.Table.from_cloud(
    "classifications", survey=SURVEY, testid=TESTID
)
TOPIC = pittgoogle.Topic.from_cloud(
    MODULE_NAME, survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run():
    """Classify alert with SuperNNova; publish and store results.

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
    try:
        alert_lite = pittgoogle.Alert.from_cloud_run(
            envelope=flask.request.get_json(), schema_name="ztf"
        )
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    snn_dict = _classify(alert_lite)

    # announce to Pub/Sub
    TOPIC.publish(_create_outgoing_alert(alert_lite, snn_dict))

    # store in BigQuery
    TABLE_SUPERNNOVA.insert_rows(
        [
            {
                "objectId": alert_lite["alertIds"]["objectId"],
                "candid": alert_lite["alertIds"]["sourceId"],
            },
            snn_dict,
        ]
    )
    TABLE_CLASSIFICATIONS.insert_rows(
        [
            {
                "objectId": alert_lite.objectid,
                "candid": alert_lite.attributes.get("candid"),
                "classifier": MODULE_NAME,
                "classifier_version": CLASSIFIER_VERSION,
                "class": snn_dict["predicted_class"],
                "probability": max(snn_dict["prob_class0"], snn_dict["prob_class1"]),
            }
        ]
    )

    return "", HTTP_204


def _classify(alert_lite: pittgoogle.Alert) -> dict:
    """Classify the alert using SuperNNova."""
    snn_df = _format_for_snn(alert_lite)
    device = "cpu"

    # classify
    _, pred_probs = classify_lcs(snn_df, MODEL_PATH, device)

    # use `.item()` to convert numpy -> python types for later json serialization
    pred_probs = pred_probs.flatten()
    classifications = {
        "prob_class0": pred_probs[0].item(),
        "prob_class1": pred_probs[1].item(),
        "predicted_class": np.argmax(pred_probs).item(),
    }

    return classifications


def _format_for_snn(alert_lite: pittgoogle.Alert) -> pd.DataFrame:
    """Create a DataFrame for input to SuperNNova."""
    alert_df = alert_lite.dataframe
    fluxcal, fluxcalerr = math.mag_to_flux(
        alert_df[alert_lite.get_key("mag")],
        alert_df[alert_lite.get_key("mag_zp")],
        alert_df[alert_lite.get_key("mag_err")],
    )

    snn_df = pd.DataFrame(
        data={
            "SNID": [alert_lite.objectid] * len(alert_df.index),
            "FLT": alert_df[alert_lite.get_key("filter")].map(pittgoogle.utils.ztf_fid_names()),
            "MJD": math.jd_to_mjd(alert_df["jd"].loc[0]),
            "FLUXCAL": fluxcal,
            "FLUXCALERR": fluxcalerr,
        },
        index=alert_df.index,
    )
    return snn_df


def _create_outgoing_alert(alert_in: pittgoogle.Alert, results: dict) -> pittgoogle.Alert:
    return pittgoogle.Alert.from_dict(
        payload={**alert_in.dict, **results},
        attributes={"supernnova_class": results["predicted_class"], **alert_in.attributes},
    )
