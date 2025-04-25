#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module creates a "lite" alert containing a subset of fields from the original alert packet."""

import os
from typing import Optional

import flask
import pittgoogle
from google.cloud import logging

# [FIXME] Make this helpful or else delete it.
# Connect the python logger to the google cloud logger.
# By default, this captures INFO level and above.
# pittgoogle uses the python logger.
# We don't currently use the python logger directly in this script, but we could.
logging.Client().setup_logging()

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# Variables for incoming data
# A url route is used in setup.sh when the trigger subscription is created.
# It is possible to define multiple routes in a single module and trigger them using different subscriptions.
ROUTE_RUN = "/"  # HTTP route that will trigger run(). Must match deploy.sh

# Variables for outgoing data
HTTP_204 = 204  # HTTP code: Success
HTTP_400 = 400  # HTTP code: Bad Request

# GCP resources used in this module
TOPIC_LITE = pittgoogle.Topic.from_cloud(
    "lite", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run():
    """Produces a 'lite' alert stream (${survey}-lite). Messages in this stream contain a subset of fields
    from the original alert packet.

    This module is intended to be deployed as a Cloud Run service. It will operate as an HTTP endpoint
    triggered by Pub/Sub messages. This function will be called once for every message sent to this route.
    It should accept the incoming HTTP request and return a response.

    Returns
    -------
    response : tuple(str, int)
        Tuple containing the response body (string) and HTTP status code (int). Flask will convert the
        tuple into a proper HTTP response. Note that the response is a status message for the web server.
    """
    # extract the envelope from the request that triggered the endpoint
    # this contains a single Pub/Sub message with the alert to be processed
    envelope = flask.request.get_json()
    try:
        alert = pittgoogle.Alert.from_cloud_run(envelope, f"{SURVEY}")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    TOPIC_LITE.publish(_create_lite_alert(alert), serializer="json")

    return "", HTTP_204


def _create_lite_alert(alert: pittgoogle.Alert) -> pittgoogle.Alert:
    """Create a "lite" alert containing a subset of the fields of the original alert packet."""

    # define the fields that will be present in the lite alert
    source_fields_list = _create_fields_list(field="source")
    object_fields_list = _create_fields_list(field="object")
    ss_object_fields_list = _create_fields_list(field="ssobject")

    # create lite versions of fields in the original alert packet
    object_lite_dict = _create_lite_dict(
        alert.dict.get(alert.get_key("object")), object_fields_list
    )
    prev_sources_lite_dict = _create_prv_sources_lite_dict(
        alert.dict.get(alert.get_key("prv_sources")), source_fields_list
    )
    source_lite_dict = _create_lite_dict(
        alert.dict.get(alert.get_key("source")), source_fields_list
    )
    ssobject_lite_dict = _create_lite_dict(
        alert.dict.get(alert.get_key("ss_object")), ss_object_fields_list
    )
    # create lite dictionary
    alert_lite_dict = {
        alert.get_key("alertid"): alert.alertid,
        alert.get_key("source"): source_lite_dict,
        alert.get_key("prv_sources"): prev_sources_lite_dict,
        "prvDiaForcedSources": alert.dict.get("prvDiaForcedSources"),
        "prvDiaNondetectionLimits": alert.dict.get("prvDiaNondetectionLimits"),
        alert.get_key("object"): object_lite_dict,
        alert.get_key("ss_object"): ssobject_lite_dict,
    }

    return pittgoogle.Alert.from_dict(payload=alert_lite_dict, schema_name=f"{SURVEY}")


def _create_fields_list(field: str) -> list[str]:
    """Creates a list of survey-specific field names that will be included in the lite dictionary."""
    if field == "source":
        source_fields_list = [
            "diaSourceId",
            "midpointMjdTai",
            "ra",
            "raErr",
            "dec",
            "decErr",
            "psfFlux",
            "psfFluxErr",
            "band",
        ]

        return source_fields_list

    elif field == "object":
        object_fields_list = [
            "diaObjectId",
            "nearbyObj1",
            "nearbyObj2",
            "nearbyObj3",
            "nearbyObj1Dist",
            "nearbyObj2Dist",
            "nearbyObj3Dist",
            "nearbyObj1LnP",
            "nearbyObj2LnP",
            "nearbyObj3LnP",
            "u_psfFluxErrMean",
            "g_psfFluxErrMean",
            "r_psfFluxErrMean",
            "i_psfFluxErrMean",
            "z_psfFluxErrMean",
            "y_psfFluxErrMean",
        ]

        return object_fields_list

    elif field == "ssobject":
        ss_object_fields_list = [
            "ssObjectId",
            "firstObservationDate",
            "arc",
            "numObs",
            "MOID",
            "MOIDEclipticLongitude",
            "MOIDDeltaV",
            "u_H",
            "u_HErr",
            "u_Chi2",
            "g_H",
            "g_HErr",
            "g_Chi2",
            "r_H",
            "r_HErr",
            "r_Chi2",
            "i_H",
            "i_HErr",
            "i_Chi2",
            "z_H",
            "z_HErr",
            "z_Chi2",
            "y_H",
            "y_HErr",
            "y_Chi2",
            "medianExtendedness",
        ]

        return ss_object_fields_list


def _create_lite_dict(alert_dict: dict, field_names: list[str]) -> dict:
    """Returns a lite dictionary containing fields specified in field_names."""
    if alert_dict is None:
        return alert_dict
    return {k: v for k, v in alert_dict.items() if k in field_names}


def _create_prv_sources_lite_dict(
    source_history: list[dict], field_names: list[str]
) -> Optional[list[dict]]:
    """Create a list of prv_sources lite dictionaries if prv_sources exist."""

    if source_history is None:
        return source_history

    prev_sources = []
    for prv_s in source_history:
        lite_source_dict = _create_lite_dict(prv_s, field_names)
        prev_sources.append(lite_source_dict)

    return prev_sources
