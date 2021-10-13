#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Classify alerts using SuperNNova (M¨oller & de Boissi`ere 2019)."""

import base64
from google.cloud import logging
import json
import numpy as np
import os
import pandas as pd
from pathlib import Path
from supernnova.validation.validate_onthefly import classify_lcs

from broker_utils import data_utils, gcp_utils, schema_maps


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

schema_map = schema_maps.load_schema_map(SURVEY, TESTID)

model_dir_name = "ZTF_DMAM_V19_NoC_SNIa_vs_CC_forFink"
model_file_name = "vanilla_S_0_CLF_2_R_none_photometry_DF_1.0_N_global_lstm_32x2_0.05_128_True_mean.pt"
model_path = Path(__file__).resolve().parent / f"{model_dir_name}/{model_file_name}"


def run(msg: dict, context) -> None:
    """Classify alert with SuperNNova; publish and store results.

    For args descriptions, see:
    https://cloud.google.com/functions/docs/writing/background#function_parameters

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
    """
    alert_dict = json.loads(base64.b64decode(msg["data"]).decode("utf-8"))

    # classify
    try:
        snn_dict = _classify_with_snn(alert_dict)
    except Exception as e:
        logger.log_text(f"Classify error: {e}", severity="DEBUG")

    # announce to pubsub
    attrs = {
        schema_map["objectId"]: str(alert_dict[schema_map["objectId"]]),
        schema_map["sourceId"]: str(alert_dict[schema_map["sourceId"]]),
    }
    gcp_utils.publish_pubsub(
        ps_topic, {"alert": alert_dict, "SuperNNova": snn_dict}, attrs=attrs
    )

    # store in bigquery
    errors = gcp_utils.insert_rows_bigquery(bq_table, [snn_dict])
    if len(errors) > 0:
        logger.log_text(f"BigQuery insert error: {errors}", severity="DEBUG")


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
        schema_map["objectId"]: snn_df.objectId,
        schema_map["sourceId"]: snn_df.sourceId,
        "prob_class0": pred_probs[0].item(),
        "prob_class1": pred_probs[1].item(),
        "predicted_class": np.argmax(pred_probs).item(),
    }

    return snn_dict


def _format_for_snn(alert_dict: dict) -> pd.DataFrame:
    """Compute features and cast to a DataFrame for input to SuperNNova."""
    # cast alert to dataframe
    alert_df = data_utils.alert_dict_to_dataframe(alert_dict, schema_map)

    # start a dataframe for input to SNN
    snn_df = pd.DataFrame(data={"SNID": alert_df.objectId}, index=alert_df.index)
    snn_df.objectId = alert_df.objectId
    snn_df.sourceId = alert_df.sourceId

    # create the columns expected by SNN
    snn_df["FLT"] = alert_df["fid"].map(schema_map["FILTER_MAP"])

    if SURVEY == "ztf":
        snn_df["MJD"] = data_utils.jd_to_mjd(alert_df["jd"])
        snn_df["FLUXCAL"], snn_df["FLUXCALERR"] = data_utils.mag_to_flux(
            alert_df[schema_map["mag"]],
            alert_df[schema_map["magzp"]],
            alert_df[schema_map["magerr"]],
        )

    elif SURVEY == "decat":
        col_map = {"mjd": "MJD", "flux": "FLUXCAL", "fluxerr": "FLUXCALERR"}
        for acol, scol in col_map.items():
            snn_df[scol] = alert_df[acol]

    return snn_df
