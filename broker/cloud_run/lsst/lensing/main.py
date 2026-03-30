#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module produces "value-added" lite alerts that flags strongly lensed supernova candidates."""

import os
import numpy as np
import pandas as pd
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
TOPIC = pittgoogle.Topic.from_cloud("lensing", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID)

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run():
    """Produces a value-added alert stream (${survey}-lensed) that identifies strongly lensed supernova candidates.
    Messages in this stream retain fields from the original alert-lite packet.

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

    # create the alert lite DataFrame and apply selection criteria
    alert_lite_df = create_dataframe(alert_lite.dict["alert_lite"])
    flux_ratio = compute_flux_ratio(alert_lite_df)
    is_lensed_sn_candidate = check_supernova_color_magnitude_criteria(alert_lite_df)

    # assign value to outgoing pittgoogle Pub/Sub message attribute
    pg_variable = {"pg_lensed_sn_candidate": False}
    if flux_ratio.get("extended_object_candidate", False) and is_lensed_sn_candidate.get(
        "lensed_sn_candidate", False
    ):
        pg_variable = {"pg_lensed_sn_candidate": True}

    TOPIC.publish(
        pittgoogle.Alert.from_dict(
            {
                "alert_lite": alert_lite.dict["alert_lite"],
                "lensing": {
                    **flux_ratio,
                    **is_lensed_sn_candidate,
                },
            },
            attributes={**alert_lite.attributes, **pg_variable},
            schema_name="default",
        )
    )

    return "", HTTP_204


def create_dataframe(alert_lite_dict: dict) -> pd.DataFrame:
    """Create a DataFrame object from the alert lite dictionary.

    Parameters
    ----------
    alert_lite_dict : dict
        Dictionary representation of an alert lite packet, expected to contain keys: diaSource, prvDiaSources, and
        prvDiaForcedSources.

    Returns
    -------
    pd.DataFrame
        DataFrame containing columns: band, midpointMjdTai, psfFlux, apFlux, and visit, sorted by midpointMjdTai in
        descending order. Rows are drawn from the diaSource, prvDiaSources, and prvDiaForcedSources fields of the
        alert lite packet.
    """

    required_cols = [
        "band",
        "midpointMjdTai",
        "psfFlux",
        "apFlux",
        "visit",
    ]

    def filter_columns(field_list: list[dict], required_cols: list[str]) -> list[dict]:
        """Extract only relevant columns if they exist.

        Parameters
        ----------
        field_list : list[dict]
            List of diaSource or diaForcedSource dictionaries to filter.
        required_cols : list[str]
            Column names to retain from each dictionary.

        Returns
        -------
        list[dict]
            List of dictionaries containing only the keys present in required_cols, with None entries removed.
        """

        return [
            {k: field.get(k) for k in required_cols if k in field}
            for field in field_list
            if field is not None
        ]

    # extract fields and create filtered DataFrames
    sources = [alert_lite_dict.get("diaSource")] + (alert_lite_dict.get("prvDiaSources") or [])
    forced_sources = alert_lite_dict.get("prvDiaForcedSources") or []
    sources_df = pd.DataFrame(filter_columns(sources, required_cols))
    forced_df = pd.DataFrame(filter_columns(forced_sources, required_cols))

    # concatenate diaSource, prvDiaSources, and prvDiaForcedSources into a single DataFrame
    df = pd.concat([sources_df, forced_df], ignore_index=True).sort_values(
        "midpointMjdTai", ascending=False
    )

    return df


def compute_flux_ratio(
    alert_df: pd.DataFrame,
    flux_based_extendedness_cutoff: float = 10**1,
) -> dict[str, float | bool]:
    """Calculate the ratio of aperture flux to PSF flux for a given diaSource and flag it as an extended candidate
    if the ratio exceeds a cutoff value in at least two visits across at least two distinct bands.

    Parameters
    ----------
    alert_df : pd.DataFrame
        DataFrame containing diaSource and associated previous source detections, with columns apFlux, psfFlux, band,
        and visit.
    flux_based_extendedness_cutoff : float, optional
        Minimum flux ratio (aperture / PSF) required to flag a detection as extended. Defaults to 10.

    Returns
    -------
    dict[str, float | bool]
        Dictionary with keys:

        - flux_ratio (float): Aperture-to-PSF flux ratio for the most recent diaSource.
        - extended_candidate (bool): True if at least two bands each contain at least two visits where the flux ratio
          exceeds flux_based_extendedness_cutoff
    """

    # calculate the ratio of aperture flux to PSF flux for the diaObject and flag if it is an extended candidate
    alert_df["flux_ratio"] = alert_df["apFlux"] / alert_df["psfFlux"]
    alert_df["extended_candidate"] = alert_df["flux_ratio"] > flux_based_extendedness_cutoff

    # require at least two detections satisfying the extendedness threshold in two distinct bands
    extended_visit_counts = (
        alert_df[alert_df["extended_candidate"]]
        .groupby("band")["visit"]
        .nunique()
        .reset_index(name="n_extended_detections")
    )
    qualifying_extended_bands = (extended_visit_counts["n_extended_detections"] >= 2).sum()

    if qualifying_extended_bands < 2:
        return {
            "flux_ratio": float(alert_df["flux_ratio"].iloc[0]),
            "extended_candidate": False,
        }

    return {
        "flux_ratio": float(alert_df["flux_ratio"].iloc[0]),
        "extended_candidate": True,
    }


def check_supernova_color_magnitude_criteria(
    alert_df: pd.DataFrame,
    max_time_diff: float = 3.0,
    tolerance: float = 0.1,
    min_matches: int = 3,
) -> dict[str, bool]:
    """Flag a diaObject as a lensed supernova candidate based on r/i color-magnitude criteria.

    Evaluates paired r- and i-band observations taken within a maximum time separation.
    A diaObject is flagged as a candidate if at least min_matches pairs satisfy:

    - r - i = 0              if i < 21.0158
    - r - i = 0.52*i - 10.96 otherwise

    Parameters
    ----------
    alert_df : pd.DataFrame
        DataFrame containing diaSource and associated previous source detections, with columns band, midpointMjdTai,
        and psfFlux.
    max_time_diff : float, optional
        Maximum allowed time separation in days between r- and i-band observations to be considered a matched pair.
        Defaults to 3.0.
    tolerance : float, optional
        Allowed deviation in magnitudes from the expected color-magnitude relation for a pair to be counted as a match.
        Defaults to 0.1.
    min_matches : int, optional
        Minimum number of r/i pairs that must satisfy the color-magnitude criteria for the diaObject to be flagged as
        a lensed supernova candidate. Defaults to 3.

    Returns
    -------
    dict[str, bool]
        Dictionary with key:

        - lensed_sn_candidate (bool): True if at least min_matches r/i pairs satisfy the color-magnitude criteria
          within max_time_diff days of each other.
    """

    not_a_candidate = {"lensed_sn_candidate": False}

    def convert_flux_to_mag(psfFlux):
        return -2.5 * np.log10(psfFlux) + 31.4

    # extract the 'r' and 'i' band photometry if it exists
    r_band_photometry = alert_df[alert_df["band"] == "r"]
    i_band_photometry = alert_df[alert_df["band"] == "i"]
    if r_band_photometry.empty or i_band_photometry.empty:
        # observations in one of the two required bands does not exist
        return not_a_candidate

    # create a time-aligned DataFrame of paired r/i observations for the diaObject
    matched = pd.merge_asof(
        r_band_photometry,
        i_band_photometry,
        on="midpointMjdTai",
        direction="nearest",
        tolerance=max_time_diff,
        suffixes=("_r", "_i"),
    )

    matched = matched.dropna(subset=["psfFlux_i"])
    if matched.empty:
        # there are no paired observations within the maximum allowed MJD difference in days
        return not_a_candidate

    # convert flux -> magnitude
    i_mag = convert_flux_to_mag(matched["psfFlux_i"].values)
    r_mag = convert_flux_to_mag(matched["psfFlux_r"].values)

    # determine the number of pairs that meet the following color-magnitude criteria
    color_obs = r_mag - i_mag
    color_expected = np.where(i_mag < 21.0158, 0.0, 0.52 * i_mag - 10.96)
    n_matches = ((color_obs - color_expected) > tolerance).sum()

    return {"lensed_sn_candidate": True if n_matches >= min_matches else False}
