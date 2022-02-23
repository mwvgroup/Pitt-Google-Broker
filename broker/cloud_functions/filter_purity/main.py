#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Filter alerts for purity."""

import base64
from google.cloud import logging
import os

from broker_utils import data_utils, gcp_utils, schema_maps


PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# connect to the logger
logging_client = logging.Client()
log_name = "filter-purity"  # same log for all broker instances
logger = logging_client.logger(log_name)

# GCP resources used in this module
bq_dataset = f"{SURVEY}_alerts"
ps_topic = f"{SURVEY}-exgalac_trans_cf"
if TESTID != "False":  # attach the testid to the names
    bq_dataset = f"{bq_dataset}_{TESTID}"
    ps_topic = f"{ps_topic}-{TESTID}"
bq_table = f"{bq_dataset}.SuperNNova"

schema_map = schema_maps.load_schema_map(SURVEY, TESTID)


def run(msg: dict, context) -> None:
    """Filter for likely extragalactic transients, publish results.

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
    # logger.log_text(f"{type(msg['data'])}', severity='DEBUG")
    # logger.log_text(f"{msg['data']}', severity='DEBUG")

    alert_dict = data_utils.decode_alert(
        base64.b64decode(msg["data"]), drop_cutouts=True, schema_map=schema_map
    )
    attrs = {
        schema_map["objectId"]: str(alert_dict[schema_map["objectId"]]),
        schema_map["sourceId"]: str(alert_dict[schema_map["sourceId"]]),
    }

    # # run the alert through the filter.
    # alert_is_pure = <set to boolean. True if alert passes purity filter, else False>
    #
    # # if it passes the filter, publish to Pub/Sub:
    # gcp_utils.publish_pubsub(ps_topic, alert_dict, attrs=attrs)
    #
    # # store results to BigQuery, regardless of whether it passes the filter
    # purity_dict = {
    #     **attrs,  # objectId and sourceId
    #     'classifier': 'is_pure',
    #     'predicted_class': int(alert_is_pure),
    # }
    # errors = gcp_utils.insert_rows_bigquery(bq_table, [purity_dict])
    # if len(errors) > 0:
    #     logger.log_text(f"BigQuery insert error: {errors}", severity="DEBUG")

    return
