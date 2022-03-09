#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Filter alerts for purity."""

import base64
import os
from google.cloud import logging

# Add these to requirements.txt but check to make sure that the format of adding is correct
from broker_utils import data_utils, gcp_utils, schema_maps



PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID") # This returns a string which is configured when the broker
                             # instance is initially set up. 
                             # (i.e. This is an input variable to the setup script)
SURVEY = os.getenv("SURVEY") # This will return ztf (in future will be our LSST)

# connect to the logger
logging_client = logging.Client()
log_name = "filter-purity"  # same log for all broker instances
logger = logging_client.logger(log_name)

# GCP resources used in this module
bq_dataset = f"{SURVEY}_alerts"

# Changed the name stub of ps_topic from exgalac_trans_cs to alerts_pure
ps_topic = f"{SURVEY}-alerts_pure" # This is the name of the Pub/Sub topic that this
                                   # module publishes to. (Publishes original alert
                                   # plus its own results. The next module downstream
                                   # in the pipeline will listen to this topic)
if TESTID != "False":  # attach the testid to the names
    bq_dataset = f"{bq_dataset}_{TESTID}"
    ps_topic = f"{ps_topic}-{TESTID}"

# Changed the name stub of the BigQuery table from SuperNNova to classifications
bq_table = f"{bq_dataset}.classifications"

schema_map = schema_maps.load_schema_map(SURVEY, TESTID)


def is_pure(alert, schema_map):
    """Adapted from: https://zwickytransientfacility.github.io/ztf-avro-alert/filtering.html

    Quoted from the source:

    ZTF alert streams contain an nearly entirely unfiltered stream of all
    5-sigma (only the most obvious artefacts are rejected). Depending on your
    science case, you may wish to improve the purity of your sample by filtering
    the data on the included attributes.

    Based on tests done at IPAC (F. Masci, priv. comm), the following filter
    delivers a relatively pure sample.
    """
    source = alert[schema_map['source']]

    rb = (source['rb'] >= 0.65)  # RealBogus score

    if schema_map['SURVEY'] == 'decat':
        is_pure = rb

    elif schema_map['SURVEY'] == 'ztf':
        nbad = (source['nbad'] == 0)  # num bad pixels
        fwhm = (source['fwhm'] <= 5)  # Full Width Half Max, SExtractor [pixels]
        elong = (source['elong'] <= 1.2)  # major / minor axis, SExtractor
        magdiff = (abs(source['magdiff']) <= 0.1)  # aperture - psf [mag]
        is_pure = (rb and nbad and fwhm and elong and magdiff)

    # Update this function so that it returns a dictionary with 6 key / value pairs: 
    #   1 for the final result (is_pure) and one for each of the 5 cuts (rb, nbad, etc.)
    # We want to save all of these results so that later we can look back and know 
    #  exactly why an alert did / didn't pass this filter.

    # Make sure you update the run() function to accommodate the new output.

    purity_reason_dict = {
        'is_pure': is_pure,
        'rb': rb,
        'nbad': nbad,
        'fwhm': fwhm,
        'elong': elong
        'magdiff': magdiff,
    }

    return purity_reason_dict



def run(msg: dict, context) -> None:
    """Filter alerts for purity, publish results.

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
    ) # this decodes the alert
    attrs = {
        schema_map["objectId"]: str(alert_dict[schema_map["objectId"]]),
        schema_map["sourceId"]: str(alert_dict[schema_map["sourceId"]]),
    } # this gets the custom attr for filtering

    # # run the alert through the filter.
    # alert_is_pure = <set to boolean. True if alert passes purity filter, else False> (gotten from dict)
    #
    alert_is_pure = purity_reason_dict['is_pure']

    # # Publish to Pub/Sub:
    # gcp_utils.publish_pubsub(ps_topic, alert_dict, attrs=attrs)
    #
    gcp_utils.publish_pubsub(
            ps_topic, {"alert": alert_dict, "is_pure": purity_reason_dict}, attrs=attrs
        )
    # So here I have "is_pure" key with the purity_reason_dict as the value, this is the
    # whole dictionary with the corresponding data as to why the alert passed or did not.
    # Was not sure if you just wanted the true or false, but figured that was also in
    # the dictionary.

    # # store results to BigQuery, regardless of whether it passes the filter
    purity_dict = {
        **attrs,  # objectId and sourceId
        'classifier': 'is_pure',
        'predicted_class': int(alert_is_pure), 
    }
    
    errors = gcp_utils.insert_rows_bigquery(bq_table, [purity_dict])
    if len(errors) > 0:
        logger.log_text(f"BigQuery insert error: {errors}", severity="DEBUG")



    return
