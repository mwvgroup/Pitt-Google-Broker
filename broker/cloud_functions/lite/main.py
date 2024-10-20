#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Create a "lite" alert containing the subset of fields necessary for broker and downstream."""
import os

from google.cloud import logging

from broker_utils import data_utils, gcp_utils, schema_maps, types


PROJECT_ID = os.getenv("GCP_PROJECT")  # For local test set this to GOOGLE_CLOUD_PROJECT
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# connect to the logger
logging_client = logging.Client()
LOG_NAME = "lite-cloudfnc"  # same log for all broker instances
logger = logging_client.logger(LOG_NAME)

# GCP resources used in this module
ps_topic = f"{SURVEY}-lite"
if TESTID != "False":  # attach the testid to the names
    ps_topic = f"{ps_topic}-{TESTID}"


def semantic_compression(alert_dict, schema_map) -> dict:
    """Construct and return the `alert_lite` dictionary."""

    source = alert_dict[schema_map["source"]]

    source_dict = {
        "jd": source["jd"],
        "sourceId": source[schema_map["sourceId"]],
        "ra": source["ra"],
        "dec": source["dec"],
        # for classify_snn
        "mag": source[schema_map["mag"]],
        "magerr": source[schema_map["magerr"]],
        "magzp": source[schema_map["magzp"]],
        "magzpsciunc": source["magzpsciunc"],
        "diffmaglim": source["diffmaglim"],
        # for tag
        "isdiffpos": source["isdiffpos"],
        "rb": source["rb"],
        "drb": source["drb"],
        "nbad": source["nbad"],
        "fwhm": source["fwhm"],
        "elong": source["elong"],
        "magdiff": source["magdiff"],
        "filter": source[schema_map["filter"]],
    }

    access_prev = alert_dict.get(schema_map["prvSources"], {})

    prev_sources = []

    for prv_s in access_prev:

        prev_source_dict = {
            "jd": prv_s["jd"],
            "sourceId": prv_s[schema_map["sourceId"]],
            "ra": prv_s["ra"],
            "dec": prv_s["dec"],
            # for classify_snn
            "mag": prv_s[schema_map["mag"]],
            "magerr": prv_s[schema_map["magerr"]],
            "magzp": prv_s[schema_map["magzp"]],
            "magzpsciunc": prv_s["magzpsciunc"],
            "diffmaglim": prv_s["diffmaglim"],
            # for tag
            "isdiffpos": prv_s["isdiffpos"],
            "rb": prv_s["rb"],
            "nbad": prv_s["nbad"],
            "fwhm": prv_s["fwhm"],
            "elong": prv_s["elong"],
            "magdiff": prv_s["magdiff"],
            "filter": prv_s[schema_map["filter"]],
        }

        prev_sources.append(prev_source_dict)

    xmatch = {
        "ssdistnr": source["ssdistnr"],
        "ssmagnr": source["ssmagnr"],
        "objectidps1": source["objectidps1"],
        "distpsnr1": source["distpsnr1"],
        "sgscore1": source["sgscore1"],
        "objectidps2": source["objectidps2"],
        "distpsnr2": source["distpsnr2"],
        "sgscore2": source["sgscore2"],
        "objectidps3": source["objectidps3"],
        "distpsnr3": source["distpsnr3"],
        "sgscore3": source["sgscore3"],
    }

    alert_lite = {
        "alertIds": types.AlertIds(schema_map, alert_dict=alert_dict).ids._asdict(),
        "source": source_dict,
        "prvSources": tuple(prev_sources),
        "xmatch": xmatch,
    }

    return alert_lite


def run(msg: dict, context):
    """Create a "lite" alert containing the subset of fields necessary for broker and downstream.

    Both parameters are required by Cloud Functions, regardless of whether they are used.
    For parameter descriptions, see:
    https://cloud.google.com/functions/docs/writing/background#function_parameters

    Parameters:
        msg: Pub/Sub message data and attributes.
            `data` field contains the message data in a base64-encoded string.
            `attributes` field contains the message's custom attributes in a dict.

        context: The Cloud Function's event metadata.
            It has the following attributes:
                `event_id`: the Pub/Sub message ID.
                `timestamp`: the Pub/Sub message publish time.
                `event_type`: for example: "google.pubsub.topic.publish".
                `resource`: the resource that emitted the event.
    """
    schema_map = schema_maps.load_schema_map(SURVEY, TESTID)

    alert_dict = data_utils.open_alert(msg["data"], drop_cutouts=True, schema_map=schema_map)

    alert_lite = semantic_compression(alert_dict, schema_map)

    attrs = {
        "objectId": str(alert_lite["alertIds"]["objectId"]),
        "candid": str(alert_lite["alertIds"]["sourceId"]),
    }

    gcp_utils.publish_pubsub(ps_topic, alert_lite, attrs=attrs)
