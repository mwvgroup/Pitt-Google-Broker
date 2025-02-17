#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module publishes alert data to various Pub/Sub topics."""

import base64
import os
import pittgoogle
from google.cloud import functions_v1, pubsub_v1, logging

PROJECT_ID = os.getenv("GCP_PROJECT")
SURVEY = os.getenv("SURVEY")
TESTID = os.getenv("TESTID")
VERSIONTAG = os.getenv("VERSIONTAG")

# connect to the cloud logger
log_name = "store-bigquery-cloudfnc"  # same log for all broker instances
logging_client = logging.Client()
logger = logging_client.logger(log_name)

# GCP resources used in this module
TOPIC_BIGQUERY_IMPORT = pittgoogle.Topic.from_cloud(
    "bigquery-import", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)


def run(event: dict, _context: functions_v1.context.Context) -> None:
    """Send alert data to various Pub/Sub topics.

    Args:
        event: Pub/Sub message data and attributes.
            `data` field contains the message data in a base64-encoded string.
            `attributes` field contains the message's custom attributes in a dict.

        context: Metadata describing the Cloud Function's trigging event.

    'context' is an unused argument in the function that is required
    see https://cloud.google.com/functions/1stgendocs/writing/write-event-driven-functions#background-functions
    """

    # decode the base64-encoded message data
    decoded_data = base64.b64decode(event["data"])

    # create a PubsubMessage-like object with the existing event dictionary
    pubsub_message = pubsub_v1.types.PubsubMessage(
        data=decoded_data, attributes=event.get("attributes", {})
    )

    # unpack the alert
    alert = pittgoogle.Alert.from_msg(msg=pubsub_message, schema_name="ztf")

    # transform the data and publish it to Pub/Sub
    TOPIC_BIGQUERY_IMPORT.publish(_drop_cutouts(alert))


def _drop_cutouts(alert: pittgoogle.alert.Alert) -> pittgoogle.alert.Alert:
    """Removes cutouts from alerts."""
    # collect attributes
    attrs = {**alert.attributes}

    # define message
    msg = alert.dict

    # define and remove cutouts from message
    cutouts = ["cutoutTemplate", "cutoutScience", "cutoutDifference"]
    for key in cutouts:
        msg.pop(key, None)

    # create outgoing alert
    alert_out = pittgoogle.Alert.from_dict(payload=msg, attributes=attrs)

    return alert_out
