#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Cross match alerts with the AllWISE catalog in BigQuery's public datasets.

https://wise2.ipac.caltech.edu/docs/release/allwise/
"""

import base64
from flask import Flask, request
from google.cloud import logging, bigquery
import os
from typing import Optional

from . import allwise
from broker_utils import data_utils, gcp_utils
from broker_utils.schema_maps import load_schema_map, get_key, get_value


app = Flask(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT")
TESTID = os.getenv("TESTID")
SURVEY = os.getenv("SURVEY")

# connect to the logger
logging_client = logging.Client()
log_name = "xmatch-wise-cloudrun"  # same log for all broker instances
logger = logging_client.logger(log_name)

# GCP resources used in this module
bq_dataset = f"{SURVEY}_alerts"
ps_topic = f"{SURVEY}-AllWISE"
if TESTID != "False":  # attach the testid to the names
    bq_dataset = f"{bq_dataset}_{TESTID}"
    ps_topic = f"{ps_topic}-{TESTID}"
bq_table = f"{bq_dataset}.xmatch"

schema_map = load_schema_map(SURVEY, TESTID)
sobjectId, ssourceId = get_key("objectId", schema_map), get_key("sourceId", schema_map)


@app.route("/", methods=["POST"])
def index():
    """Entry point for Cloud Run trigger."""
    envelope = request.get_json()

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
    )
    attrs = {
        sobjectId: get_value("objectId", alert_dict, schema_map),
        ssourceId: get_value("sourceId", alert_dict, schema_map),
    }

    # do the cross match
    wise_dict = _xmatch_wise(alert_dict)

    # announce and store results
    gcp_utils.publish_pubsub(
        ps_topic, {"alert": alert_dict, "AllWISE": wise_dict}, attrs=attrs
    )
    _store_bigquery(wise_dict, attrs)

    return ("", 204)


def _xmatch_wise(alert_dict):
    """Query the AllWISE catalog for positional matches and return them in a dict."""
    sql_stmnt = _create_sql_stmnt()
    job_config = _create_job_config(alert_dict)
    query_job = _query_bigquery(sql_stmnt, job_config=job_config)

    results = {}
    for r, row in enumerate(query_job):
        results[f'allwise{r}'] = dict(row)

    return results


def _create_sql_stmnt():
    """Return the parameterized SQL statement that cross matches the alert to AllWISE.

    The query takes the following parameters:
        @ra: Alert source right ascension in degrees, transformed to [-180, 180] deg.
        @dec: Alert source declination in degrees.
        @max_sep: Maximum separation in arcsec to declare an AllWISE source is a match.
        @polygon: String representing a Polygon geography; restricts the region of space
                  within which BigQuery should search for matches.
        @limit: Maximum number of matches to return (ordered by separation distance).
    """
    cols = _allwise_cols_to_select()
    # Note: ST_DISTANCE() returns the distance (meters) on a sphere with Earth's radius.
    # 30.8874796235 = meters/arcsec on that sphere.
    sql_stmnt = f"""
        CREATE TEMP FUNCTION
            IsWithinMaxSep(p1 GEOGRAPHY, p2 GEOGRAPHY, max_sep_arcsec FLOAT64)
                AS (ST_DISTANCE(p1, p2) < max_sep_arcsec * 30.8874796235);
        SELECT {', '.join(cols)}
        FROM `bigquery-public-data.wise_all_sky_data_release.all_wise`
        WHERE
            IsWithinMaxSep(point, ST_GEOGPOINT(@ra, @dec), @max_sep)
            AND ST_CONTAINS(ST_GEOGFROMTEXT(@polygon), point)
        ORDER BY ST_DISTANCE(point, ST_GEOGPOINT(@ra, @dec))
        LIMIT @limit;
    """

    return sql_stmnt


def _allwise_cols_to_select():
    return [
        # Sexagesimal, equatorial position-based source name in form: hhmmss.ss+ddmmss.s
        'designation',
        'ra',  # J2000 right asc. wrt 2MASS PSC ref frame, non-moving src extraction
        'dec',  # J2000 declination wrt 2MASS PSC ref frame, non-moving src extraction
        # 'sigra',  # One-sigma uncertainty in ra from the non-moving source extraction
        # 'sigdec',  # One-sigma uncertainty in dec from the non-moving source extraction
        'cntr',  # Unique ID number for this object in the AllWISE Catalog/Reject Table
        'source_id',  # Unique source ID
        # # W1 magnitude measured with profile-fitting photometry, or the magnitude of the
        # # 95% confidence brightness upper limit if the W4 flux measurement has SNR<2
        # 'w1mpro',
        # 'w1sigmpro',  # W1 profile-fit photometric measurement uncertainty in mag units
        # 'w1snr',  # W1 profile-fit measurement signal-to-noise ratio
        # 'w1rchi2',  # Reduced χ2 of the W1 profile-fit photometry
        # # W2 magnitude measured with profile-fitting photometry, or the magnitude of the
        # # 95% confidence brightness upper limit if the W4 flux measurement has SNR<2
        # 'w2mpro',
        # 'w2sigmpro',  # W2 profile-fit photometric measurement uncertainty in mag units
        # 'w2snr',  # W2 profile-fit measurement signal-to-noise ratio
        # 'w2rchi2',  # Reduced χ2 of the W2 profile-fit photometry
        # # W3 magnitude measured with profile-fitting photometry, or the magnitude of the
        # # 95% confidence brightness upper limit if the W4 flux measurement has SNR<2
        # 'w3mpro',
        # 'w3sigmpro',  # W3 profile-fit photometric measurement uncertainty in mag units
        # 'w3snr',  # W3 profile-fit measurement signal-to-noise ratio
        # 'w3rchi2',  # Reduced χ2 of the W3 profile-fit photometry
        # # W4 magnitude measured with profile-fitting photometry, or the magnitude of the
        # # 95% confidence brightness upper limit if the W4 flux measurement has SNR<2
        # 'w4mpro',
        # 'w4sigmpro',  # W4 profile-fit photometric measurement uncertainty in mag units
        # 'w4snr',  # W4 profile-fit measurement signal-to-noise ratio
        # 'w4rchi2',  # Reduced χ2 of the W4 profile-fit photometry
        # 'nb',  # Number of PSF components used simultaneously in profile-fitting the src
        # 'na',  # Active deblending flag.
        # 'pmra',  # The apparent (not proper!) motion in RA estimated for source
        # 'sigpmra',  # Uncertainty in the RA motion estimation.
        # 'pmdec',  # The apparent (not proper!) motion in declination estimated for src
        # 'sigpmdec',  # Uncertainty in the Dec motion estimated for this source
        # 'ext_flg',  # Extended source flag
        # 'var_flg',  # Variability flag
        # # Unique ID of closest source in 2MASS Point Source Catalog (PSC)
        # # that falls within 3" of the non-motion fit position
        # 'tmass_key',
        # 'r_2mass',  # Distance between WISE source and associated 2MASS PSC source
        # 'n_2mass',  # num 2MASS PSC entries within a 3" radius of the WISE src position
        # 'j_m_2mass',  # 2MASS J-band magnitude or magnitude upper limit
        # 'j_msig_2mass',  # 2MASS J-band corrected photometric uncertainty
        # 'h_m_2mass',  # 2MASS H-band magnitude or magnitude upper limit
        # 'h_msig_2mass',  # 2MASS H-band corrected photometric uncertainty
        # 'k_m_2mass',  # 2MASS K_s-band magnitude or magnitude upper limit
        # 'k_msig_2mass',  # 2MASS K_s-band corrected photometric uncertainty
    ]


def _create_job_config(alert_dict):
    """Return the BigQuery `job_config` for the cross match with AllWISE.

    The `job_config` contains the query parameters for the SQL statement that is
    returned by `_create_sql_stmnt()`.
    """
    # declare the parameters
    max_sep = 5  # arcsec, max separation to declare a match
    limit = 3  # max number of matches to return (ordered by separation distance)
    # alert source position
    source = schema_map["source"]
    ra, dec = alert_dict[source]['ra'], alert_dict[source]['dec']
    if ra > 180.0:
        ra = ra - 360.0
    # Polygon that bounds the ra/dec. Restricts the BigQuery search region.
    arcsec_per_deg = 3600
    pad = max_sep / arcsec_per_deg
    polygon = (
        "Polygon(("
        f"{ra-pad} {dec-pad},"
        f"{ra-pad} {dec+pad},"
        f"{ra+pad} {dec+pad},"
        f"{ra+pad} {dec-pad},"
        f"{ra-pad} {dec-pad}"
        "))"
    )

    # create and return the job_config
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("ra", "FLOAT64", ra),
            bigquery.ScalarQueryParameter("dec", "FLOAT64", dec),
            bigquery.ScalarQueryParameter("max_sep", "FLOAT64", max_sep),
            bigquery.ScalarQueryParameter("polygon", "STRING", polygon),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ]
    )
    return job_config


def _store_bigquery(wise_dict, attrs):
    """Store the cross match results in BigQuery."""
    # if there is no match, skip bq storage
    # if len(wise_dict) == 0:
    #     return

    # create dict to upload to bigquery
    store_dict = dict(attrs)
    # don't store everything. store just enough to re-query the AllWISE catalog.
    keep_allwise_cols = ['designation', 'cntr', 'source_id']
    for allwiseN, wdict in wise_dict.items():
        store_dict.update(
            {f'{allwiseN}_{k}': v for k, v in wdict.items() if k in keep_allwise_cols}
        )
    # store to bigquery
    gcp_utils.insert_rows_bigquery(bq_table, [store_dict])


def _query_bigquery(
    query: str,
    project_id: Optional[str] = None,
    job_config: Optional[bigquery.job.QueryJobConfig] = None,
):
    """Query BigQuery.

    REPRODUCED FROM `broker_utils` FOR TESTING PURPOSES.

    Example query:
        ``
        query = (
            f'SELECT * '
            f'FROM `{project_id}.{dataset}.{table}` '
            f'WHERE objectId={objectId} '
        )
        ``

    Example of working with the query_job:
        ``
        for r, row in enumerate(query_job):
            # row values can be accessed by field name or index
            print(f"objectId={row[0]}, candid={row['candid']}")
        ``
    """
    bq_client = bigquery.Client()
    query_job = bq_client.query(query, job_config=job_config)

    return query_job


if __name__ == "__main__":
    PORT = int(os.getenv("PORT")) if os.getenv("PORT") else 8080

    # This is used when running locally. Gunicorn is used to run the
    # application on Cloud Run. See entrypoint in Dockerfile.
    app.run(host="127.0.0.1", port=PORT, debug=True)
