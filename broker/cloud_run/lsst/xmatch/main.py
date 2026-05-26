#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module produces "value-added" lite alerts containing xmatch results of the diaSource against the Gaia DR3
vari_classifier catalog."""

import os
from pathlib import Path
import numpy as np
import flask
import pittgoogle
import hpgeom
import pyarrow as pa
import pyarrow.parquet as pq
import astropy.units as u
from astropy.coordinates import SkyCoord
from google.cloud import logging
import pyarrow.compute as pc

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
nside19 = hpgeom.order_to_nside(19)
parquet_dir_name = "gaia_dr3"
parquet_file_name = "enriched_vari_classifier.parquet"
ENRICHED_VARI_CLASSIFIER_FILE_PATH = (
    Path(__file__).resolve().parent / parquet_dir_name / parquet_file_name
)
_GAIA_TABLE = pq.read_table(
    ENRICHED_VARI_CLASSIFIER_FILE_PATH,
    columns=["source_id", "ra", "dec", "healpix19", "best_class_name", "best_class_score"],
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
    """Produces a value-added alert stream (${survey}-xmatch) containing xmatch results of the diaSource
    against Gaia DR3 vari_classifier catalog. Messages in this stream retain fields from the original
    alert-lite packet.

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
    ra = alert_lite.dict["alert_lite"]["diaSource"]["ra"]
    dec = alert_lite.dict["alert_lite"]["diaSource"]["dec"]
    xmatch_results = xmatch_gaia(ra, dec)

    # determine three closest Gaia objects (if they exist)
    closest_gaia_sources = find_closest_gaia_sources(ra, dec, xmatch_results)

    TOPIC.publish(
        pittgoogle.Alert.from_dict(
            {"alert_lite": alert_lite.dict["alert_lite"], "xmatch_gaia": closest_gaia_sources},
            attributes={**alert_lite.attributes},
            schema_name="default",
        )
    )

    return "", HTTP_204


def xmatch_gaia(diasource_ra: float, diasource_dec: float, radius_arcsec: float = 90.0):
    """Crossmatch a diaSource sky position against the Gaia DR3 vari_classifier catalog.

    Identifies HEALPix pixels at order 19 that overlap a cone of ``radius_arcsec`` centered on the given coordinates,
    then reads matching rows from the local Parquet file using a HEALPix filter for efficiency.

    Parameters
    ----------
    diasource_ra : float
        Right ascension of the diaSource in decimal degrees (ICRS).
    diasource_dec : float
        Declination of the diaSource in decimal degrees (ICRS).
    radius_arcsec : float, optional
        Search cone radius in arcseconds. Default is 90.0.

    Returns
    -------
    pyarrow.Table
        Table of matching Gaia sources with columns: ``source_id``, ``ra``, ``dec``, ``best_class_name``, and
        ``best_class_score``. May be empty if no sources fall within the cone.
    """

    cone = set(
        hpgeom.query_circle(
            nside19, diasource_ra, diasource_dec, radius_arcsec / 3600, inclusive=True
        )
    )
    # perform xmatch and return results
    mask = pc.is_in(_GAIA_TABLE["healpix19"], value_set=pa.array(list(cone)))

    return _GAIA_TABLE.filter(mask).select(
        ["source_id", "ra", "dec", "best_class_name", "best_class_score"]
    )


def find_closest_gaia_sources(diasource_ra: float, diasource_dec: float, xmatch_results) -> dict:
    """Identify up to three closest Gaia sources to a diaSource position.

    Computes on-sky angular separations between the diaSource and every source in ``xmatch_results``, sorts by
    separation, and returns metadata for the nearest three. Values are ``None`` when fewer than three Gaia sources are
    available.

    Parameters
    ----------
    diasource_ra : float
        Right ascension of the diaSource in decimal degrees (ICRS).
    diasource_dec : float
        Declination of the diaSource in decimal degrees (ICRS).
    xmatch_results : pyarrow.Table
        Candidate Gaia sources returned by :func:`xmatch_gaia`. Expected columns: ``source_id``, ``ra``, ``dec``, and
        ``best_class_name``.

    Returns
    -------
    dict
        Dictionary with nine keys following the pattern ``{ordinal}_gaia_source``, ``{ordinal}_gaia_source_class``, and
        ``separation_to_{ordinal}_gaia_source`` for ordinals ``closest``, ``second_closest``, and ``third_closest``.
        Separations are in arcseconds. Any entry beyond the number of matched sources is set to ``None``.
    """

    result = {}
    ORDINALS = ["closest", "second_closest", "third_closest"]

    for ordinal in ORDINALS:
        result[f"{ordinal}_gaia_source"] = None
        result[f"{ordinal}_gaia_source_class"] = None
        result[f"{ordinal}_gaia_source_class_score"] = None
        result[f"separation_to_{ordinal}_gaia_source"] = None

    if len(xmatch_results) == 0:
        return result

    # instatiate positions and determine separations between sources
    diasource_coord = SkyCoord(diasource_ra * u.deg, diasource_dec * u.deg, frame="icrs")
    gaia_coords = SkyCoord(
        xmatch_results["ra"].to_pylist() * u.deg,
        xmatch_results["dec"].to_pylist() * u.deg,
        frame="icrs",
    )
    separations = diasource_coord.separation(gaia_coords).arcsec

    # sort results
    num_closest = min(
        3, len(separations)
    )  # determine the number of closest sources; max returned by module is 3
    top_k_unsorted_indices = np.argpartition(separations, range(num_closest))[
        :num_closest
    ]  #  partially sort the array so that the k smallest values are in the first k positions
    sorted_idx = top_k_unsorted_indices[
        np.argsort(separations[top_k_unsorted_indices])
    ]  # sort the unordered subset by their separation values
    subset = xmatch_results.take(sorted_idx).to_pydict()
    sorted_separations = separations[sorted_idx].tolist()

    for i, ordinal in enumerate(ORDINALS[: len(sorted_idx)]):
        result[f"{ordinal}_gaia_source"] = int(subset["source_id"][i])
        result[f"{ordinal}_gaia_source_class"] = subset["best_class_name"][i]
        result[f"{ordinal}_gaia_source_class_score"] = subset["best_class_score"][i]
        result[f"separation_to_{ordinal}_gaia_source"] = float(sorted_separations[i])

    return result
