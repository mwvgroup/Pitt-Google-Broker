#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Filter alerts for likely extragalactic transients."""

import astropy.units as u
import base64
from google.cloud import logging
import numpy as np
import os

from broker_utils import data_utils, gcp_utils, schema_maps


PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# connect to the logger
logging_client = logging.Client()
log_name = "filter-exgalac-trans-cloudfnc"  # same log for all broker instances
logger = logging_client.logger(log_name)

# GCP resources used in this module
ps_topic = f"{SURVEY}-exgalac_trans_cf"
if TESTID != "False":  # attach the testid to the names
    ps_topic = f"{ps_topic}-{TESTID}"

schema_map = schema_maps.load_schema_map(SURVEY, TESTID)


def run(msg: dict, context) -> None:
    """Filter for likely extragalactic transients, publish results.

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
    # logger.log_text(f"{type(msg['data'])}', severity='DEBUG")
    # logger.log_text(f"{msg['data']}', severity='DEBUG")

    alert_dict = data_utils.decode_alert(
        base64.b64decode(msg["data"]), drop_cutouts=True, schema_map=schema_map
    )
    attrs = {
        schema_map["objectId"]: str(alert_dict[schema_map["objectId"]]),
        schema_map["sourceId"]: str(alert_dict[schema_map["sourceId"]]),
    }

    if _is_extragalactic_transient(alert_dict):
        gcp_utils.publish_pubsub(ps_topic, alert_dict, attrs=attrs)


def _is_extragalactic_transient(alert_dict: dict) -> bool:
    """Check whether alert is likely to be an extragalactic transient.

    Adapted from:
    https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    if schema_map["SURVEY"] == "decat":
        # No straightforward way to translate this ZTF filter for DECAT.
        # DECAT alert does not include whether the subtraction (sci-ref) is
        # positive, nor SExtractor results,
        # and the included xmatch data is significantly different.
        # However, DECAT is a transient survey.
        # Assume the alert should pass the filter:
        is_extragalactic_transient = True

    elif schema_map["SURVEY"] == "ztf":
        dflc = data_utils.alert_dict_to_dataframe(alert_dict, schema_map)
        candidate = dflc.loc[0]

        is_positive_sub = candidate["isdiffpos"] == "t"

        if (candidate["distpsnr1"] is None) or (candidate["distpsnr1"] > 1.5):  # arcsec
            no_pointsource_counterpart = True
            # closest candidate == star < 1.5 arcsec away -> candidate probably star
        else:
            no_pointsource_counterpart = candidate["sgscore1"] < 0.5

        where_detected = dflc["isdiffpos"] == "t"
        if np.sum(where_detected) >= 2:
            detection_times = dflc.loc[where_detected, "jd"].values
            dt = np.diff(detection_times)
            not_moving = np.max(dt) >= (30 * u.minute).to(u.day).value
        else:
            not_moving = False

        no_ssobject = (
            (candidate["ssdistnr"] is None)
            or (candidate["ssdistnr"] < 0)
            or (candidate["ssdistnr"] > 5)
        )
        # candidate['ssdistnr'] == -999 is another encoding of None

        is_extragalactic_transient = (
            is_positive_sub
            and no_pointsource_counterpart
            and not_moving
            and no_ssobject
        )

    return is_extragalactic_transient
