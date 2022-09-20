#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Publish stream for ELAsTiCC using brokerClassification schema in the following repo.

https://github.com/LSSTDESC/plasticc_alerts/blob/main/Examples/plasticc_schema
"""

import base64
import io
import os

import fastavro
from google.cloud import logging
import json

from broker_utils import gcp_utils
from broker_utils.schema_maps import load_schema_map, get_value
from broker_utils.data_utils import open_alert


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

schema_map = load_schema_map(SURVEY, TESTID)
schema_out = fastavro.schema.load_schema("elasticc.v0_9.brokerClassfication.avsc")


def run(msg: dict, context) -> None:
    """Publish Pitt-Google's classifications.

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
    #alert_dict = json.loads(base64.b64decode(msg["data"]).decode("utf-8"))
    alert_dict = open_alert(msg["data"])
    attrs = msg["attributes"]

    # create the message for elasticc and publish the stream
    avro = _create_elasticc_msg(alert_dict, attrs)
    gcp_utils.publish_pubsub(ps_topic, avro, attrs=attrs)


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
    elasticcPublishTimestamp = int(attrs["kafka.timestamp"])
    brokerIngestTimestamp = int(attrs["brokerIngestTimestamp"])  # Troy: attach this in first module
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
        "diaSourceId": get_value("sourceId", elasticc_alert, schema_map),
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
