#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Classify alerts using SuperNNova (Möller & de Boissière 2019)."""
import os
from datetime import datetime, timezone
from pathlib import Path

import flask
import google.cloud.logging
import numpy as np
import pandas as pd
import pittgoogle
from supernnova.validation.validate_onthefly import classify_lcs

# [FIXME] Make this helpful or else delete it.
# Connect the python logger to the google cloud logger.
# By default, this captures INFO level and above.
# pittgoogle uses the python logger.
# We don't currently use the python logger directly in this script, but we could.
google.cloud.logging.Client().setup_logging()

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# Provenance variables
BROKER_NAME = "Pitt-Google Broker"
MODULE_NAME = "supernnova"
MODULE_VERSION = "v0.6"

# Classifier variables
CLASSIFIER_NAME = "SuperNNova_v1.3"  # include the version for provenance
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
TABLE_SUPERNNOVA = pittgoogle.Table.from_cloud(MODULE_NAME, survey=SURVEY, testid=TESTID)
TABLE_CLASSIFICATIONS = pittgoogle.Table.from_cloud(
    "classifications", survey=SURVEY, testid=TESTID
)
TOPIC = pittgoogle.Topic.from_cloud(
    "SuperNNova", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run():
    """Classify the alert with SuperNNova; publish and store results.

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
        # unpack the alert
        # if the request does not contain a valid message, this raises a `BadRequest`
        alert_lite = pittgoogle.Alert.from_cloud_run(
            envelope=flask.request.get_json(), schema_name="ztf"
        )
        # what about attributes?
    except pittgoogle.exceptions.BadRequest as exc:
        # return the error text and an HTTP 400 Bad Request code
        return str(exc), 400

    # continue processing the alert
    snn_dict = _classify_with_snn(alert_lite)

    # announce to Pub/Sub
    TOPIC.publish(
        message={**alert_lite, "SuperNNova": snn_dict},
        attributes={"supernnova_class": str(snn_dict["predicted_class"])},
    )

    # when finished, return an empty string and an HTTP success code
    return "", 204

    # announce to pubsub
    gcp_utils.publish_pubsub(
        ps_topic,
        message={**alert_lite, "SuperNNova": snn_dict},
        attrs={**attrs, "supernnova_class": str(snn_dict["predicted_class"])},
    )

    # store in bigquery
    errors = gcp_utils.insert_rows_bigquery(
        snn_table,
        [
            {
                **snn_dict,
                "objectId": alert_lite["alertIds"]["objectId"],
                "candid": alert_lite["alertIds"]["sourceId"],
            }
        ],
    )
    if len(errors) > 0:
        logger.log_text(f"BigQuery insert error: {errors}", severity="WARNING")

    # store in bigquery
    classifications = [
        {
            "objectId": attrs["objectId"],
            "candid": attrs["candid"],
            "classifier": "SuperNNova",
            "classifier_version": 1.3,
            "class": snn_dict["predicted_class"],
            "probability": max(snn_dict["prob_class0"], snn_dict["prob_class1"]),
        }
    ]
    errors = gcp_utils.insert_rows_bigquery(class_table, classifications)
    if len(errors) > 0:
        logger.log_text(f"BigQuery insert error: {errors}", severity="WARNING")


def _classify_with_snn(alert_lite: pittgoogle.Alert) -> dict:
    """Classify the alert using SuperNNova."""
    snn_df = _format_for_snn(alert_lite)
    device = "cpu"

    # classify
    _, pred_probs = classify_lcs(snn_df, MODEL_PATH, device)

    # use `.item()` to convert numpy -> python types for later json serialization
    pred_probs = pred_probs.flatten()
    snn_dict = {
        "prob_class0": pred_probs[0].item(),
        "prob_class1": pred_probs[1].item(),
        "predicted_class": np.argmax(pred_probs).item(),
    }

    return snn_dict


def _format_for_snn(alert_lite: pittgoogle.Alert) -> pd.DataFrame:
    """Compute features and cast to a DataFrame for input to SuperNNova."""

    alert_df = alert_lite.dataframe

    snn_df = pd.DataFrame(data={"SNID": alert_lite.objectid}, index=alert_df.index)
    snn_df["FLT"] = alert_df["filter"].map(data_utils.ztf_fid_names())

    if SURVEY == "ztf":
        snn_df["MJD"] = math.jd_to_mjd(alert_df["jd"].loc[0])
        snn_df["FLUXCAL"], snn_df["FLUXCALERR"] = math.mag_to_flux(
            alert_df["mag"], alert_df["magzp"], alert_df["magerr"]
        )

    elif SURVEY == "decat":
        col_map = {"mjd": "MJD", "flux": "FLUXCAL", "fluxerr": "FLUXCALERR"}
        for acol, scol in col_map.items():
            snn_df[scol] = alert_df[acol]

    return snn_df
