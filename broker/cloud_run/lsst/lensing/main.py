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
module_version = {"module_version": "v0.1"}

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

    alert_lite_df = create_dataframe(alert_lite.dict["alert_lite"])

    # apply selection criteria to the alert
    flux_ratio = compute_flux_ratio(alert_lite_df)
    is_lensed_sn_candidate = check_supernova_color_magnitude_criteria(alert_lite_df)

    pg_variable = {"pg_lensed_sn_candidate": False}

    if flux_ratio.get("extended_object_candidate", False) and is_lensed_sn_candidate.get(
        "lensed_sn_candidate", False
    ):
        pg_variable = {"pg_lensed_sn_candidate": True}

    TOPIC.publish(
        pittgoogle.Alert.from_dict(
            {
                "alert_lite": alert_lite.dict["alert_lite"],
                "strong_lensing": {
                    **flux_ratio,
                    **is_lensed_sn_candidate,
                    **module_version,
                },
            },
            attributes={**alert_lite.attributes, **pg_variable},
            schema_name="default",
        )
    )

    return "", HTTP_204


def create_dataframe(alert_lite_dict: dict) -> pd.DataFrame:
    """Create a DataFrame object from the alert lite dictionary."""

    required_cols = [
        "band",
        "midpointMjdTai",
        "psfFlux",
        "apFlux",
        "visit",
    ]

    def filter_columns(field_list, required_cols):
        """Extract only relevant columns if they exist."""

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
    df = pd.concat([sources_df, forced_df], ignore_index=True)

    return df.sort_values("midpointMjdTai", ascending=False)


def compute_flux_ratio(alert_df, flux_based_extendedness_cutoff=10**1):
    """
    Calculates the ratio of aperture flux to PSF flux for a given diaSource. Flags the diaSource as an extended
    candidate when this ratio exceeds a specified cutoff value.
    """

    # calculate the ratio of aperture flux to PSF flux for the diaSource
    flux_ratio = alert_df["apFlux"].iloc[0] / alert_df["psfFlux"].iloc[0]

    # require at least two detections of the diaObject in a single band
    visit_counts = alert_df.groupby("band")["visit"].nunique().reset_index(name="n_visits")
    if not (visit_counts["n_visits"] > 2).any():
        return {
            "flux_ratio": float(flux_ratio),
            "extended_object_candidate": False,
        }

    return {
        "flux_ratio": float(flux_ratio),
        "extended_object_candidate": bool(flux_ratio > flux_based_extendedness_cutoff),
    }


def check_supernova_color_magnitude_criteria(
    alert_df, max_time_diff=3.0, tolerance=0.1, min_matches=3
):
    """
    Flags a diaObject as a lensed supernovae candidate if at least 3 r/i band pairs observed within 3 days satisfy:
        r-i = 0                    if i < 21.0158
        r-i = 0.52*i - 10.96       otherwise
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
    n_matches = (np.abs(color_obs - color_expected) < tolerance).sum()

    return {"lensed_sn_candidate": True if n_matches >= min_matches else False}
