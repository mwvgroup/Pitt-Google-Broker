#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
from google.cloud import bigquery
import datetime
from datetime import timedelta, timezone


BILLING_PROJECT_ID = "light-cycle-328823"
BILLING_TABLE = (
    f"{BILLING_PROJECT_ID}.billing.gcp_billing_export_resource_v1_0102E2_E3A6BA_C2AFD5"
)

PROD_PROJECT_ID = "ardent-cycling-243415"
METADATA_TABLE = f"{PROD_PROJECT_ID}.ztf_alerts.metadata"
ALERTS_TABLE = f"{PROD_PROJECT_ID}.ztf_alerts.alerts"
DIA_TABLE = f"{PROD_PROJECT_ID}.ztf_alerts.DIASource"


def _datetime_to_date(dtime):
    y, m, d = dtime.strftime("%Y-%m-%d").split("-")
    return datetime.date(int(y), int(m), int(d))


# def _date_to_datetime(date):
#     return datetime.datetime(date)


# ALERT QUERIES
def count_alerts_by_date(lookback=None, date="today"):
    """Use UTC for everything."""
    query_params = []
    timecol = "candidate.jd"
    # timecol = "jd"

    select = """
        SELECT
            COUNT(candid) AS num_alerts
    """

    frm = f"FROM `{ALERTS_TABLE}`"
    # frm = f"FROM `{DIA_TABLE}`"

    # WHERE
    t0 = 2459496.50000
    t1 = 2459497.50000
    where = f"WHERE {timecol} BETWEEN @t0 AND @t1"
    query_params.append(bigquery.ScalarQueryParameter("t0", "FLOAT", t0))
    query_params.append(bigquery.ScalarQueryParameter("t1", "FLOAT", t1))

    query = f"{select} {frm} {where}"
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    return (query, job_config)


def count_metadata_by_date(lookback=None, date="today"):
    """Use UTC for everything."""
    query_params = []
    # timecol = "kafka_timestamp__alerts"
    timecol = "publish_time__alerts"

    select = f"""
        SELECT
            CAST({timecol} AS DATE) AS date,
            COUNT(candid) AS num_alerts
    """

    frm = f"FROM `{METADATA_TABLE}`"

    # WHERE
    now = datetime.datetime.now(timezone.utc)
    replace = {"hour": 0, "minute": 0, "second": 0, "microsecond": 0}
    if lookback is not None:
        t0 = (now - timedelta(days=lookback)).replace(**replace)
        where = f"WHERE {timecol} >= @t0"
        query_params.append(bigquery.ScalarQueryParameter("t0", "TIMESTAMP", t0))
    elif date == "today":
        t0 = now.replace(**replace)
        where = f"WHERE {timecol} >= @t0"
        query_params.append(bigquery.ScalarQueryParameter("t0", "TIMESTAMP", t0))
    else:
        t0 = datetime.datetime.strptime(f"{date}-+0000", "%Y-%m-%d-%z")
        t1 = t0 + timedelta(days=1)
        where = f"WHERE {timecol} BETWEEN @t0 AND @t1"
        query_params.append(bigquery.ScalarQueryParameter("t0", "TIMESTAMP", t0))
        query_params.append(bigquery.ScalarQueryParameter("t1", "TIMESTAMP", t1))
    # where = f"{where} AND publish_time__alerts IS NOT NULL"

    groupby = f"GROUP BY CAST({timecol} AS DATE)"

    query = f"{select} {frm} {where} {groupby}"
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    return (query, job_config)


# BILLING QUERIES
def where_date(lookback=None, date="today"):
    query_params = []

    select = """
        SELECT
          service.description AS service,
          resource.name AS resource,
          sku.description AS sku,
          project.id AS project_id,
          cost,
          usage.amount AS usage_amount,
          usage.unit AS usage_unit,
          usage_start_time,
          usage_end_time
    """

    frm = f"FROM `{BILLING_TABLE}`"

    # WHERE
    # timecol = "DATE(_PARTITIONTIME)"
    timecol = "DATE(usage_start_time)"
    now = _datetime_to_date(datetime.datetime.now(timezone.utc))
    if lookback is not None:
        where = f"WHERE {timecol} > @date"
        query_params.append(bigquery.ScalarQueryParameter("date", "DATE", now))
    elif date == "today":
        where = f"WHERE {timecol} = @date"
        query_params.append(bigquery.ScalarQueryParameter("date", "DATE", now))
    else:
        y, m, d = date.split("-")
        t0 = datetime.date(int(y), int(m), int(d))
        where = f"WHERE {timecol} = @date"
        query_params.append(bigquery.ScalarQueryParameter("date", "DATE", t0))
        # t0 = datetime.datetime.strptime(f"{date}-+0000", "%Y-%m-%d-%z")
        # t1 = t0 + timedelta(days=1)
        # where = f"WHERE {timecol} BETWEEN @t0 AND @t1"
        # query_params.append(bigquery.ScalarQueryParameter("t0", "DATE", t0))
        # query_params.append(bigquery.ScalarQueryParameter("t1", "DATE", t1))

    query = f"{select} {frm} {where}"
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    return (query, job_config)


def resource_name_not_null():
    return f"""
        SELECT
          service.description AS service_description,
          resource.name AS resource_name,
          sku.description AS sku_description,
          project.id AS project_id,
          cost,
        FROM
          `{BILLING_TABLE}`
        WHERE
          resource.name IS NOT NULL
    """
