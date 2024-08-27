#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module stores alert data in BigQuery tables."""

import os
import pittgoogle
import base64
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
pittgoogle_project = pittgoogle.ProjectIds().pittgoogle
MODULE_NAME = f"alerts_{VERSIONTAG}"
TABLE = pittgoogle.Table.from_cloud(MODULE_NAME, survey=SURVEY, testid=TESTID)
TOPIC = pittgoogle.Topic.from_cloud("BigQuery", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID)

def run(event: dict, context: functions_v1.context.Context) -> None:
    """Send alert data to various BigQuery tables.

    Args:
        msg: Pub/Sub message data and attributes.
            `data` field contains the message data in a base64-encoded string.
            `attributes` field contains the message's custom attributes in a dict.

        context: Metadata describing the Cloud Function's trigging event.
    """
    
    # decode the base64-encoded message data
    decoded_data = base64.b64decode(event["data"])

    # create a PubsubMessage-like object with the existing event dictionary
    pubsub_message = pubsub_v1.types.PubsubMessage(
        data=decoded_data,
        attributes=event.get(["attributes"], {})
    )

    # unpack the alert
    alert = pittgoogle.Alert.from_msg(msg=pubsub_message,schema_name="default_schema")
    
    # send the alert to BigQuery table
    alert_table = insert_rows_alerts(alert)
    
    # announce what's been done
    TOPIC.publish(_create_outgoing_alert(alert, alert_table))

def insert_rows_alerts(alert: pittgoogle.alert.Alert):
    """Insert rows into the `alerts` table via the streaming API."""
    # send to bigquery
    errors = TABLE.insert_rows([alert])

    # handle errors; if none, save table id for Pub/Sub message
    if len(errors) == 0:
        table_dict = {"alerts_table": f"{TABLE.id}"}
    else:
        msg = f"Error inserting to alerts table: {errors}"
        logger.log_text(msg, severity="DEBUG")
        table_dict = {"alerts_table": None}

    return table_dict

def _create_outgoing_alert(alert: pittgoogle.alert.Alert, table_dict: dict) -> pittgoogle.Alert:

    attrs = {
        "alert_table": table_dict['alerts_table'],
        "type": alert.dict['alert_type']
    }
    
    alert_out = pittgoogle.Alert.from_dict(
        payload=alert.dict, attributes=attrs, schema_name="default_schema"
    )
    
    return alert_out