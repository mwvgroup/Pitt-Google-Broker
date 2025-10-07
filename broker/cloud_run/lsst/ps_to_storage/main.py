#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module stores LSST alert data as an Avro file in Cloud Storage and publishes it to various Pub/Sub topics."""

import os
from typing import Any
import flask
import pittgoogle
from google.cloud import logging, storage
from google.cloud.exceptions import PreconditionFailed

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
LITE_FIELDS_CONFIG = {
    "diaSource": {
        "fields": {
            "diaSourceId",
            "midpointMjdTai",
            "ra",
            "raErr",
            "dec",
            "decErr",
            "psfFlux",
            "psfFluxErr",
            "band",
        },
        "is_list": False,
    },
    "prvDiaSources": {
        "fields": {
            "diaSourceId",
            "midpointMjdTai",
            "ra",
            "raErr",
            "dec",
            "decErr",
            "psfFlux",
            "psfFluxErr",
            "band",
        },
        "is_list": True,
    },
    "diaObject": {
        "fields": {
            "diaObjectId",
            "lastDiaSourceMjdTai",
            "firstDiaSourceMjdTai",
            "nDiaSources",
            "u_psfFluxErrMean",
            "g_psfFluxErrMean",
            "r_psfFluxErrMean",
            "i_psfFluxErrMean",
            "z_psfFluxErrMean",
            "y_psfFluxErrMean",
        },
        "is_list": False,
    },
}

# GCP resources used in this module
TOPIC_ALERTS = pittgoogle.Topic.from_cloud(
    "alerts", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)
TOPIC_ALERTS_JSON = pittgoogle.Topic.from_cloud(
    "alerts-json", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)
TOPIC_LITE = pittgoogle.Topic.from_cloud(
    "lite", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)
bucket_name = f"{PROJECT_ID}-{SURVEY}_alerts"
if TESTID != "False":
    bucket_name = f"{bucket_name}-{TESTID}"

client = storage.Client()
bucket = client.get_bucket(client.bucket(bucket_name, user_project=PROJECT_ID))

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run():
    """Uploads alert data to a GCS bucket. Publishes a de-duplicated "alerts" stream (${survey}-alerts) containing the
    original alert bytes and publishes an additional JSON message stream (${survey}-bigquery-import) in which a
    BigQuery subscription is used to write alert data to the appropriate BigQuery table.

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
        alert = pittgoogle.Alert.from_cloud_run(envelope, "lsst")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    blob = bucket.blob(alert.name_in_bucket)
    blob.metadata = _create_file_metadata(alert, event_id=envelope["message"]["messageId"])

    # raise a PreconditionFailed exception if filename already exists in the bucket using "if_generation_match=0"
    # let it raise. the message will be dropped.
    try:
        blob.upload_from_string(alert.msg.data, if_generation_match=0)
    except PreconditionFailed:
        # this alert is a duplicate. drop it.
        return "", HTTP_204

    # publish the same alert as Confluent Wire Avro.
    TOPIC_ALERTS.publish(alert)
    # publish the same alert as JSON. Data will be coerced to valid JSON by pittgoogle.
    TOPIC_ALERTS_JSON.publish(alert, serializer="json")
    # publish a lite version of the alert as JSON
    TOPIC_LITE.publish(_create_lite_alert(alert), serializer="json")

    return "", HTTP_204


def _create_file_metadata(alert: pittgoogle.Alert, event_id: str) -> dict:
    """Return key/value pairs to be attached to the file as metadata."""

    metadata = {"file_origin_message_id": event_id}
    metadata["_".join(alert.get_key("objectid"))] = alert.objectid
    metadata["_".join(alert.get_key("sourceid"))] = alert.sourceid
    metadata["_".join(alert.get_key("ra"))] = alert.ra
    metadata["_".join(alert.get_key("dec"))] = alert.dec
    metadata["kafka.timestamp"] = alert.attributes["kafka.timestamp"]

    return metadata


def _create_lite_alert(alert: pittgoogle.Alert) -> pittgoogle.Alert:
    """Creates a lite Alert object by filtering nested fields from the original Alert dictionary."""

    alert_lite_dict = alert.drop_cutouts()
    for key, config in LITE_FIELDS_CONFIG.items():
        if key in alert_lite_dict:
            # replace the original nested object with its filtered version
            alert_lite_dict[key] = _process_field(alert_lite_dict.get(key), config)

    return pittgoogle.Alert.from_dict(
        payload={"alert_lite": alert_lite_dict},
        attributes={**alert.attributes},
    )


def _process_field(original_value: Any, config: dict) -> Any:
    """Filters a dictionary or a list of dictionaries based on the provided configuration."""
    whitelisted_fields = config["fields"]

    if config["is_list"]:
        return [_filter_dict(item, whitelisted_fields) for item in original_value or []]
    return _filter_dict(original_value, whitelisted_fields)


def _filter_dict(alert_dict: dict, whitelisted_fields: set) -> dict:
    """Creates a new dictionary containing only the keys specified in whitelisted_fields."""

    return {k: v for k, v in (alert_dict or {}).items() if k in whitelisted_fields}
