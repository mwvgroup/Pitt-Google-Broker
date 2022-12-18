#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Classify alerts using SuperNNova (M¨oller & de Boissi`ere 2019)."""

from astropy.time import Time
import base64
from google.cloud import logging
import json
import numpy as np
import pandas as pd
import os
from pathlib import Path
from supernnova.validation.validate_onthefly import classify_lcs
from typing import Tuple


from broker_utils import data_utils, gcp_utils, math
from broker_utils.types import _AlertIds


PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# connect to the logger
logging_client = logging.Client()
log_name = "classify-snn-cloudfnc"  # same log for all broker instances
logger = logging_client.logger(log_name)

# GCP resources used in this module
bq_dataset = f"{SURVEY}_alerts"
ps_topic = f"{SURVEY}-SuperNNova"
if TESTID != "False":  # attach the testid to the names
    bq_dataset = f"{bq_dataset}_{TESTID}"
    ps_topic = f"{ps_topic}-{TESTID}"

bq_table = f"{bq_dataset}.SuperNNova"

# Changed the name stub of the BigQuery table from SuperNNova to classifications
class_table = f"{bq_dataset}.classifications"

model_dir_name = "ZTF_DMAM_V19_NoC_SNIa_vs_CC_forFink"
model_file_name = (
    "vanilla_S_0_CLF_2_R_none_photometry_DF_1.0_N_global_lstm_32x2_0.05_128_True_mean.pt"
)
model_path = Path(__file__).resolve().parent / f"{model_dir_name}/{model_file_name}"


def run(msg: dict, context) -> None:
    """Classify alert with SuperNNova; publish and store results.

    For args descriptions, see:
    https://cloud.google.com/functions/docs/writing/background#function_parameters

    This function is intended to be triggered by Pub/Sub messages, via Cloud Functions.

    Args:
        msg: Pub/Sub message data and attributes.
            `data` field contains the message data in a base64-encoded string.
            `attributes` field contains the message's custom attributes in a dict.

        context: The Cloud Function's event metadata.
            It has the following attributes:
                `event_id`: the Pub/Sub message ID.
                `timestamp`: the Pub/Sub message publish time.
                `event_type`: for example: "google.pubsub.topic.publish".
                `resource`: the resource that emitted the event.
            This argument is not currently used in this function, but the argument is
            required by Cloud Functions, which will call it.
    """
    alert_lite = data_utils.open_alert(msg["data"])  # Use this in ach module to load alert_lite

    # classify
    try:
        snn_dict = _classify_with_snn(alert_lite)

    # if something goes wrong, let's just log it and exit gracefully
    # once we know more about what might go wrong, we can make this more specific
    except Exception as e:
        logger.log_text(f"Classify error: {e}", severity="WARNING")

    else:
        # announce to pubsub
        attrs = msg["attributes"]
        gcp_utils.publish_pubsub(ps_topic, {**alert_lite, "SuperNNova": snn_dict}, attrs=attrs)

        # store in bigquery
        errors = gcp_utils.insert_rows_bigquery(
            bq_table,
            [
                {
                    **snn_dict,
                    "objectId": alert_lite["alertIds"]["objectId"],
                    "candid": alert_lite["alertIds"]["sourceId"],
                }
            ],
        )
        if len(errors) > 0:
            logger.log_text(f"BigQuery insert error: {errors}", severity="WARNING")

        classifications = [
            {
                "objectId": attrs["objectId"],
                "candid": attrs["candid"],
                "classifier": "SuperNNova",
                "classifier_version": 1.3,
                "class": snn_dict["predicted_class"],
                "probability": max(snn_dict["prob_class0"], snn_dict["prob_class1"]),
            }
        ]

        # store in bigquery
        errors = gcp_utils.insert_rows_bigquery(class_table, classifications)
        if len(errors) > 0:
            logger.log_text(f"BigQuery insert error: {errors}", severity="WARNING")


def _classify_with_snn(alert_dict: dict) -> dict:
    """Classify the alert using SuperNNova."""
    # init
    snn_df = _format_for_snn(alert_dict)
    device = "cpu"

    # classify
    _, pred_probs = classify_lcs(snn_df, model_path, device)

    # extract results to dict and attach object/source ids.
    # use `.item()` to convert numpy -> python types for later json serialization
    pred_probs = pred_probs.flatten()
    snn_dict = {
        "prob_class0": pred_probs[0].item(),
        "prob_class1": pred_probs[1].item(),
        "predicted_class": np.argmax(pred_probs).item(),
    }

    return snn_dict


def _format_for_snn(alert_dict: dict) -> pd.DataFrame:
    """Compute features and cast to a DataFrame for input to SuperNNova."""

    # cast alert to dataframe
    alert_df = data_utils.alert_lite_to_dataframe(
        alert_dict
    )  # again can we remove schema map from this funciton

    # start a dataframe for input to SNN
    snn_df = pd.DataFrame(data={"SNID": alert_dict["alertIds"]["objectId"]}, index=alert_df.index)

    # create the columns expected by SNN
    snn_df["FLT"] = alert_df["fid"].map(data_utils.ztf_fid_names())  ## REMOVE SCHEMA

    if SURVEY == "ztf":
        snn_df["MJD"] = math.jd_to_mjd(alert_df["jd"].loc[0])  # ADDED .loc[0]
        snn_df["FLUXCAL"], snn_df["FLUXCALERR"] = math.mag_to_flux(
            alert_df["magpsf"],
            alert_df["magzpsci"],  ## REMOVE SCHEMA
            alert_df["sigmapsf"],  ## REMOVE SCHEMA
        )

    elif SURVEY == "decat":
        col_map = {"mjd": "MJD", "flux": "FLUXCAL", "fluxerr": "FLUXCALERR"}
        for acol, scol in col_map.items():
            snn_df[scol] = alert_df[acol]

    return snn_df
