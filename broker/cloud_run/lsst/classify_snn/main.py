#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Classify an alert using SuperNNova (Möller & de Boissière 2019).

This code is intended to be containerized and deployed to Google Cloud Run.
Once deployed, individual alerts in the "trigger" stream will be delivered to the container as HTTP requests.
"""

import os
from pathlib import Path
import flask  # Manage the HTTP request containing the alert
import pittgoogle  # Manipulate the alert and interact with cloud resources

import google.cloud.logging
import numpy as np
import pandas as pd
from supernnova.validation.validate_onthefly import classify_lcs  # Classify the alert

# [FIXME] Make this helpful or else delete it.
# Connect the python logger to the google cloud logger.
# By default, this captures INFO level and above.
# pittgoogle uses the python logger.
# We don't currently use the python logger directly in this script, but we could.
google.cloud.logging.Client().setup_logging()

# These environment variables are defined when running the deploy.sh script.
PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# provenance variables
MODULE_NAME = "SuperNNova"
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
# pittgoogle will construct the full resource names from the MODULE_NAME, SURVEY, and TESTID
TOPIC = pittgoogle.Topic.from_cloud(
    MODULE_NAME, survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)
TOPIC_BIGQUERY_IMPORT_SUPERNNOVA = pittgoogle.Topic.from_cloud(
    "bigquery-import-SuperNNova", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)

TOPIC_BIGQUERY_IMPORT_CLASSIFICATIONS = pittgoogle.Topic.from_cloud(
    "bigquery-import-classifications", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
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
        alert = pittgoogle.Alert.from_cloud_run(envelope, "lsst")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    # classify
    snn_dict = _classify(alert)

    # prepare data for publishing
    classifier_summary = _classification_summary(snn_dict)
    snn_alert = _create_outgoing_alert(alert, snn_dict)
    snn_results = pittgoogle.Alert.from_dict(payload=snn_dict)

    # publish
    TOPIC.publish(snn_alert, serializer="avro")
    TOPIC_BIGQUERY_IMPORT_CLASSIFICATIONS.publish(classifier_summary, serializer="json")
    TOPIC_BIGQUERY_IMPORT_SUPERNNOVA.publish(snn_results, serializer="json")

    return "", HTTP_204


def _classify(alert: pittgoogle.Alert) -> dict:
    """Classify the alert using SuperNNova."""
    # init
    snn_df = _format_for_classifier(alert)
    device = "cpu"

    # classify
    _, pred_probs = classify_lcs(snn_df, MODEL_PATH, device)

    # use `.item()` to convert numpy -> python types for later serialization
    pred_probs = pred_probs.flatten()
    snn_dict = {
        "diaObjectId": alert.objectid,
        "diaSourceId": alert.sourceid,
        "prob_class0": pred_probs[0].item(),
        "prob_class1": pred_probs[1].item(),
        "predicted_class": np.argmax(pred_probs).item(),
    }

    return snn_dict


def _format_for_classifier(alert: pittgoogle.Alert) -> pd.DataFrame:
    """Create a DataFrame for input to SuperNNova."""
    alert_df = alert.dataframe
    snn_df = pd.DataFrame(
        data={
            # select a subset of columns and rename them for SuperNNova
            # get_key returns the name that the survey uses for a given field
            # for the full mapping, see alert.schema.map
            "SNID": [alert.objectid] * len(alert_df.index),
            "FLT": alert_df[alert.get_key("filter")[1]],
            "MJD": alert_df[alert.get_key("mjd")[1]],
            "FLUXCAL": alert_df[alert.get_key("flux")[1]],
            "FLUXCALERR": alert_df[alert.get_key("flux_err")[1]],
        },
        index=alert_df.index,
    )

    return snn_df


def _create_outgoing_alert(alert: pittgoogle.Alert, snn_dict: dict) -> pittgoogle.Alert:
    """Combine the incoming alert with the classification results to create the outgoing alert."""

    return pittgoogle.Alert.from_dict(
        payload={**alert.dict, "SuperNNova": snn_dict},
        attributes={"supernnova_class": snn_dict["predicted_class"], **alert.attributes},
    )


def _classification_summary(snn_dict: dict) -> pittgoogle.Alert:
    """Create a summary of the classification results for storage in BigQuery."""
    classification_dict = {
        "diaObjectId": snn_dict["diaObjectId"],
        "diaSourceId": snn_dict["diaSourceId"],
        "classifier": "purity",
        "classifier_version": MODULE_VERSION,
        "class": snn_dict["predicted_class"],
        "probability": max(snn_dict["prob_class0"], snn_dict["prob_class1"]),
    }

    return pittgoogle.Alert.from_dict(payload={**classification_dict})
