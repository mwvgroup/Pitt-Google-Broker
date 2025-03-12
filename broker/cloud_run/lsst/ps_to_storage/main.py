#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module stores LSST alert data as an Avro file in Cloud Storage."""

import base64
import json
import math
import os
from typing import Any, Dict, Optional
from astropy.time import Time

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

# GCP resources used in this module
TOPIC_ALERTS = pittgoogle.Topic.from_cloud(
    "alerts", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)
TOPIC_BIGQUERY_IMPORT = pittgoogle.Topic.from_cloud(
    "bigquery-import", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
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
    try:
        store_alert_data(envelope=flask.request.get_json())
    # this is raised by blob.upload_from_file if the object already exists in the bucket
    except PreconditionFailed:
        # we'll simply pass, and the duplicate alert will go no further in our pipeline
        pass

    return "", HTTP_204


def store_alert_data(envelope) -> None:
    """Uploads the msg data bytes to a GCP storage bucket."""

    # create an alert object from the envelope
    try:
        alert = pittgoogle.Alert.from_cloud_run(envelope, "lsst")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    blob = bucket.blob(_generate_alert_filename(alert))
    blob.metadata = _create_file_metadata(alert, event_id=envelope["message"]["messageId"])

    # raise a PreconditionFailed exception if filename already exists in the bucket using "if_generation_match=0"
    # let it raise. the main function will catch it and then drop the message.
    blob.upload_from_string(base64.b64decode(envelope["message"]["data"]), if_generation_match=0)

    json_dict = _reformat_alert_data_to_valid_json(alert)

    # publish alerts to appropriate Pub/Sub topics
    TOPIC_ALERTS.publish(alert)  # deduplicated "alerts" stream
    publish_valid_json_stream(
        topic_name=TOPIC_BIGQUERY_IMPORT.name,
        message=json_dict,
        attributes={
            "schema_version": alert.schema.version,
        },
    )


def _generate_alert_filename(alert: pittgoogle.Alert) -> str:
    """Generate the filename of an alert stored to a Cloud Storage bucket.
    Parameters
    ----------
    alert : pittgoogle.Alert
        The alert object.
    Returns
    -------
    str: The formatted filename as "{schema_version}/{YYYY-MM-DD}/{diaObjectId}/{diaSourceId}.{format}".
    """
    time_obj = Time(alert.get("mjd"), format="mjd")
    alert_date = time_obj.datetime.strftime(
        "%Y-%m-%d"
    )  # convert the MJD timestamp to "YYYY-MM-DD"

    return f"{alert.schema.version}/{alert_date}/{alert.objectid}/{alert.sourceid}.avro"


def _create_file_metadata(alert: pittgoogle.Alert, event_id: str) -> dict:
    """Return key/value pairs to be attached to the file as metadata."""

    metadata = {"file_origin_message_id": event_id}
    metadata["diaObjectId"] = alert.objectid
    metadata["diaSourceId"] = alert.sourceid
    metadata["ra"] = alert.get("ra")
    metadata["dec"] = alert.get("dec")

    return metadata


def _reformat_alert_data_to_valid_json(alert: pittgoogle.Alert) -> dict:
    """Creates an Alert object whose data will be published as a valid JSON message."""
    return _reformat_nan_in_alert_dict(alert.drop_cutouts())


def _reformat_nan_in_alert_dict(alert_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively replace NaN values with None if present in alert dictionary."""
    return {k: _replace_nan_values_with_none(v) for k, v in alert_dict.items()}


def _replace_nan_values_with_none(value: Any) -> Any:
    """Recursively replace NaN values with None."""
    if isinstance(value, dict):
        return {k: _replace_nan_values_with_none(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace_nan_values_with_none(v) for v in value]
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def publish_valid_json_stream(
    topic_name: str, message: dict, attributes: Optional[dict] = None
) -> str:
    """Publish alert data to a Pub/Sub topic as a valid JSON message."""

    message_json = json.dumps(message, default=str)
    message_bytes = message_json.encode("utf-8")

    topic_path = publisher.topic_path(PROJECT_ID, topic_name)
    future = publisher.publish(topic_path, data=message_bytes, **attributes)

    return future.result()
