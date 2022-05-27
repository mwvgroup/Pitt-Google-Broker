#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Filter alerts for purity."""

import base64
import numpy as np
import os
from google.cloud import logging
from astropy import units as u

# Add these to requirements.txt but check to make sure that the format of adding is correct
from broker_utils import data_utils, gcp_utils, schema_maps



PROJECT_ID = os.getenv("GCP_PROJECT") # For local test set this to GOOGLE_CLOUD_PROJECT

TESTID = os.getenv("TESTID") # This returns a string which is configured when the broker
                             # instance is initially set up. When we create resources 
                             # in the cloud, we need unique test names. 
                             # (i.e. This is an input variable to the setup script)
                             # We cannot have separate pub/sub streams with the same
                             # name, (i.e. is_pure), so the testID is appended
                             # to all the resource names for the instance you set up
                             # (When we deploy to the cloud we set up a broker instance).
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

tags_table = f"{bq_dataset}.tags" # THIS SHOULD BE CHANGED TO 'tags'




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



def _is_extragalactic_transient(alert_dict: dict, schema_map) -> dict:
    """Check whether alert is likely to be an extragalactic transient.
    Adapted from:
    https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """
    if schema_map["SURVEY"] == "decat":
        # No straightforward way to translate this ZTF filter for DECAT.
        # DECAT alert does not include whether the subtraction (sci-ref) is
        # positive, nor SExtractor results,
        # and the included xmatch data is significantly different.
        # However, DECAT is a transient survey.
        # Assume the alert should pass the filter:
        is_extragalactic_transient = True

    elif schema_map["SURVEY"] == "ztf":
        dflc = data_utils.alert_dict_to_dataframe(alert_dict, schema_map)
        candidate = dflc.loc[0]

        is_positive_sub = candidate["isdiffpos"] == "t"

        if (candidate["distpsnr1"] is None) or (candidate["distpsnr1"] > 1.5):  # arcsec
            no_pointsource_counterpart = True
            # closest candidate == star < 1.5 arcsec away -> candidate probably star
        else:
            no_pointsource_counterpart = candidate["sgscore1"] < 0.5

        where_detected = dflc["isdiffpos"] == "t"
        if np.sum(where_detected) >= 2:
            detection_times = dflc.loc[where_detected, "jd"].values
            dt = np.diff(detection_times)
            not_moving = np.max(dt) >= (30 * u.minute).to(u.day).value
        else:
            not_moving = False

        no_ssobject = (
            (candidate["ssdistnr"] is None)
            or (candidate["ssdistnr"] < 0)
            or (candidate["ssdistnr"] > 5)
        )
        # candidate['ssdistnr'] == -999 is another encoding of None

        is_extragalactic_transient = (
            is_positive_sub
            and no_pointsource_counterpart
            and not_moving
            and no_ssobject
        )

    exgalac_dict = {
        'is_extragalactic_transient': int(is_extragalactic_transient), # # DO we want these to be the words true or false or ints
        'is_positive_sub': int(is_positive_sub),
        'no_pointsource_counterpart': int(no_pointsource_counterpart),
        'not_moving': int(not_moving),
        'no_ssobject': int(no_ssobject),
    }

    return exgalac_dict



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

    schema_map = schema_maps.load_schema_map(SURVEY, TESTID) # This is pulling from a bucket in the cloud

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


    extragalactic_dict = _is_extragalactic_transient(alert_dict, schema_map) ## ADDED

    # # run the alert through the filter.

    # # Publish to Pub/Sub:
    # gcp_utils.publish_pubsub(ps_topic, alert_dict, attrs=attrs)
    #
    gcp_utils.publish_pubsub(
            ps_topic, 
            alert_dict, 
            attrs={**attrs, **{k: str(v) for k, v in purity_reason_dict}, **{k: str(v) for k, v in extragalactic_dict}, 'fid': str(alert_dict[schema_map["source"]]["fid"]),}
    )                                                                      

 


    ### GOT TO HERE RELATIVELY    
        # (Do I need a copy of extragalactic_trans_dict?)
        # ()

    # # store results to BigQuery, regardless of whether it passes the filter
    tags_dict = {
        **attrs,
        'classifier_version': 0.1,
        **purity_reason_dict,
        **extragalactic_dict,     
    }

    errors = gcp_utils.insert_rows_bigquery(tags_table, [tags_dict])
    if len(errors) > 0:
        logger.log_text(f"BigQuery insert error: {errors}", severity="DEBUG")


    # # store results to BigQuery, regardless of whether it passes the filter
    classifications= [ 
        {
            **attrs,  # objectId and sourceId (same thing as candId, but we call it a sourceId in our
                    #  internal broker) [** is a splat, it takes the elements from attrs dict and unpacks
                    #   it and passes it to the new dict constr, and passes it as individual elements]
            'classifier': 'purity',
            'classifier_version': 0.1,
            'class': purity_reason_dict['is_pure'],
        },
        {
            **attrs,  # objectId and sourceId (same thing as candId, but we call it a sourceId in our
                    #  internal broker) [** is a splat, it takes the elements from attrs dict and unpacks
                    #   it and passes it to the new dict constr, and passes it as individual elements]
            'classifier': 'extragalactic_transient',
            'classifier_version': 0.1,
            'class': extragalactic_dict['is_extragalactic_transient'],
        }
    ]

    errors = gcp_utils.insert_rows_bigquery(class_table, classifications)
    if len(errors) > 0:
        logger.log_text(f"BigQuery insert error: {errors}", severity="DEBUG")



    return
