#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Classify an alert using ORACLE (Shah et al. 2025).

This code is intended to be containerized and deployed to Google Cloud Run.
Once deployed, individual alerts in the "trigger" stream will be delivered to the container as HTTP requests.
"""

import os
from pathlib import Path
import flask  # Manage the HTTP request containing the alert
import pittgoogle  # Manipulate the alert and interact with cloud resources

import pandas as pd
from astropy.table import Table
from astroOracle.pretrained_models import ORACLE_lite

import google.cloud.logging

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
MODULE_NAME = "ORACLE"
MODULE_VERSION = 0.1

# classifier variables
model_dir_name = "./"
model_file_name = "best_no_md_model.h5"
MODEL_PATH = Path(__file__).resolve().parent / model_dir_name / model_file_name

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
        alert_lite = pittgoogle.Alert.from_cloud_run(envelope, "default")
    except pittgoogle.exceptions.BadRequest as exc:
        return str(exc), HTTP_400
    
    model_lite = ORACLE_lite(MODEL_PATH)
    oracle_classification = model_lite.predict([_format_for_classifier(alert_lite)]).to_dict(orient='records')[0]

    level_1_class = _most_likely_class(oracle_classification, ['Transient', 'Variable'])
    level_2_class = _most_likely_class(oracle_classification, ['SN', 'Fast', 'Long',    # Transient
                                                               'Periodic', 'AGN'])      # Variable
    leaf_class = _most_likely_class(oracle_classification, ['SNIa', 'SNIb/c', 'SNIax', 'SNI91bg', 'SNII',   # SN
                                                            'KN', 'Dwarf Novae', 'uLens', 'M-dwarf Flare',  # Fast
                                                            'SLSN', 'TDE', 'ILOT', 'CART', 'PISN',          # Long
                                                            'Cepheid', 'RR Lyrae', 'Delta Scuti', 'EB',     # Periodic
                                                            'AGN'])                                         # AGN

    # publish
    outpt_dict = {
        "output": oracle_classification,
        "predicted_level_1": level_1_class[0],
        "predicted_level_1_prob": level_1_class[1],
        "predicted_level_2": level_2_class[0],
        "predicted_level_2_prob": level_2_class[1],
        "predicted_leaf": leaf_class[0],
        "predicted_leaf_prob": leaf_class[1]
    }

    TOPIC.publish(
        pittgoogle.Alert.from_dict(
            payload={'alert_lite': alert_lite.dict['alert_lite'], 'ORACLE': outpt_dict},
            attributes={
                **alert_lite.attributes,
                'pg_oracle_class': outpt_dict['predicted_leaf'],
            },
            schema_name='default',
        )
    )

    return "", HTTP_204

def y_to_Y(band):
    if band == 'y':
        return 'Y'
    return band

# this could use improvement
def get_photflag(flux):
    if flux[1] > 5*abs(flux[0]):
        return 1024
    elif abs(flux[0]) < max(100, flux[1]):
        return 0
    else:
        return 4096

def _format_for_classifier(alert: pittgoogle.Alert) -> pd.DataFrame:
    """Create a DataFrame for input to ORACLE."""
    alert_df = alert.dataframe
    t = Table([alert_df[alert.get_key("mjd")[1]],
               alert_df[alert.get_key("filter")[1]],
               alert_df[alert.get_key("flux")[1]],
               alert_df[alert.get_key("flux_err")[1]]],
               names=('MJD', 'BAND', 'FLUXCAL', 'FLUXCALERR'))
    
    t['PHOTFLAG'] = [get_photflag(flux) for flux in zip(t['FLUXCAL'], t['FLUXCALERR'])]
    t['BAND'] = [y_to_Y(band) for band in t['BAND']]
    MJD_min = min(t['MJD'])
    t['MJD'] = [MJD - MJD_min for MJD in t['MJD']]
    t.sort('MJD')
    return t.to_pandas()

def _most_likely_class(probability_dict: dict, keys: list) -> tuple[str, float]:
    max_val = 0
    max_class = None
    for key in keys:
        if max_val < probability_dict[key]:
            max_val = probability_dict[key]
            max_class = key
    return (max_class, max_val)