#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Classify an alert using SuperNNova (M¨oller & de Boissi`ere 2019).

This code is intended to be containerized and deployed to Google Cloud Run.
Once deployed, individual alerts in the "trigger" stream will be delivered to the container as HTTP requests.
"""

import base64
import io
import json
import os
import struct
from typing import Optional
from astropy.time import Time

import flask  # Manage the HTTP request containing the alert
import fastavro
import pittgoogle  # Manipulate the alert and interact with cloud resources
from confluent_kafka.schema_registry import SchemaRegistryClient
from google.cloud import storage, pubsub_v1

from datetime import datetime, timezone
from pathlib import Path

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

# These environment variables are defined when running the setup.sh script.
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
# Schema name of the incoming alert. View name options: pittgoogle.
SCHEMA_IN = "lsst.v7_4.alert"  # View the schema: pittgoogle.Schemas.get(SCHEMA_IN).avsc
# define a binary data structure for packing and unpacking bytes
_ConfluentWireFormatHeader = struct.Struct(">bi")

# Variables for outgoing data
HTTP_204 = 204  # HTTP code: Success
HTTP_400 = 400  # HTTP code: Bad Request
SCHEMA_OUT = "elasticc.v0_9_1.brokerClassification"  # View the schema: pittgoogle.Schemas.get(SCHEMA_OUT).avsc
# pittgoogle will construct the full resource names from the MODULE_NAME, SURVEY, and TESTID
TABLE = pittgoogle.Table.from_cloud(MODULE_NAME, survey=SURVEY, testid=TESTID)
# DESC is already listening to this pubsub stream so the leave camel case to avoid a breaking change
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
        # classify
        classifications = _classify(alert)
        alert = pittgoogle.Alert.from_cloud_run(envelope=envelope, schema_name=SCHEMA_IN)
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    # publish
    TOPIC.publish(_create_outgoing_alert(alert, classifications))
    TABLE.insert_rows([classifications])

    return "", HTTP_204


def _classify(alert: pittgoogle.Alert) -> dict:
    """Classify the alert using SuperNNova."""
    # init
    snn_df = _format_for_classifier(alert)
    device = "cpu"

    # classify
    _, pred_probs = classify_lcs(snn_df, MODEL_PATH, device)

    # extract results to a dict that matches the TABLE schema (TABLE.table.schema)
    # use `.item()` to convert numpy -> python types for later serialization
    pred_probs = pred_probs.flatten()
    classifications = {
        "alertId": alert.alertid,
        "diaObjectId": alert.objectid,
        "diaSourceId": alert.sourceid,
        "prob_class0": pred_probs[0].item(),
        "prob_class1": pred_probs[1].item(),
        "predicted_class": np.argmax(pred_probs).item(),
        "brokerVersion": MODULE_VERSION,
        # divide by 1000 to switch millisecond -> microsecond precision for BigQuery
        "elasticcPublishTimestamp": int(alert.attributes["kafka.timestamp"]) / 1000,
        "brokerIngestTimestamp": alert.msg.publish_time,
        "classifierTimestamp": datetime.now(timezone.utc),
    }

    return classifications


def _format_for_classifier(alert: pittgoogle.Alert) -> pd.DataFrame:
    """Create a DataFrame for input to SuperNNova."""
    alert_df = alert.dataframe
    snn_df = pd.DataFrame(
        data={
            # select a subset of columns and rename them for SuperNNova
            # get_key returns the name that the survey uses for a given field
            # for the full mapping, see alert.schema.map
            "FLT": alert_df[alert.get_key("filter")],
            "FLUXCAL": alert_df[alert.get_key("flux")],
            "FLUXCALERR": alert_df[alert.get_key("flux_err")],
            "MJD": alert_df[alert.get_key("mjd")],
            # add the object ID
            "SNID": [alert.objectid] * len(alert_df.index),
        },
        index=alert_df.index,
    )
    return snn_df


def _create_outgoing_alert(alert_in: pittgoogle.Alert, results: dict) -> pittgoogle.Alert:
    """Combine the incoming alert with the classification results to create the outgoing alert."""
    # write down the mappings between our classifications and the ELAsTiCC taxonomy
    # https://github.com/LSSTDESC/elasticc/blob/main/taxonomy/taxonomy.ipynb
    classifications = [
        {"classId": 2222, "probability": results["prob_class0"]},
    ]

    # construct a dict that conforms to SCHEMA_OUT
    outgoing_dict = {
        "alertId": alert_in.alertid,
        "diaSourceId": alert_in.sourceid,
        # multiply by 1000 to switch microsecond -> millisecond precision for elasticc schema
        "elasticcPublishTimestamp": int(results["elasticcPublishTimestamp"] * 1000),
        "brokerIngestTimestamp": results["brokerIngestTimestamp"],
        "brokerName": BROKER_NAME,
        "brokerVersion": results["brokerVersion"],
        "classifierName": CLASSIFIER_NAME,
        "classifierParams": str(MODEL_PATH),  # record the training file
        "classifications": classifications,
    }

    # create the outgoing Alert
    alert_out = pittgoogle.Alert.from_dict(
        payload=outgoing_dict, attributes=alert_in.attributes, schema_name=SCHEMA_OUT
    )
    # add the predicted class to the attributes. may help downstream users filter messages.
    alert_out.attributes[MODULE_NAME] = results["predicted_class"]

    return alert_out


def deserialize_confluent_wire_header(raw):
    """Parses the byte prefix for Confluent Wire Format-style Kafka messages.
    Parameters
    ----------
    raw : `bytes`
        The 5-byte encoded message prefix.
    Returns
    -------
    schema_version : `int`
        A version number which indicates the Confluent Schema Registry ID
        number of the Avro schema used to encode the message that follows this
        header.
    """
    _, version = _ConfluentWireFormatHeader.unpack(raw)

    return version
