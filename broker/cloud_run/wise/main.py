#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Cross match alerts with the AllWISE catalog in BigQuery's public datasets.

https://wise2.ipac.caltech.edu/docs/release/allwise/
"""

import base64
from flask import Flask, request
from google.cloud import logging, bigquery
import json
import os

from broker_utils import gcp_utils, schema_maps


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
ps_topic = f"{SURVEY}-alerts"
if TESTID != "False":  # attach the testid to the names
    bq_dataset = f"{bq_dataset}_{TESTID}"
    ps_topic = f"{ps_topic}-{TESTID}"
bq_table = f"{bq_dataset}.xmatch"

schema_map = schema_maps.load_schema_map(SURVEY, TESTID)


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
    alert_dict = json.loads(base64.b64decode(msg["data"]).decode("utf-8"))
    attrs = {
        schema_map["objectId"]: str(alert_dict[schema_map["objectId"]]),
        schema_map["sourceId"]: str(alert_dict[schema_map["sourceId"]]),
    }

    # do the cross match
    wise_dict = _xmatch_wise(alert_dict)

    # announce and store results
    gcp_utils.publish_pubsub(
        ps_topic, {"alert": alert_dict, "AllWISE": wise_dict}, attrs=attrs
    )
    gcp_utils.insert_rows_bigquery(bq_table, [wise_dict])

    return ("", 204)


def _xmatch_wise(alert_dict):
    sql_stmnt = _get_sql_stmnt()
    job_config = _get_job_config(alert_dict)
    query_job = gcp_utils.query_bigquery(sql_stmnt, job_config=job_config)

    results = {}
    for r, row in enumerate(query_job):
        results[f'match{r}'] = dict(row)

    return results


def _get_sql_stmnt():
    """Return the parameterized SQL statement that cross matches the alert to AllWISE.

    The query takes the following parameters:
        @ra: Alert source right ascension in degrees, transformed to [-180, 180] deg.
        @dec: Alert source declination in degrees.
        @max_sep: Maximum separation in arcsec to declare an AllWISE source is a match.
        @polygon: String representing a Polygon geography; restricts the region of space
                  within which BigQuery should search for matches.
        @limit: Maximum number of matches to return (ordered by separation distance).
    """
    # Note: ST_DISTANCE() returns the distance (meters) on a sphere with Earth's radius.
    # 30.8874796235 = meters/arcsec on that sphere.
    sql_stmnt = """
        CREATE TEMP FUNCTION
            ArcSecondDistance(p1 GEOGRAPHY, p2 GEOGRAPHY, max_sep_arcsec FLOAT64)
                AS (ST_DISTANCE(p1, p2) < max_sep_arcsec * 30.8874796235);
        SELECT source_id, ra, dec, point
        FROM `bigquery-public-data.wise_all_sky_data_release.all_wise`
        WHERE
            ArcSecondDistance(point, ST_GEOGPOINT(@ra, @dec), @max_sep)
            AND ST_CONTAINS(ST_GEOGFROMTEXT(@polygon), point)
        ORDER BY ST_DISTANCE(point, ST_GEOGPOINT(@ra, @dec))
        LIMIT @limit;
    """

    return sql_stmnt


def _get_job_config(alert_dict):
    """Return the BigQuery `job_config` for the cross match with AllWISE.

    The `job_config` contains the query parameters for the SQL statement that is
    returned by `_get_sql_stmnt()`.
    """
    # declare the parameters
    max_sep = 5  # arcsec, max separation to declare a match
    limit = 3  # max number of matches to return (ordered by separation distance)
    # alert source position
    ra, dec = alert_dict['candidate']['ra'], alert_dict['candidate']['dec']
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
            bigquery.ScalarQueryParameter("limit", "INT", limit),
        ]
    )
    return job_config


if __name__ == "__main__":
    PORT = int(os.getenv("PORT")) if os.getenv("PORT") else 8080

    # This is used when running locally. Gunicorn is used to run the
    # application on Cloud Run. See entrypoint in Dockerfile.
    app.run(host="127.0.0.1", port=PORT, debug=True)
