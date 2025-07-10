#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Create a "lite" alert containing the subset of fields necessary for broker and downstream."""

import os
from typing import Dict, List, Optional
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
TOPIC = pittgoogle.Topic.from_cloud("lite", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID)

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run() -> tuple[str, int]:
    """Produces a 'lite' alert stream (${survey}-lite). Messages in this stream contain a subset of fields
    from the original alert packet.

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

    TOPIC.publish(_create_lite_alert(alert))

    return "", HTTP_204


def _create_lite_alert(alert: pittgoogle.Alert) -> pittgoogle.Alert:
    """Creates a "lite" alert containing a subset of the fields of the original alert packet."""

    # create a list of field names that will be included in a lite dictionary
    source_fields_list = _get_fields(field_name=alert.get_key("source"))
    xmatch_fields_list = _get_fields(field_name="xmatch")

    # create lite dictionaries for each of the fields that will be included in the lite alert
    prev_sources_lite_dict = _create_prv_sources_lite_dict(
        alert.dict.get(alert.get_key("prv_sources")), source_fields_list
    )
    source_lite_dict = _create_lite_dict(
        alert.dict.get(alert.get_key("source")), source_fields_list
    )
    xmatch_dict = _create_lite_dict(alert.dict.get(alert.get_key("source")), xmatch_fields_list)

    # create the lite dictionary for the outgoing alert
    alert_lite_dict = {
        "alert_lite": {
            alert.get_key("objectid"): alert.objectid,
            alert.get_key("sourceid"): alert.sourceid,
            alert.get_key("source"): source_lite_dict,
            alert.get_key("prv_sources"): tuple(prev_sources_lite_dict),
        },
        "xmatch": xmatch_dict,
    }

    return pittgoogle.Alert.from_dict(
        payload=alert_lite_dict,
        attributes={**alert.attributes},
    )


def _get_fields(field_name: str) -> list[str]:
    """Returns a list of survey-specific field names that will be included in a lite dictionary."""

    if field_name == "candidate":
        source_fields_list = [
            "jd",
            "candid",
            "ra",
            "dec",
            # for classify_snn
            "magpsf",
            "sigmapsf",
            "magzpsci",
            "magzpsciunc",
            "diffmaglim",
            # for tag
            "isdiffpos",
            "rb",
            "drb",
            "nbad",
            "fwhm",
            "elong",
            "magdiff",
            "fid",
        ]

        return source_fields_list

    if field_name == "xmatch":
        xmatch_fields_list = [
            "ssdistnr",
            "ssmagnr",
            "objectidps1",
            "distpsnr1",
            "sgscore1",
            "objectidps2",
            "distpsnr2",
            "sgscore2",
            "objectidps3",
            "distpsnr3",
            "sgscore3",
        ]

        return xmatch_fields_list

    raise ValueError(
        f"Unrecognized field type: {field_name}. Only 'candidate', and 'xmatch' are supported."
    )


def _create_lite_dict(alert_dict: dict, field_names: list[str]) -> dict:
    """Returns a lite dictionary containing fields specified in field_names."""
    if alert_dict is None:
        return alert_dict
    return {k: v for k, v in alert_dict.items() if k in field_names}


def _create_prv_sources_lite_dict(
    source_history: Optional[List[Dict]], field_names: List[str]
) -> Optional[List[Dict]]:
    """Create a list of prv_sources lite dictionaries if prv_sources exist."""

    if source_history is None:
        return source_history

    prev_sources = []
    for prv_s in source_history:
        lite_source_dict = _create_lite_dict(prv_s, field_names)
        prev_sources.append(lite_source_dict)

    return prev_sources
