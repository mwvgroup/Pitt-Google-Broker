#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Identify basic categorizations; publish results to BigQuery and as Pub/Sub messsage attributes."""

import os
import numpy as np
from typing import Dict
from astropy import units as u
from google.cloud import logging
import pittgoogle
import flask

# [FIXME] Make this helpful or else delete it.
# Connect the python logger to the google cloud logger. By default, this captures INFO level and above. pittgoogle uses
# the Python logger. We don't currently use the python logger directly in this script, but we could.
logging.Client().setup_logging()

# --- Variables for incoming data
# A url route is used in setup.sh when the trigger subscription is created. It is possible to define multiple routes
# in a single module and trigger them using different subscriptions.
ROUTE_RUN = "/"  # HTTP route that will trigger run(). Must match deploy.sh
# --- Variables for outgoing data
HTTP_204 = 204  # HTTP code: Success
HTTP_400 = 400  # HTTP code: Bad Request

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# --- GCP resources used in this module
TABLE_CLASSIFICATIONS = pittgoogle.Table.from_cloud(
    "classifications", survey=SURVEY, testid=TESTID
)
TABLE_TAGS = pittgoogle.Table.from_cloud("tags", survey=SURVEY, testid=TESTID)
TOPIC = pittgoogle.Topic.from_cloud("tagged", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID)

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run():
    """Identify basic categorizations; publish results to BigQuery and as Pub/Sub msg attributes. Messages in this
    stream retain fields from the original alert packet.

    This module is intended to be deployed as a Cloud Run service. It will operate as an HTTP endpoint triggered by
    Pub/Sub messages. This function will be called once for every message sent to this route. It should accept the
    incoming HTTP request and return a response.

    Returns
    -------
    response : tuple(str, int)
        Tuple containing the response body (string) and HTTP status code (int). Flask will convert the tuple into a
        proper HTTP response. Note that the response is a status message for the web server.
    """
    # extract the envelope from the request that triggered the endpoint
    # this contains a single Pub/Sub message with the alert to be processed
    envelope = flask.request.get_json()
    try:
        alert = pittgoogle.Alert.from_cloud_run(envelope, schema_name="ztf")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    purity_reason_dict = _is_pure(alert)
    extragalactic_dict = _is_extragalactic_transient(alert)
    tagged_alert = pittgoogle.Alert.from_dict(
        payload=alert.dict,
        attributes={
            **alert.attributes,
            **{k: v for k, v in purity_reason_dict.items()},
            **{k: v for k, v in extragalactic_dict.items()},
            "fid": alert.get("source")["fid"],
        },
        schema_name="ztf",
    )

    TOPIC.publish(tagged_alert)

    # store in BigQuery
    TABLE_TAGS.insert_rows(
        [
            {
                "objectId": alert.objectid,
                "candid": alert.sourceid,
                "classifier_version": 0.1,
                **purity_reason_dict,
                **extragalactic_dict,
            }
        ]
    )
    TABLE_CLASSIFICATIONS.insert_rows(
        [
            {
                "objectId": alert.objectid,
                "candid": alert.sourceid,
                "classifier": "purity",
                "classifier_version": 0.1,
                "class": purity_reason_dict["is_pure"],
            },
            {
                "objectId": alert.objectid,
                "candid": alert.sourceid,
                "classifier": "extragalactic_transient",
                "classifier_version": 0.1,
                "class": extragalactic_dict["is_extragalactic_transient"],
            },
        ]
    )

    return "", HTTP_204


def _is_pure(alert: pittgoogle.Alert) -> Dict:
    """Adapted from: https://zwickytransientfacility.github.io/ztf-avro-alert/filtering.html

    Quoted from the source:
    ZTF alert streams contain an nearly entirely unfiltered stream of all 5-sigma (only the most obvious artefacts are
    rejected). Depending on your science case, you may wish to improve the purity of your sample by filtering the data
    on the included attributes.

    Based on tests done at IPAC (F. Masci, priv. comm), the following filter delivers a relatively pure sample.
    """

    source = alert.get("source")
    rb = source["rb"] >= 0.65  # RealBogus score

    if SURVEY == "decat":
        pure = rb
    else:
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


def _is_extragalactic_transient(alert: pittgoogle.Alert) -> Dict:
    """Adapted from:
    https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb

    Check whether alert is likely to be an extragalactic transient.
    """
    if SURVEY == "decat":
        # No straightforward way to translate this ZTF filter for DECAT. DECAT alert does not include whether the
        # subtraction (sci-ref) is positive, nor SExtractor results, and the included xmatch data is significantly
        # different. However, DECAT is a transient survey. Assume the alert should pass the filter:
        is_extragalactic_transient = True

    else:
        dflc = alert.dataframe
        candidate = dflc.loc[0]

        # include both encodings of a positive image subtraction (sci minus ref)
        is_positive_sub = candidate["isdiffpos"] in ["t", 1]
        distpsnr1 = alert.get("source")["distpsnr1"]
        sgscore1 = alert.get("source")["sgscore1"]
        ssdistnr = alert.get("source")["ssdistnr"]
        if (distpsnr1 is None) or (distpsnr1 > 1.5):  # arcsec
            # closest candidate == star < 1.5 arcsec away => candidate probably star
            no_pointsource_counterpart = True
        else:
            no_pointsource_counterpart = sgscore1 < 0.5

        where_detected = dflc["isdiffpos"] == "t"
        if np.sum(where_detected) >= 2:
            detection_times = dflc.loc[where_detected, "jd"].values
            dt = np.diff(detection_times)
            not_moving = np.max(dt) >= (30 * u.minute).to(u.day).value
        else:
            not_moving = False
        # candidate['ssdistnr'] == -999 is another encoding of None
        no_ssobject = (ssdistnr is None) or (ssdistnr < 0) or (ssdistnr > 5)
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
