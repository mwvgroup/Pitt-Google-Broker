#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Filter alerts for purity."""


import base64
import os
import numpy as np
from google.cloud import logging
from astropy import units as u

# Add these to requirements.txt but check to make sure that the format of adding is correct
from broker_utils import data_utils, gcp_utils, schema_maps, types


PROJECT_ID = os.getenv("GCP_PROJECT")  # For local test set this to GOOGLE_CLOUD_PROJECT


# This returns a string which is configured when the broker
# instance is initially set up. When we create resources
# in the cloud, we need unique test names.
# (i.e. This is an input variable to the setup script)
# We cannot have separate pub/sub streams with the same
# name, (i.e. is_pure), so the testID is appended
# to all the resource names for the instance you set up
# (When we deploy to the cloud we set up a broker instance).
TESTID = os.getenv("TESTID")

SURVEY = os.getenv("SURVEY")  # This will return ztf (in future will be our LSST)

# connect to the logger
logging_client = logging.Client()
LOG_NAME = "filter-purity"  # same log for all broker instances
logger = logging_client.logger(LOG_NAME)

# GCP resources used in this module
bq_dataset = f"{SURVEY}_alerts"


# This is the name of the Pub/Sub topic that this
# module publishes to. (Publishes original alert
# plus its own results. The next module downstream
# in the pipeline will listen to this topic)
ps_topic = f"{SURVEY}-lite"

if TESTID != "False":  # attach the testid to the names
    bq_dataset = f"{bq_dataset}_{TESTID}"
    ps_topic = f"{ps_topic}-{TESTID}"


def semantic_compression(alert_dict, schema_map) -> dict:

    source = alert_dict[schema_map["source"]]

    # NEED FILTER MAP FOR _format_for_snn IN classify_snn
    # ALSO NEED mag, magzp, magerr FOR _format_for_snn IN classify_snn

    # FOR tag function WE NEED A WAY TO CHECK THE SURVEY (ZTF, DECAT, ETC)
    # ALSO NEED TO DETERMINE WHETHER TO CHANGE data_utils.alert_dict_to_dataframe()
    # TO NOT RELY ON schema_maps

    # Will probably be better to leave the types the way they are
    # in the packet
    source_dict = {
        "jd": source["jd"],
        "sourceId": source["candid"],  # candid some might make an int others a string
        "ra": source["ra"],
        "dec": source["dec"],
        "magpsf": source["magpsf"],
        "sigmapsf": source["sigmapsf"],
        "magzpsci": source["magzpsci"],
        "magzpsciunc": source["magzpsciunc"],
        "diffmaglim": source["diffmaglim"],
        "isdiffpos": source["isdiffpos"],
        "rb": source["rb"],  # RealBogus score
        "drb": source["drb"],
        # HAD TO ADD THESE FOR PURITY REASON DICT
        "nbad": source["nbad"],
        "fwhm": source["fwhm"],
        "elong": source["elong"],
        "magdiff": source["magdiff"],
        "fid": source["fid"],
    }

    access_prev = alert_dict[schema_map["prvSources"]]

    prev_sources = []

    for prv_s in access_prev:

        prev_source_dict = {
            "prv_jd": prv_s["jd"],
            "prv_candid": prv_s["candid"],
            "prv_ra": prv_s["ra"],
            "prv_dec": prv_s["dec"],
            "prv_magpsf": prv_s["magpsf"],
            "prv_sigmapsf": prv_s["sigmapsf"],
            "prv_magzpsci": prv_s["magzpsci"],
            "prv_magzpsciunc": prv_s["magzpsciunc"],
            "prv_diffmaglim": prv_s["diffmaglim"],
            "prv_isdiffpos": prv_s["isdiffpos"],
            # HAD TO ADD THESE FOR PURITY REASON DICT
            "prv_nbad": source["nbad"],
            "prv_fwhm": source["fwhm"],
            "prv_elong": source["elong"],
            "prv_magdiff": source["magdiff"],
            "prv_fid": source["fid"],
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
        # This extracts alert ids. This is a named tuple it contains all of the ids
        "alertIds": types.AlertIds(schema_map, alert_dict=alert_dict).ids._asdict(),
        "source": source_dict,
        "prvSources": tuple(prev_sources),  # name of prvSources style may be changed
        "xmatch": xmatch,
    }

    return alert_lite


def run(msg: dict, context):
    """Filter alerts for purity and extragalctic transient, publish results.

    For args descriptions, see:
    https://cloud.google.com/functions/docs/writing/background#function_parameters

    Args:
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

    # This is pulling from a bucket in the cloud
    schema_map = schema_maps.load_schema_map(SURVEY, TESTID)

    # logger.log_text(f"{type(msg['data'])}', severity='DEBUG")
    # logger.log_text(f"{msg['data']}', severity='DEBUG")

    alert_dict = data_utils.open_alert(
        msg["data"], drop_cutouts=True, schema_map=schema_map
    )  # this decodes the alert

    alert_lite = semantic_compression(alert_dict, schema_map)

    attrs = {
        "objectId": str(alert_lite["alertIds"]["objectId"]),
        "candid": str(alert_lite["alertIds"]["sourceId"]),
    }  # this gets the custom attr for filtering

    # # run the alert through the filter.

    # # Publish to Pub/Sub:
    # gcp_utils.publish_pubsub(ps_topic, alert_dict, attrs=attrs)
    #
    gcp_utils.publish_pubsub(
        ps_topic,
        alert_lite,
        attrs=attrs,
    )
