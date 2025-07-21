#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module stores LVK alert data as a JSON file in Cloud Storage."""

import os
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
VERSIONTAG = os.getenv("VERSIONTAG")

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
bucket_name = f"{PROJECT_ID}-{SURVEY}_alerts"
if TESTID != "False":
    bucket_name = f"{bucket_name}-{TESTID}"

client = storage.Client()
bucket = client.get_bucket(client.bucket(bucket_name, user_project=PROJECT_ID))

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run():
    """Uploads alert data to a GCS bucket. Publishes a de-duplicated JSON-serialized "alerts" stream
    (${survey}-alerts) containing the original alert bytes. A BigQuery subscription is used to write alert data to
    the appropriate BigQuery table.

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
        alert = pittgoogle.Alert.from_cloud_run(envelope, "lvk")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    blob = bucket.blob(_name_in_bucket(alert))
    blob.metadata = _create_file_metadata(alert, event_id=envelope["message"]["messageId"])

    # raise a PreconditionFailed exception if filename already exists in the bucket using "if_generation_match=0"
    try:
        blob.upload_from_string(alert.msg.data, if_generation_match=0)
    except PreconditionFailed:
        # this alert is a duplicate. drop it.
        return "", HTTP_204

    # publish the same alert as JSON
    TOPIC_ALERTS.publish(alert)

    return "", HTTP_204


def _create_file_metadata(alert: pittgoogle.Alert, event_id: str) -> dict:
    """Return key/value pairs to be attached to the file as metadata."""
    # https://git.ligo.org/emfollow/igwn-gwalert-schema/-/blob/main/igwn.alerts.v1_0.Alert.schema.json
    metadata = {"file_origin_message_id": event_id}
    metadata["_".join("time_created")] = alert.dict["time_created"]
    metadata["_".join("alert_type")] = alert.dict["alert_type"]
    metadata["_".join("id")] = alert.dict["superevent_id"]

    return metadata


def _name_in_bucket(alert: pittgoogle.Alert) -> str:
    """Return the name of the file in the bucket."""
    _date = alert.dict["time_created"]
    _alert_type = alert.dict["alert_type"]
    _id = alert.dict["superevent_id"]

    return f"{VERSIONTAG}/{_date}/{_alert_type}/{_id}.json"
