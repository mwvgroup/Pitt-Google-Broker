#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module stores alert data in BigQuery tables."""

import base64
import os
from typing import Dict, Optional
from pathlib import Path

from google.cloud import functions_v1, logging

from broker_utils import data_utils, gcp_utils, schema_maps

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")
VERSIONTAG = os.getenv("VERSIONTAG")

# connect to the cloud logger
logging_client = logging.Client()
log_name = "store-bigquery-cloudfnc"  # same log for all broker instances
logger = logging_client.logger(log_name)

# GCP resources used in this module
bq_dataset = SURVEY
ps_topic = f"{SURVEY}-BigQuery"
if TESTID != "False":
    bq_dataset = f"{bq_dataset}_{TESTID}"
    ps_topic = f"{ps_topic}-{TESTID}"

schema_dir_name = "schema_maps"
schema_file_name = f"{SURVEY}.yaml"
path_to_local_schema_yaml = Path(__file__).resolve().parent / f"{schema_dir_name}/{schema_file_name}"
schema_map = schema_maps.load_schema_map(SURVEY, TESTID, schema=path_to_local_schema_yaml)


def run(msg: dict, context: functions_v1.context.Context) -> None:
    """Send alert data to various BigQuery tables.

    Args:
        msg: Pub/Sub message data and attributes.
            `data` field contains the message data in a base64-encoded string.
            `attributes` field contains the message's custom attributes in a dict.

        context: Metadata describing the Cloud Function's trigging event.
    """
    # extract the alert
    alert_dict = data_utils.open_alert(
        base64.b64decode(msg["data"]), drop_cutouts=False, schema_map=schema_map
    )
    
    # send the alert to BigQuery tables
    alert_table = insert_rows_alerts(alert_dict)

    # announce what's been done
    publish_pubsub(alert_dict, [alert_table])


def insert_rows_alerts(alert_dict: dict):
    """Insert rows into the `alerts` table via the streaming API."""
    # send to bigquery
    table_id = f"{bq_dataset}.alerts_{VERSIONTAG}"
    errors = gcp_utils.insert_rows_bigquery(table_id, [alert_dict])

    # handle errors; if none, save table id for Pub/Sub message
    if len(errors) == 0:
        table_dict = {"alerts_table": f"{PROJECT_ID}:{table_id}"}
    else:
        msg = f"Error inserting to alerts table: {errors}"
        logger.log_text(msg, severity="DEBUG")
        table_dict = {"alerts_table": None}

    return table_dict


def publish_pubsub(alert_dict: dict, table_dicts: Dict[str, Optional[dict]]):
    """Announce the table storage operation to Pub/Sub."""
    # collect attributes
    attrs = {
        schema_map["objectId"]: str(alert_dict[schema_map["objectId"]]),
        schema_map["url"]: str(alert_dict[schema_map["url"]]),
        schema_map["type"]: str(alert_dict[schema_map["type"]]),
    }
    for d in table_dicts:
        for k, v in d.items():
            attrs[k] = str(v) if v is not None else ""

    # set empty message body; everything is in the attributes
    msg = b""

    # publish
    gcp_utils.publish_pubsub(ps_topic, msg, attrs=attrs)
