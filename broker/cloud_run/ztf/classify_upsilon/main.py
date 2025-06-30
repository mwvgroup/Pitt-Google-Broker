#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Classify alerts using UPSILoN (Kim & Bailer-Jones 2015)."""

import os
import flask
import pandas as pd
import pittgoogle
import upsilon
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
TOPIC = pittgoogle.Topic.from_cloud("upsilon", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID)

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run() -> tuple[str, int]:
    """Classify alert with UPSILoN; publish and store results.

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
        alert_lite = pittgoogle.Alert.from_cloud_run(envelope, "default")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    # UPSILoN recommends using light curves with more than ~80 data points
    has_min_detections_in_any_filter = any(
        alert_lite.dict["variability"].get(f"n_detections_{filter}_band", 0) >= 80
        for filter in ["g", "r", "i"]
    )

    if has_min_detections_in_any_filter:
        # classify and publish results
        alert_lite_df = _create_lite_dataframe(alert_lite.dict["alert_lite"])
        upsilon_dict = _classify_with_upsilon(alert_lite_df)
        TOPIC.publish(
            pittgoogle.Alert.from_dict(
                {
                    "alert_lite": alert_lite.dict,
                    "upsilon": {
                        "objectId": alert_lite.dict["alertIds"]["objectId"],
                        "candid": alert_lite.dict["alertIds"]["sourceId"],
                        **upsilon_dict,
                    },
                },
                attributes={
                    **alert_lite.attributes,
                    "pg_upsilon_g_label": upsilon_dict["g_label"],
                    "pg_upsilon_g_flag": upsilon_dict["g_flag"],
                    "pg_upsilon_r_label": upsilon_dict["r_label"],
                    "pg_upsilon_r_flag": upsilon_dict["r_flag"],
                    "pg_upsilon_i_label": upsilon_dict["i_label"],
                    "pg_upsilon_i_flag": upsilon_dict["i_flag"],
                },
                schema_name="default",
            )
        )

    return "", HTTP_204


def _classify_with_upsilon(alert_lite_df: pd.Dataframe) -> dict:
    upsilon_dict = {}
    bands = alert_lite_df["filter"].map(pittgoogle.utils.ztf_fid_names()).unique()
    rf_model = upsilon.load_rf_model()  # load UPSILoN's classification model
    for band in bands:
        # ---Extract data
        filter_diaSources = alert_lite_df[alert_lite_df["filter"] == band]
        mag_gt_zero = filter_diaSources["mag"].to_numpy() > 0
        # set output to None if data is absent or there are too few data points for this band
        # limit recommended by UPSILoN
        if filter_diaSources.empty or mag_gt_zero.sum() <= 80:
            upsilon_dict[f"{band}_label"] = None
            upsilon_dict[f"{band}_probability"] = None
            upsilon_dict[f"{band}_flag"] = None
            continue

        # ---Extract features
        date = filter_diaSources["jd"].to_numpy()[mag_gt_zero]
        mag = filter_diaSources["mag"].to_numpy()[mag_gt_zero]
        mag_err = filter_diaSources["magerr"].to_numpy()[mag_gt_zero]
        e_features = upsilon.ExtractFeatures(date, mag, mag_err)
        e_features.run()
        features = e_features.get_features()

        # ---Classify
        label, probability, flag = upsilon.predict(rf_model, features)
        upsilon_dict[f"{band}_label"] = label
        upsilon_dict[f"{band}_probability"] = probability
        upsilon_dict[f"{band}_flag"] = flag

    return upsilon_dict


def _create_lite_dataframe(alert_dict: dict) -> pd.DataFrame:
    """Return a pandas DataFrame containing the source detections."""

    # sources and previous sources are expected to have the same fields
    sources_df = pd.DataFrame([alert_dict.get("source")] + (alert_dict.get("prvSources") or []))
    # use nullable integer data type to avoid converting ints to floats for columns in one dataframe but not the other
    sources_ints = [c for c, v in sources_df.dtypes.items() if v == int]
    dataframe = sources_df.astype({c: "Int64" for c in sources_ints})

    return dataframe
