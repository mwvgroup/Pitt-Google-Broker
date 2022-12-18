#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Filter alerts for purity."""

import os

import numpy as np
from astropy import units as u
from google.cloud import logging

from broker_utils import data_utils, gcp_utils


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
ps_topic = f"{SURVEY}-tagged"

if TESTID != "False":  # attach the testid to the names
    bq_dataset = f"{bq_dataset}_{TESTID}"
    ps_topic = f"{ps_topic}-{TESTID}"


# Changed the name stub of the BigQuery table from SuperNNova to classifications
class_table = f"{bq_dataset}.classifications"

tags_table = f"{bq_dataset}.tags"


def is_pure(alert_dict):
    """Adapted from: https://zwickytransientfacility.github.io/ztf-avro-alert/filtering.html

    Quoted from the source:

    ZTF alert streams contain an nearly entirely unfiltered stream of all
    5-sigma (only the most obvious artefacts are rejected). Depending on your
    science case, you may wish to improve the purity of your sample by filtering
    the data on the included attributes.

    Based on tests done at IPAC (F. Masci, priv. comm), the following filter
    delivers a relatively pure sample.
    """

    source = alert_dict["source"]

    rb = source["rb"] >= 0.65  # RealBogus score

    if SURVEY == "decat":  ## How to get find survey type without schema_map
        pure = rb

    elif SURVEY == "ztf":  ## How to get find survey type without schema_map
        nbad = source["nbad"] == 0  # num bad pixels
        fwhm = source["fwhm"] <= 5  # Full Width Half Max, SExtractor [pixels]
        elong = source["elong"] <= 1.2  # major / minor axis, SExtractor
        magdiff = abs(source["magdiff"]) <= 0.1  # aperture - psf [mag]
        pure = rb and nbad and fwhm and elong and magdiff

    purity_reason_dict = {
        "is_pure": int(pure),
        "rb": int(rb),
        "nbad": int(nbad),
        "fwhm": int(fwhm),
        "elong": int(elong),
        "magdiff": int(magdiff),
    }

    return purity_reason_dict


def _is_extragalactic_transient(alert_dict: dict) -> dict:
    """Check whether alert is likely to be an extragalactic transient.
    Adapted from:
    https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    if SURVEY == "decat":  ## How to get find survey type without schema_map
        # No straightforward way to translate this ZTF filter for DECAT.
        # DECAT alert does not include whether the subtraction (sci-ref) is
        # positive, nor SExtractor results,
        # and the included xmatch data is significantly different.
        # However, DECAT is a transient survey.
        # Assume the alert should pass the filter:
        is_extragalactic_transient = True

    elif SURVEY == "ztf":  ## How to get find survey type without schema_map
        dflc = data_utils.alert_lite_to_dataframe(
            alert_dict
        )  # Is schema_map necessary for this function?
        # NEED TO GO TO data_utils.py and determine whether to take out schema map

        candidate = dflc.loc[0]

        is_positive_sub = candidate["isdiffpos"] == "t"
        distpsnr1 = alert_dict["xmatch"]["distpsnr1"]
        sgscore1 = alert_dict["xmatch"]["sgscore1"]
        ssdistnr = alert_dict["xmatch"]["ssdistnr"]
        if (distpsnr1 is None) or (distpsnr1 > 1.5):  # arcsec
            no_pointsource_counterpart = True
            # closest candidate == star < 1.5 arcsec away -> candidate probably star
        else:
            no_pointsource_counterpart = sgscore1 < 0.5

        where_detected = dflc["isdiffpos"] == "t"
        if np.sum(where_detected) >= 2:
            detection_times = dflc.loc[where_detected, "jd"].values
            dt = np.diff(detection_times)
            not_moving = np.max(dt) >= (30 * u.minute).to(u.day).value
        else:
            not_moving = False

        no_ssobject = (ssdistnr is None) or (ssdistnr < 0) or (ssdistnr > 5)
        # candidate['ssdistnr'] == -999 is another encoding of None

        is_extragalactic_transient = (
            is_positive_sub and no_pointsource_counterpart and not_moving and no_ssobject
        )

    exgalac_dict = {
        "is_extragalactic_transient": int(is_extragalactic_transient),
        "is_positive_sub": int(is_positive_sub),
        "no_pointsource_counterpart": int(no_pointsource_counterpart),
        "not_moving": int(not_moving),
        "no_ssobject": int(no_ssobject),
    }

    return exgalac_dict


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

    alert_lite = data_utils.open_alert(msg["data"])

    attrs = msg["attributes"]  # this gets the custom attr for filtering

    purity_reason_dict = is_pure(alert_lite)

    extragalactic_dict = _is_extragalactic_transient(alert_lite)  ## ADDED

    # # run the alert through the filter.

    # # Publish to Pub/Sub:
    # gcp_utils.publish_pubsub(ps_topic, alert_dict, attrs=attrs)
    #
    gcp_utils.publish_pubsub(
        ps_topic,
        alert_lite,
        attrs={
            **attrs,
            **{k: str(v) for k, v in purity_reason_dict.items()},
            **{k: str(v) for k, v in extragalactic_dict.items()},
            "fid": str(alert_lite["source"]["fid"]),
        },
    )

    # # store results to BigQuery, regardless of whether it passes the filter
    tags_dict = {
        **attrs,
        "classifier_version": 0.1,
        **purity_reason_dict,
        **extragalactic_dict,
    }

    errors = gcp_utils.insert_rows_bigquery(tags_table, [tags_dict])
    if len(errors) > 0:
        logger.log_text(f"BigQuery insert error: {errors}", severity="WARNING")

    # # store results to BigQuery, regardless of whether it passes the filter
    classifications = [
        {
            # **attrs: objectId and candid (sourceId, but renamed for bigquery)
            # (same thing as candId, but we call it a sourceId in our internal
            # broker) [** is a splat, it takes the elements from attrs dict
            # and unpacks it and passes it to the new dict constr, and passes
            # it as individual elements]
            "objectId": attrs["objectId"],
            "candid": attrs["candid"],
            "classifier": "purity",
            "classifier_version": 0.1,
            "class": purity_reason_dict["is_pure"],
        },
        {
            "objectId": attrs["objectId"],
            "candid": attrs["candid"],
            "classifier": "extragalactic_transient",
            "classifier_version": 0.1,
            "class": extragalactic_dict["is_extragalactic_transient"],
        },
    ]

    errors = gcp_utils.insert_rows_bigquery(class_table, classifications)
    if len(errors) > 0:
        logger.log_text(f"BigQuery insert error: {errors}", severity="WARNING")
