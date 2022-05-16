#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Publish stream for ELAsTiCC using brokerClassification schema in the following repo.

https://github.com/LSSTDESC/plasticc_alerts/blob/main/Examples/plasticc_schema
"""

import base64
import os
from typing import Tuple

import fastavro
from flask import Flask, request
from google.cloud import logging

from broker_utils import data_utils, gcp_utils, schema_maps

app = Flask(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")  # elasticc

# connect to the logger
logging_client = logging.Client()
log_name = "elasticc-stream"  # same log for all broker instances
logger = logging_client.logger(log_name)

# GCP resources used in this module
ps_topic = f"{SURVEY}-classifications"
if TESTID != "False":  # attach the testid to the names
    ps_topic = f"{ps_topic}-{TESTID}"

schema_map = schema_maps.load_schema_map(SURVEY, TESTID)
schema_out = fastavro.schema.load_schema("elasticc.v0_9.brokerClassfication.avsc")


@app.route("/", methods=["POST"])
def index() -> Tuple[str, int]:
    """Entry point for Cloud Run trigger."""
    msg = _unpack_envelope(request.get_json())
    # if there was an error, msg is a tuple. return immediately.
    if isinstance(msg, Tuple):
        return msg
    # else, unpack
    alert_dict, attrs = _unpack_message(msg)

    # create the message for elasticc and publish the stream
    avro = _create_elasticc_msg(alert_dict, attrs)
    gcp_utils.publish_pubsub(ps_topic, avro)

    return ("", 204)

def _unpack_envelope(envelope: dict) -> dict:
    """Check that the incoming envelope is valid and return the enclosed message."""
    if not envelope:
        msg = ("Bad Request: no Pub/Sub message received", 400)
        logger.log_text(err_msg, severity="DEBUG")

    elif isinstance(envelope, dict) or "message" not in envelope:
        msg = ("Bad Request: invalid Pub/Sub message format", 400)
        logger.log_text(err_msg, severity="DEBUG")

    else:
        msg = envelope["message"]

    return msg


def _unpack_message(msg: dict) -> Tuple[dict, dict]:
    """Unpack the alert."""
    alert_dict = data_utils.decode_alert(
        base64.b64decode(msg["data"]), drop_cutouts=True, schema_map=schema_map
    )
    return alert_dict, msg["attributes"]


def _create_elasticc_msg(alert_dict, attrs):
    """Create a message according to the ELAsTiCC broker classifications schema.

    https://github.com/LSSTDESC/plasticc_alerts/blob/main/Examples/plasticc_schema
    """
    # original elasticc alert as a dict
    elasticc_alert = alert_dict["alert"]

    # dict with the following keys:
    #   schema_map["objectId"]
    #   schema_map["sourceId"]
    #   "prob_class0"
    #   "prob_class1"
    #   "predicted_class"
    supernnova_results = alert_dict["SuperNNova"]

    # here are a few things you'll need
    elasticcPublishTimestamp = attrs["kafka.timestamp"]
    brokerIngestTimestamp = attrs["ingest_time"]  # Troy: attach this in first module
    brokerVersion = "v0.6"

    classifications = [
        {
            "classifierName": "SuperNNova_v1.3",  # Troy: pin version in classify_snn
            # Chris: fill these two in. classIds are listed here:
            #        https://docs.google.com/presentation/d/1FwOdELG-XgdNtySeIjF62bDRVU5EsCToi2Svo_kXA50/edit#slide=id.ge52201f94a_0_12
            "classifierParams": "",  # leave this blank for now
            "classId": 111120,
            "probability": supernnova_results["prob_class0"], 
        },
    ]

    # Chris: fill this in with the correct key/value pairs.
    #        it is the dictionary that will be sent to elasticc, so it needs these:
    #        https://github.com/LSSTDESC/plasticc_alerts/blob/main/Examples/plasticc_schema/elasticc.v0_9.brokerClassification.avsc
    msg = {
        "alertId": elasticc_alert["alertId"],
        "diaSourceId": elasticc_alert[schema_map["source"]][schema_map["sourceId"]],
        "elasticcPublishTimestamp": elasticcPublishTimestamp, 
        "brokerIngestTimestamp": brokerIngestTimestamp,
        "brokerName": "Pitt-Google Broker",
        "brokerVersion": brokerVersion,
        "classifications": classifications
    }

    # avro serialize the dictionary
    avro = _dict_to_avro(msg, schema_out)

    return avro

def _dict_to_avro(msg: dict, schema: dict):
    """Avro serialize a dictionary."""
    fout = io.BytesIO()
    fastavro.writer(fout, schema, [msg])
    fout.seek(0)
    avro = fout.getvalue()
    return avro


if __name__ == "__main__":
    PORT = int(os.getenv("PORT")) if os.getenv("PORT") else 8080

    # This is used when running locally. Gunicorn is used to run the
    # application on Cloud Run. See entrypoint in Dockerfile.
    app.run(host="127.0.0.1", port=PORT, debug=True)