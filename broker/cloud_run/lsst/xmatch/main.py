#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module produces "value-added" lite alerts containing xmatch results of the diaSource against the Gaia DR3
Source Catalog."""

import os
import numpy as np
import pandas as pd
import flask
import pittgoogle
import hats
import astropy.units as u
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
gaia_dr3_catalog = hats.read_hats("s3://stpubdata/gaia/gaia_dr3/public/hats").main_catalog
GAIA_READ_COLUMNS = [
    "source_id",
    "ra",
    "dec",
    "pm",
    "pmra",
    "pmra_error",
    "pmdec",
    "pmdec_error",
    "parallax",
    "parallax_over_error",
    "phot_variable_flag",
    "classprob_dsc_combmod_quasar",
    "classprob_dsc_combmod_galaxy",
    "classprob_dsc_combmod_star",
    "phot_g_mean_mag",
    "phot_g_mean_flux_over_error",
    "bp_rp",
]
GAIA_OUTPUT_COLUMNS = [
    column for column in GAIA_READ_COLUMNS if column not in ("source_id", "ra", "dec")
]
ORDINALS = ["closest", "second_closest", "third_closest"]
MAX_SEPARATION_ARCSEC = 5

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
    """Produces a value-added alert stream (${survey}-xmatch) identifying up to three Gaia sources (from the DR3 Source
    Catalog) within 5 arcseconds of a DIA source position. Messages in this stream retain fields from the original
    alert-lite packet.

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
        alert_lite = pittgoogle.Alert.from_cloud_run(envelope, schema_name="default")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    # define RA, Dec of the incoming DIA source
    ra = alert_lite.dict["alert_lite"]["diaSource"]["ra"]
    dec = alert_lite.dict["alert_lite"]["diaSource"]["dec"]

    # load the filtered Gaia DR3 Source Catalog
    filtered_gaia_dr3_catalog = filter_gaia_catalog(ra, dec)

    # identify the 3 closest Gaia sources within a radius of 5 arcseconds, if available
    xmatch_results = xmatch(ra, dec, filtered_gaia_dr3_catalog)

    TOPIC.publish(
        pittgoogle.Alert.from_dict(
            {"alert_lite": alert_lite.dict["alert_lite"], "xmatch_gaia": xmatch_results},
            attributes={
                **alert_lite.attributes,
                "closest_gaia_source_separation": str(
                    xmatch_results["closest_gaia_source_separation"]
                ),
                "pg_closest_gaia_source_phot_variable_flag": xmatch_results[
                    "closest_gaia_source_phot_variable_flag"
                ],
                "closest_gaia_source_classprob_dsc_combmod_star": str(
                    xmatch_results["closest_gaia_source_classprob_dsc_combmod_star"]
                ),
            },
            schema_name="default",
        )
    )

    return "", HTTP_204


def filter_gaia_catalog(ra: float, dec: float) -> pd.DataFrame:
    """Retrieve candidate Gaia DR3 sources near a sky position from the HATS catalog.

    Selects the HEALPix partitions of the Gaia DR3 HATS catalog that overlap a 5 arcsecond cone around the given
    position, reads the ``GAIA_READ_COLUMNS`` columns from each of those partitions, and concatenates them into a
    single table with a fresh index.

    Note that the cone selection operates at the partition level only. The returned table contains every source in the
    overlapping partitions, not only those within 5 arcseconds of the position, so it will typically include many
    sources outside the cone. Use :func:`xmatch` to rank the candidates by exact angular separation and apply the
    final cutoff radius.

    Parameters
    ----------
    ra : float
        Right ascension of the position in decimal degrees (ICRS).
    dec : float
        Declination of the position in decimal degrees (ICRS).

    Returns
    -------
    pandas.DataFrame
        Candidate Gaia sources from all overlapping partitions, with one column for each entry in
        ``GAIA_READ_COLUMNS``: ``source_id``, ``ra``, ``dec``, ``pm``, ``pmra``, ``pmra_error``, ``pmdec``,
        ``pmdec_error``, ``parallax``, ``parallax_over_error``, ``phot_variable_flag``,
        ``classprob_dsc_combmod_quasar``, ``classprob_dsc_combmod_galaxy``, ``classprob_dsc_combmod_star``,
        ``phot_g_mean_mag``, ``phot_g_mean_flux_over_error``, and ``bp_rp``.
    """

    # filter catalog
    radius_arcseconds = 5.0
    filtered_catalog = gaia_dr3_catalog.filter_by_cone(ra, dec, radius_arcseconds)

    return pd.concat(
        [
            filtered_catalog.read_pixel_to_pandas(
                pixel,
                columns=GAIA_READ_COLUMNS,
            )
            for pixel in filtered_catalog.get_healpix_pixels()
        ],
        ignore_index=True,
    )


def xmatch(ra: float, dec: float, filtered_gaia_dr3_catalog: pd.DataFrame) -> dict:
    """Identify up to three Gaia sources within 5 arcseconds of a DIA source position.

    Computes on-sky angular separations between a DIA source and every object in ``filtered_gaia_dr3_catalog``, keeps
    the three closest, and discards any of those that are not closer than ``MAX_SEPARATION_ARCSEC``. For each remaining
    source, returns the Gaia ``source_id``, the separation, and the catalog columns listed in ``GAIA_OUTPUT_COLUMNS``.
    Sources are ordered by increasing separation. Values are ``None`` when fewer than three Gaia sources fall within
    the cutoff radius, or when Gaia has no value for a given column.

    Parameters
    ----------
    ra : float
        Right ascension of the DIA source in decimal degrees (ICRS).
    dec : float
        Declination of the DIA source in decimal degrees (ICRS).
    filtered_gaia_dr3_catalog : pandas.DataFrame
        Candidate Gaia sources, as returned by :func:`filter_gaia_catalog`. Must be non-empty and contain the columns
        in ``GAIA_READ_COLUMNS``.

    Returns
    -------
    dict
        For each ordinal in ``ORDINALS`` (``closest``, ``second_closest`` and ``third_closest``):

        - ``{ordinal}_gaia_source``: Gaia DR3 ``source_id``
        - ``{ordinal}_gaia_source_separation``: angular separation in arcseconds
        - ``{ordinal}_gaia_source_{column}`` for each column in ``GAIA_OUTPUT_COLUMNS``

        Every entry for an ordinal is ``None`` if there is no source for that rank within ``MAX_SEPARATION_ARCSEC``.
        Individual column entries are also ``None`` when Gaia has no value for them. If no sources are within the
        cutoff radius, all entries are ``None``.
    """

    # instatiate coordinates
    dia_source_coord = SkyCoord(ra * u.deg, dec * u.deg, frame="icrs")
    gaia_coords = SkyCoord(
        filtered_gaia_dr3_catalog["ra"].to_numpy(dtype="float64") * u.deg,
        filtered_gaia_dr3_catalog["dec"].to_numpy(dtype="float64") * u.deg,
        frame="icrs",
    )

    # calculate the angular separation between each Gaia object and the DIA source
    angular_separations = dia_source_coord.separation(gaia_coords).arcsec

    # identify the indices of the 3 closest Gaia objects
    sorted_idx = np.argpartition(angular_separations, range(3))[:3]  # sorted in ascending order

    # enforce a cutoff radius of 5 arcseconds
    n_within_cutoff = sum(angular_separations[sorted_idx] < MAX_SEPARATION_ARCSEC)
    candidate_idx = sorted_idx[:n_within_cutoff]
    candidate_separations = angular_separations[candidate_idx]

    # select the catalog rows for the Gaia objects that passed the cutoff
    candidates = filtered_gaia_dr3_catalog.iloc[candidate_idx]

    # convert the selected rows into a list of dicts (one per source, keyed by column name) with
    # missing values as None rather than NaN, so they are serialized as proper nulls downstream
    rows = candidates.astype(object).where(candidates.notna(), None).to_dict("records")

    # format output
    result = {}
    for idx, ordinal in enumerate(ORDINALS):
        prefix = f"{ordinal}_gaia_source"
        has_match = idx < len(rows)

        result[prefix] = int(rows[idx]["source_id"]) if has_match else None
        result[f"{prefix}_separation"] = float(candidate_separations[idx]) if has_match else None
        for col in GAIA_OUTPUT_COLUMNS:
            result[f"{prefix}_{col}"] = rows[idx][col] if has_match else None

    return result
