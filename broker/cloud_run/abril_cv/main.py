#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Cross match alerts with the Abril 2020 CV catalog."""

import base64
import os

from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy_healpix import HEALPix
from flask import Flask, request
from google.cloud import logging
import pandas as pd

from broker_utils import data_utils, gcp_utils, schema_maps


app = Flask(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# connect to the logger
logging_client = logging.Client()
log_name = "xmatch-AbrilCVs-cloudrun"  # same log for all broker instances
logger = logging_client.logger(log_name)

# GCP resources used in this module
bq_dataset = f"{SURVEY}_alerts"
ps_topic = f"{SURVEY}-xmatch_AbrilCVs"
if TESTID != "False":  # attach the testid to the names
    bq_dataset = f"{bq_dataset}_{TESTID}"
    ps_topic = f"{ps_topic}-{TESTID}"
bq_table = f"{bq_dataset}.xmatch"

# schema_map = schema_maps.load_schema_map(SURVEY, TESTID)
import json
from google.cloud import bigquery, pubsub_v1
import yaml
with open('ztf.yaml') as f:
    schema_map = yaml.safe_load(f)  # dict

MAX_SEP = 1.0 * u.arcsec
CATALOG = "J_MNRAS_492_L40/catalog_condensed.dat"


@app.route("/abrilcv", methods=["POST"])
def index():
    """Entry point for Cloud Run trigger."""
    alert_dict = unpack_envelope(envelope=request.get_json())

    abrilcv_dict = _xmatch_abril_cv(alert_dict)

    # announce and store results
    is_abril_cv = 0 if len(abrilcv_dict) == 0 else 1  # 1 = True; 0 = False
    attrs = {
        schema_map["objectId"]: str(alert_dict[schema_map["objectId"]]),
        schema_map["sourceId"]: str(alert_dict[schema_map["sourceId"]]),
        "Abril_CV": str(is_abril_cv)
    }
    # gcp_utils.publish_pubsub(
    #     ps_topic, {"alert": alert_dict, "Abril_CV": abrilcv_dict},
    #     attrs=attrs,
    #     project_id=PROJECT_ID,
    # )
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, ps_topic)
    # logger.log_text(f"topic: {topic_path}", severity="DEBUG")
    message = json.dumps({"alert": alert_dict, "Abril_CV": abrilcv_dict}).encode('utf-8')
    try:
        future = publisher.publish(topic_path, data=message, **attrs)
        future.result()
    except Exception as e:
        logger.log_text(f"{e}", severity="DEBUG")

    if is_abril_cv == 1:
        _store_bigquery(abrilcv_dict, attrs)

    return ("", 204)


def _xmatch_abril_cv(alert_dict):
    """Search the Abril 2020 CV catalog for a positional match."""
    alertcoords = SkyCoord(
        alert_dict[schema_map['source']]['ra'],
        alert_dict[schema_map['source']]['dec'],
        frame='icrs',
        unit='deg',
    )
    abrildf = pd.read_csv(CATALOG)

    # get list of all pixels that overlap with with the search cone
    hp, hpcol, frame = _create_healpix(abrildf)
    pixel_list = hp.cone_search_skycoord(alertcoords, radius=MAX_SEP)

    # get the closest CV within MAX_SEP
    nearby_cvs = _get_nearby_cvs(abrildf, alertcoords, frame, hpcol, pixel_list)  # df
    try:
        match = nearby_cvs.sort_values('separation', ascending=True).iloc[0]  # series
    except (IndexError, KeyError):
        abrilcv_dict = {}  # no match found
    else:
        abrilcv_dict = match.to_dict()

    return abrilcv_dict


def _get_nearby_cvs(abrildf, alertcoords, frame, hpcol, pixel_list):
    def calc_separation(row):
        cvcoords = SkyCoord(row["RAdeg"], row["DEdeg"], frame=frame, unit='deg')
        sep = alertcoords.separation(cvcoords)
        if sep <= MAX_SEP:
            return sep.to(u.arcsec).value
        else:
            return None

    nearby_cvs = abrildf.loc[abrildf[hpcol].isin(pixel_list), :].copy()
    if len(nearby_cvs) > 0:
        nearby_cvs['separation'] = nearby_cvs.apply(calc_separation, axis=1)
        nearby_cvs = nearby_cvs.dropna(subset=['separation'])

    return nearby_cvs


def _create_healpix(abrildf):
    """Instantiate a pixelization as indicated by abrildf."""
    hpcols = [c for c in abrildf.columns if c.split("_")[0] == "HEALPix"]
    try:
        hpcol = hpcols[0]
        tmp = hpcol.split("_")
        n, order, frame = tmp[1], tmp[2], tmp[3]
    except Exception:
        raise ValueError("Cannot parse HEALPix column name.")

    hp = HEALPix(nside=2**int(n), order=order, frame=frame)
    return (hp, hpcol, frame)


def unpack_envelope(envelope):
    """Check the envelope for errors; unpack and return alert as dict."""
    # do some checks
    if not envelope:
        msg = "no Pub/Sub message received"
        print(f"error: {msg}")
        return f"Bad Request: {msg}", 400

    if not isinstance(envelope, dict) or "message" not in envelope:
        msg = "invalid Pub/Sub message format"
        print(f"error: {msg}")
        return f"Bad Request: {msg}", 400

    # unpack the alert
    msg = envelope["message"]
    alert_dict = data_utils.decode_alert(
        base64.b64decode(msg["data"]), drop_cutouts=True, schema_map=schema_map
        # msg["data"], drop_cutouts=True, schema_map=schema_map
    )

    return alert_dict


def _store_bigquery(abrilcv_dict, attrs):
    """Store the cross match results in BigQuery."""
    # if there is no match, skip bq storage
    # if len(wise_dict) == 0:
    #     return

    # create dict to upload to bigquery
    store_dict = dict(attrs)
    # prepend the catalog id
    prefix = "AbrilCV"
    store_dict.update({f'{prefix}_{k}': v for k, v in abrilcv_dict.items()})

    # store to bigquery
    # gcp_utils.insert_rows_bigquery(bq_table, [store_dict])
    keep_cols = [
        "objectId",
        "candid",
        "AbrilCV_Name",
        "AbrilCV_Type1",
        "AbrilCV_Type2",
        "AbrilCV_HEALPix_17_nested_icrs",
        "AbrilCV_separation"
    ]

    def cast_nan_to_none(value):
        """BigQuery can't handle NaN; replace with None."""
        return None if pd.isna(value) else value
    sdict = {
        k: cast_nan_to_none(v) for k, v in store_dict.items() if k in keep_cols
    }

    bq_client = bigquery.Client(project=PROJECT_ID)
    table = bq_client.get_table(bq_table)
    try:
        errors = bq_client.insert_rows(table, [sdict])
    except Exception as e:
        logger.log_text(f"Errors uploading to BigQuery: {e}", severity="DEBUG")
    else:
        if len(errors) > 0:
            logger.log_text(f"Errors uploading to BigQuery: {errors}", severity="DEBUG")


if __name__ == "__main__":
    PORT = int(os.getenv("PORT")) if os.getenv("PORT") else 8080

    # This is used when running locally. Gunicorn is used to run the
    # application on Cloud Run. See entrypoint in Dockerfile.
    app.run(host="127.0.0.1", port=PORT, debug=True)
