#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module produces "value-added" lite alerts containing J indices on the DIA point source fluxes."""

import os
from typing import Dict
import numpy as np
import flask
import pittgoogle
import hpgeom
import pyarrow.parquet as pq
import astropy.units as u
from pathlib import Path
from astropy.coordinates import SkyCoord
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

# module variables
parquet_dir_name = "gaia_catalog"
parquet_file_name = "enriched_vari_classifier.parquet"
ENRICHED_VARI_CLASSIFIER_FILE_PATH = (
    Path(__file__).resolve().parent / parquet_dir_name / parquet_file_name
)

# Variables for incoming data
# A url route is used in setup.sh when the trigger subscription is created.
# It is possible to define multiple routes in a single module and trigger them using different subscriptions.
ROUTE_RUN = "/"  # HTTP route that will trigger run(). Must match deploy.sh

# Variables for outgoing data
HTTP_204 = 204  # HTTP code: Success
HTTP_400 = 400  # HTTP code: Bad Request

# GCP resources used in this module
TOPIC = pittgoogle.Topic.from_cloud("xmatch", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID)

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run():
    """Produces a value-added alert stream (${survey}-variability) containing StetsonJ statistics on the DIA point
    source fluxes. Messages in this stream retain fields from the original alert-lite packet.

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
        alert_lite = pittgoogle.Alert.from_cloud_run(envelope, schema_name="default")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    # xmatch Gaia DR3 enriched_vari_classifier catalog
    xmatch_results = xmatch_gaia(alert_lite.ra, alert_lite.dec)

    # determine three closest Gaia objects (if they exist)
    closest_gaia_sources = find_closest_gaia_sources(
        alert_lite.dict["ra"], alert_lite.dict["dec"], xmatch_results
    )

    TOPIC.publish(
        pittgoogle.Alert.from_dict(
            {"alert_lite": alert_lite.dict["alert_lite"], "xmatch_gaia": closest_gaia_sources},
            attributes={**alert_lite.attributes},
            schema_name="default",
        )
    )

    return "", HTTP_204


def xmatch_gaia(diasource_ra: float, diasource_dec: float, radius_arcsec: float = 90.0):
    """Crossmatch a diaSource position against the Gaia DR3 enriched_vari_classifier catalog."""
    nside19 = hpgeom.order_to_nside(19)
    cone = hpgeom.query_circle(
        nside19, diasource_ra, diasource_dec, radius_arcsec / 3600, inclusive=True
    )

    return pq.read_table(
        ENRICHED_VARI_CLASSIFIER_FILE_PATH,
        filters=[("healpix19", "in", cone)],
        columns=["source_id", "ra", "ra_error", "dec", "dec_error", "best_class_name"],
    )


def find_closest_gaia_sources(diasource_ra: float, diasource_dec: float, xmatch_results) -> dict:
    """Return up to 3 closest Gaia sources to the diaSource position, sorted by separation."""

    result = {}
    ORDINALS = ["closest", "second_closest", "third_closest"]

    for ordinal in ORDINALS:
        result[f"{ordinal}_gaia_source"] = None
        result[f"{ordinal}_gaia_source_class"] = None
        result[f"separation_to_{ordinal}_gaia_source"] = None

    if len(xmatch_results) == 0:
        return result

    diasource_coord = SkyCoord(diasource_ra * u.deg, diasource_dec * u.deg, frame="icrs")
    gaia_coords = SkyCoord(
        xmatch_results["ra"].to_pylist() * u.deg,
        xmatch_results["dec"].to_pylist() * u.deg,
        frame="icrs",
    )
    separations = diasource_coord.separation(gaia_coords).arcsec

    sorted_idx = np.argsort(separations)[:3]
    subset = xmatch_results.take(sorted_idx).to_pydict()
    sorted_separations = separations[sorted_idx].tolist()

    for i, ordinal in enumerate(ORDINALS[: len(sorted_idx)]):
        result[f"{ordinal}_gaia_source"] = int(subset["source_id"][i])
        result[f"{ordinal}_gaia_source_class"] = subset["best_class_name"][i]
        result[f"separation_to_{ordinal}_gaia_source"] = float(sorted_separations[i])

    return result
