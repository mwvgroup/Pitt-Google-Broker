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

path_to_local_schema_yaml = Path(__file__).resolve().parent / f"{SURVEY}.yaml"
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
        base64.b64decode(msg["data"]), drop_cutouts=True, schema_map=schema_map
    )

    # send the alert to BigQuery tables
    alert_table = insert_rows_alerts(alert_dict)
    source_table = insert_rows_DIASource(alert_dict)

    # announce what's been done
    publish_pubsub(alert_dict, [alert_table, source_table])


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


def insert_rows_DIASource(alert_dict: dict):
    """Insert rows into the `DIASource` table via the streaming API."""
    table_id = f"{bq_dataset}.DIASource"

    # extract the DIA source data
    if SURVEY == "ztf":
        source_dict = _extract_ztf_source(alert_dict)
    elif SURVEY == "decat":
        source_dict = _extract_decat_source(alert_dict)

    # send to bigquery
    errors = gcp_utils.insert_rows_bigquery(table_id, [source_dict])

    # handle errors; if none, save table id for Pub/Sub message
    if len(errors) == 0:
        table_dict = {"DIASource_table": f"{PROJECT_ID}:{table_id}"}
    else:
        msg = f"Error inserting to DIASource table: {errors}"
        logger.log_text(msg, severity="DEBUG")
        table_dict = {"DIASource_table": None}

    return table_dict


def _extract_ztf_source(alert_dict: dict):
    # get candidate
    dup_cols = ["candid"]  # candid is repeated, drop the one nested here
    cand = {k: v for k, v in alert_dict["candidate"].items() if k not in dup_cols}

    # get info for provenance
    metakeys = ["schemavsn", "publisher", "objectId", "candid"]
    metadict = {k: v for k, v in alert_dict.items() if k in metakeys}

    # get string of previous candidates' candid, comma-separated
    if alert_dict["prv_candidates"] is not None:
        prv_candids = ",".join(
            str(pc["candid"])
            for pc in alert_dict["prv_candidates"]
            if pc["candid"] is not None
        )
    else:
        prv_candids = None

    # package it up and return
    source_dict = {**metadict, **cand, "prv_candidates_candids": prv_candids}
    return source_dict


def _extract_decat_source(alert_dict: dict):
    # get source
    dup_cols = ["ra", "dec"]  # names duplicated in object and source levels

    def sourcename(c):
        return c if c not in dup_cols else f"source_{c}"

    src = {sourcename(k): v for k, v in alert_dict["triggersource"].items()}

    # get info for provenance
    notmetakeys = ["triggersource", "sources"]
    metadict = {k: v for k, v in alert_dict.items() if k not in notmetakeys}

    # get string of previous sources' sourceid, comma-separated
    if alert_dict["sources"] is not None:
        tmp = [ps["sourceid"] for ps in alert_dict["sources"]]
        prv_sources = ",".join([f"{sid}" for sid in tmp if sid is not None])
    else:
        prv_sources = None

    # package it up and return
    source_dict = {**metadict, **src, "sources_sourceids": prv_sources}
    return source_dict


def publish_pubsub(alert_dict: dict, table_dicts: Dict[str, Optional[dict]]):
    """Announce the table storage operation to Pub/Sub."""
    # collect attributes
    attrs = {
        schema_map["objectId"]: str(alert_dict[schema_map["objectId"]]),
        schema_map["sourceId"]: str(alert_dict[schema_map["sourceId"]]),
    }
    for d in table_dicts:
        attrs.update(d)

    # set empty message body; everything is in the attributes
    msg = b""

    # publish
    gcp_utils.publish_pubsub(ps_topic, msg, attrs=attrs)
