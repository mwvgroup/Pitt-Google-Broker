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
import hpgeom
import astropy.units as u
import pyarrow.fs as pafs
import pyarrow.parquet as pq
from hats.io import paths
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
GAIA_DR3_CATALOG = hats.read_hats(
    "s3://stpubdata/gaia/gaia_dr3/public/hats/gaia", single_catalog=True
)
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
HEALPIX_ORDER = 15  # used to build a parquet row filter
BIT_SHIFT = 2 * (
    29 - HEALPIX_ORDER
)  # bits between an order-{HEALPIX_ORDER} index and an order-29 index (i.e., SHIFT = 28 for HEALPIX_ORDER = 15)
NSIDE = hpgeom.order_to_nside(HEALPIX_ORDER)  # 2**ORDER
MAX_SEPARATION_ARCSEC = 5
ORDINALS = ["closest", "second_closest", "third_closest"]
S3FS = pafs.S3FileSystem(
    anonymous=True,
    region="us-east-1",
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
                "pg_closest_gaia_source_id": str(
                    xmatch_results["closest_gaia_source"]["source_id"]
                ),
                "pg_closest_gaia_source_separation": str(
                    xmatch_results["closest_gaia_source"]["separation"]
                ),
                "pg_closest_gaia_source_phot_variable_flag": str(
                    xmatch_results["closest_gaia_source"]["phot_variable_flag"]
                ),
                "pg_closest_gaia_source_classprob_dsc_combmod_star": str(
                    xmatch_results["closest_gaia_source"]["classprob_dsc_combmod_star"]
                ),
            },
            schema_name="default",
        )
    )

    return "", HTTP_204


def filter_gaia_catalog(ra: float, dec: float) -> pd.DataFrame:
    """Retrieve Gaia DR3 sources near a sky position from the publicly available HATS catalog.

    Reads only the rows of the Gaia DR3 Source Catalog that lie in the HEALPix pixels touched by a cone of radius
    ``MAX_SEPARATION_ARCSEC`` around the given position. The selection happens in two stages:

    1. Partition selection (metadata only): ``filter_by_cone`` keeps the catalog partitions (HATS files)
       that overlap the cone. No data is read at this stage.
    2. Row selection (at read time): within each of those partitions, a parquet filter on the ``_healpix_29``
       column keeps only the rows inside the pixels of order ``ORDER`` that overlap the cone. Since
       an order-``ORDER`` pixel is slightly larger than the cone, the result is a superset of the cone.

    Note that the returned table is NOT limited to sources within ``MAX_SEPARATION_ARCSEC`` of the position. It
    contains every source in the overlapping order-``ORDER`` pixels.
    The exact angular separation cut is applied downstream in :func:`xmatch`.

    Parameters
    ----------
    ra : float
        Right ascension of the position in decimal degrees (ICRS).
    dec : float
        Declination of the position in decimal degrees (ICRS).

    Returns
    -------
    pandas.DataFrame
        Candidate Gaia sources, with one column for each entry in ``GAIA_READ_COLUMNS``: ``source_id``,
        ``ra``, ``dec``, ``pm``, ``pmra``, ``pmra_error``, ``pmdec``, ``pmdec_error``, ``parallax``,
        ``parallax_over_error``, ``phot_variable_flag``, ``classprob_dsc_combmod_quasar``,
        ``classprob_dsc_combmod_galaxy``, ``classprob_dsc_combmod_star``, ``phot_g_mean_mag``,
        ``phot_g_mean_flux_over_error``, and ``bp_rp``. The table may be empty if no sources fall in the
        selected pixels.

    Raises
    ------
    ValueError
        If no catalog partitions overlap the cone, because ``pd.concat`` cannot concatenate an empty list.
    """

    # select the catalog partitions that overlap a ``MAX_SEPARATION_ARCSEC`` cone
    filtered_catalog = GAIA_DR3_CATALOG.filter_by_cone(ra, dec, MAX_SEPARATION_ARCSEC)

    # identify the HEALPix pixels that overlap the cone
    cone_pixels = hpgeom.query_circle(NSIDE, ra, dec, MAX_SEPARATION_ARCSEC / 3600, inclusive=True)

    # build a parquet row filter from the pixels in ``cone_pixels``
    # a catalog entry is in pixel ``p`` if:
    # p * 2**BIT_SHIFT <= _healpix_29 < (p + 1) * 2**BIT_SHIFT
    # this is because every index in ``_healpix_29`` starts with the index of the ``HEALPIX_ORDER`` containing it,
    # followed by ``BIT_SHIFT`` bits for the position within that pixel
    filters = [
        [
            ("_healpix_29", ">=", int(pixel) * 2**BIT_SHIFT),
            ("_healpix_29", "<", (int(pixel) + 1) * 2**BIT_SHIFT),
        ]
        for pixel in cone_pixels
    ]

    # read the matching rows from each overlapping partition and combine them into a single table
    return pd.concat(
        [
            read_partition(partition, filters)
            for partition in filtered_catalog.get_healpix_pixels()
        ],
        ignore_index=True,
    )


def xmatch(ra: float, dec: float, filtered_gaia_dr3_catalog: pd.DataFrame) -> dict:
    """Identify up to three Gaia sources within ``MAX_SEPARATION_ARCSEC`` of a DIA source position.

    Computes on-sky angular separations between a DIA source and every object in ``filtered_gaia_dr3_catalog``,
    keeps the three closest, and discards any of those that are not closer than ``MAX_SEPARATION_ARCSEC``. For each
    remaining source, the function returns the Gaia ``source_id``, the separation, and the catalog columns listed in
    ``GAIA_OUTPUT_COLUMNS``. Sources are ordered by increasing separation. Values are ``None`` when fewer than three
    Gaia sources fall within the cutoff radius, or when Gaia has no value for a given column.

    Parameters
    ----------
    ra : float
        Right ascension of the DIA source in decimal degrees (ICRS).
    dec : float
        Declination of the DIA source in decimal degrees (ICRS).
    filtered_gaia_dr3_catalog : pandas.DataFrame
        Candidate Gaia sources, as returned by :func:`filter_gaia_catalog`. This is a superset of the sources
        within the cutoff radius (every source in the order-``HEALPIX_ORDER`` pixels touched by the cone), so
        the exact separation cut is applied here. May be empty or contain fewer than three rows. Must contain
        the columns in ``GAIA_READ_COLUMNS``.

    Returns
    -------
    dict
        Three top-level keys, one per ordinal in ``ORDINALS``: ``closest_gaia_source``, ``second_closest_gaia_source``
        and ``third_closest_gaia_source``. Each maps to a dict with:

        - ``source_id``: Gaia DR3 ``source_id``
        - ``separation``: angular separation from the DIA source in arcseconds
        - one entry for each column in ``GAIA_OUTPUT_COLUMNS``

        Every field of a record is ``None`` if there is no source for that rank within ``MAX_SEPARATION_ARCSEC``.
        Individual column entries are also ``None`` when Gaia has no value for them.
    """

    if filtered_gaia_dr3_catalog.empty:
        candidates = filtered_gaia_dr3_catalog
        candidate_separations = np.array([])
    else:
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
        sorted_idx = np.argsort(angular_separations)[: len(ORDINALS)]  # sorted in ascending order

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
        has_match = idx < len(rows)
        result[f"{ordinal}_gaia_source"] = {
            "source_id": int(rows[idx]["source_id"]) if has_match else None,
            "separation": float(candidate_separations[idx]) if has_match else None,
            **{col: rows[idx][col] if has_match else None for col in GAIA_OUTPUT_COLUMNS},
        }

    return result


def read_partition(partition, filters):
    path = str(paths.pixel_catalog_file(GAIA_DR3_CATALOG.catalog_base_dir, partition))
    path = path.removeprefix("s3://")
    return pq.read_table(
        path, columns=GAIA_READ_COLUMNS, filters=filters, filesystem=S3FS
    ).to_pandas()
