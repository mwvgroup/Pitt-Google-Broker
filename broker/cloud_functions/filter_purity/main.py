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
class_table = f"{bq_dataset}.classifications" 

purity_table = f"{bq_dataset}.purity"

schema_map = schema_maps.load_schema_map(SURVEY, TESTID)


def is_pure(alert_dict, schema_map):
    """Adapted from: https://zwickytransientfacility.github.io/ztf-avro-alert/filtering.html

    Quoted from the source:

    ZTF alert streams contain an nearly entirely unfiltered stream of all
    5-sigma (only the most obvious artefacts are rejected). Depending on your
    science case, you may wish to improve the purity of your sample by filtering
    the data on the included attributes.

    Based on tests done at IPAC (F. Masci, priv. comm), the following filter
    delivers a relatively pure sample.
    """
    source = alert_dict[schema_map['source']]

    rb = (source['rb'] >= 0.65)  # RealBogus score

    if schema_map['SURVEY'] == 'decat':
        is_pure = rb

    elif schema_map['SURVEY'] == 'ztf':
        nbad = (source['nbad'] == 0)  # num bad pixels
        fwhm = (source['fwhm'] <= 5)  # Full Width Half Max, SExtractor [pixels]
        elong = (source['elong'] <= 1.2)  # major / minor axis, SExtractor
        magdiff = (abs(source['magdiff']) <= 0.1)  # aperture - psf [mag]
        is_pure = (rb and nbad and fwhm and elong and magdiff)



    purity_reason_dict = {
        'is_pure': int(is_pure),
        'rb': int(rb),
        'nbad': int(nbad),
        'fwhm': int(fwhm),
        'elong': int(elong),
        'magdiff': int(magdiff),
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


    purity_reason_dict = is_pure(alert_dict, schema_map)

    # # run the alert through the filter.
    # alert_is_pure = <set to boolean. True if alert passes purity filter, else False> (gotten from dict)
    #
    alert_is_pure = purity_reason_dict['class']

    # # Publish to Pub/Sub:
    # gcp_utils.publish_pubsub(ps_topic, alert_dict, attrs=attrs)
    #
    gcp_utils.publish_pubsub(
            ps_topic, {"alert": alert_dict, "is_pure": purity_reason_dict}, attrs={**attrs, 'is_pure': alert_is_pure} # check to make sure 'is_pure' can be integer
        )
 

    # # store results to BigQuery, regardless of whether it passes the filter
    class_dict = {
        **attrs,  # objectId and sourceId (same thing as candId, but we call it a sourceId in our
                  #  internal broker) [** is a splat, it takes the elements from attrs dict and unpacks
                  #   it and passes it to the new dict constr, and passes it as individual elements]
        'classifier': 'purity',
        'classifier_version': 0.1,
        'class': alert_is_pure,
    }

    errors = gcp_utils.insert_rows_bigquery(class_table, [class_dict])
    if len(errors) > 0:
        logger.log_text(f"BigQuery insert error: {errors}", severity="DEBUG")

    # Creating a copy of purity_reason_dict
    prd_copy = dict(purity_reason_dict) 

    # Changing the name of first key from 'is_pure' to 'class'
    prd_copy['class'] = prd_copy.pop('is_pure')
    
    # # store results to BigQuery, regardless of whether it passes the filter
    purity_dict = {
        **attrs,
        'classifier_version': 0.1,
        **prd_copy,     
    }

    errors = gcp_utils.insert_rows_bigquery(purity_table, [purity_dict])
    if len(errors) > 0:
        logger.log_text(f"BigQuery insert error: {errors}", severity="DEBUG")


    return
