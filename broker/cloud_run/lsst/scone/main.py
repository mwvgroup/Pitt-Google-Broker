#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Classify an alert using SCONE (Qu et al. 2021).

This code is intended to be containerized and deployed to Google Cloud Run.
Once deployed, individual alerts in the "trigger" stream will be delivered to the container as HTTP requests.
"""

import os
from pathlib import Path
import flask  # Manage the HTTP request containing the alert
import pittgoogle  # Manipulate the alert and interact with cloud resources

import google.cloud.logging
import numpy as np
import pandas as pd

from model_utils import *
from data_utils import *
from base import CreateHeatmapsBase

# [FIXME] Make this helpful or else delete it.
# Connect the python logger to the google cloud logger.
# By default, this captures INFO level and above.
# pittgoogle uses the python logger.
# We don't currently use the python logger directly in this script, but we could.
google.cloud.logging.Client().setup_logging()

# These environment variables are defined when running the deploy.sh script.
PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# provenance variables
MODULE_NAME = "SCONE"
MODULE_VERSION = 0.1

# classifier variables
model_dir_name = ""
model_file_name = ""
MODEL_PATH = Path(__file__).resolve().parent / model_dir_name / model_file_name
scone_config = {
    "metadata_paths": ["/path/to/data/metadata_0.csv", "/path/to/data/metadata_1.csv"],
    "lcdata_paths": ["~/path/to/data/lcdata_0.csv", "~/path/to/data/lcdata_1.csv"],
    "ids_path": "/path/to/output/dir/0_5_Ia_split_heatmaps_ids.hdf5",
    "output_path": "/path/to/output/dir",
    "num_wavelength_bins": 32,
    "num_mjd_bins": 180,
    "Ia_fraction": None,
    "categorical_min_per_type": 200,
    "categorical_max_per_type": 2000,
    "save_to_json": True,
    "from_json": False,
    "sn_type_id_to_name": {
        42: "SNII",
        52: "SNIax",
        62: "SNIbc",
        67: "SNIa-91bg",
        64: "KN",
        90: "SNIa",
        95: "SLSN-1",
    },
    "mode": "predict",
    "trained_model": MODEL_PATH,
    "class_balanced": True,
    "categorical": False,
    "batch_size": 32,
    "num_epochs": 400,
    "train_proportion": 0.8,
    "val_proportion": 0.1,
    "has_ids": True,
    "with_z": False,
    "output_path_orig": "/path/to/output/dir",
    "trained_model_orig": "/path/to/trained/model",
    "heatmaps_paths": "/path/to/heatmaps",
    "survey": SURVEY,
}

# Variables for incoming data
# A url route is used in setup.sh when the trigger subscription is created.
# It is possible to define multiple routes in a single module and trigger them using different subscriptions.
ROUTE_RUN = "/"  # HTTP route that will trigger run(). Must match setup.sh

# Variables for outgoing data
HTTP_204 = 204  # HTTP code: Success
HTTP_400 = 400  # HTTP code: Bad Request

# GCP resources used in this module
# pittgoogle will construct the full resource names from the MODULE_NAME, SURVEY, and TESTID
TOPIC = pittgoogle.Topic.from_cloud(
    MODULE_NAME, survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)
TOPIC_BIGQUERY_IMPORT_SUPERNNOVA = pittgoogle.Topic.from_cloud(
    "bigquery-import-SCONE", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)

TOPIC_BIGQUERY_IMPORT_CLASSIFICATIONS = pittgoogle.Topic.from_cloud(
    "bigquery-import-classifications", survey=SURVEY, testid=TESTID, projectid=PROJECT_ID
)

app = flask.Flask(__name__)


@app.route(ROUTE_RUN, methods=["POST"])
def run():
    """Classify the alert; publish and store results.

    This module is intended to be deployed as a Cloud Run service. It will operate as an HTTP endpoint
    triggered by Pub/Sub messages. This function will be called once for every message sent to this route.
    It should accept the incoming HTTP request and return a response.

    Returns
    -------
    response : tuple(str, int)
        Tuple containing the response body (string) and HTTP status code (int). Flask will convert the
        tuple into a proper HTTP response. Note that the response is a status message for the web server
        and should not contain the classification results.
    """
    # extract the envelope from the request that triggered the endpoint
    # this contains a single Pub/Sub message with the alert to be processed
    envelope = flask.request.get_json()

    # unpack the alert. raises a `BadRequest` if the envelope does not contain a valid message
    try:
        alert = pittgoogle.Alert.from_cloud_run(envelope, "lsst")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400

    # create heatmap and classify
    input_data = _format_for_classifier(alert)
    heatmap = CreateHeatmapsManager().run(scone_config, input_data)
    scone_classification = SconeClassifier(scone_config).run(heatmap)

    # publish
    TOPIC.publish(_create_outgoing_alert(scone_classification), serializer="json")

    return "", HTTP_204


def _format_for_classifier(alert: pittgoogle.Alert) -> pd.DataFrame:
    """Create a DataFrame for input to SCONE."""
    alert_df = alert.dataframe
    scone_df = pd.DataFrame(
        data={
            # select a subset of columns and rename them for SCONE
            # get_key returns the name that the survey uses for a given field
            # for the full mapping, see alert.schema.map
            "object_id": [alert.objectid] * len(alert_df.index),
            "mjd": alert_df[alert.get_key("mjd")[1]],
            "flux": alert_df[alert.get_key("flux")[1]],
            "flux_err": alert_df[alert.get_key("flux_err")[1]],
            "passband": alert_df[alert.get_key("filter")[1]],
        },
        index=alert_df.index,
    )

    return scone_df


class CreateHeatmapsManager:
    def run(self, config, input_data):
        create_heatmaps_object = CreateHeatmapsFull(config)
        return create_heatmaps_object.run(input_data)


class CreateHeatmapsFull(CreateHeatmapsBase):
    def run(self, input_data):
        heatmap = self.create_heatmaps(input_data, [[-30, 150]])
        return heatmap

    @staticmethod
    def _calculate_mjd_range(sn_data):
        mjd_range = [np.min(sn_data["mjd"]), np.max(sn_data["mjd"])]
        return mjd_range


def _create_outgoing_alert(scone_classification):
    return pittgoogle.Alert.from_dict(scone_classification)
