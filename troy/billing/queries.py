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
PROD_TABLE = f"{PROD_PROJECT_ID}.ztf_alerts.metadata"


def _datetime_to_date(dtime):
    y, m, d = dtime.strftime("%Y-%m-%d").split("-")
    return datetime.date(int(y), int(m), int(d))


# def _date_to_datetime(date):
#     return datetime.datetime(date)

# query = f"""
#     SELECT kafka_timestamp__alerts, publish_time__alerts, candid
#     FROM `{PROD_TABLE}`
#     WHERE kafka_topic__alerts = 'ztf_20211015_programid1'
# """
#     # WHERE kafka_timestamp__alerts BETWEEN @t0 AND @t1
# df = gcp_utils.query_bigquery(query, job_config=job_config).to_dataframe()
# dup = df.loc[df.duplicated(subset='candid', keep=False)]
# for i, cid in enumerate(dup.candid.unique()):
#     prv = None
#     for index, row in dup.loc[dup['candid']==cid].iterrows():
#         if prv is None: prv = row.publish_time__alerts
#         if not prv == row.publish_time__alerts:
#             print(index)
#             print(dup.loc[dup['candid']==cid])
#             break


# ALERT QUERIES
def count_alerts_by_date(lookback=30, date="today"):
    query_params = []

    select = """
        SELECT
            CAST(kafka_timestamp__alerts AS DATE) AS date,
            COUNT(candid) AS num_alerts
    """

    frm = f"FROM `{PROD_TABLE}`"

    # WHERE
    now = datetime.datetime.now(timezone.utc)
    replace = {"hour": 0, "minute": 0, "second": 0, "microsecond": 0}
    if lookback is not None:
        t0 = (now - timedelta(days=lookback)).replace(**replace)
        where = "WHERE kafka_timestamp__alerts >= @t0"
        query_params.append(bigquery.ScalarQueryParameter("t0", "TIMESTAMP", t0))
    elif date == "today":
        t0 = now.replace(**replace)
        where = "WHERE kafka_timestamp__alerts >= @t0"
        query_params.append(bigquery.ScalarQueryParameter("t0", "TIMESTAMP", t0))
    else:
        t0 = datetime.datetime.strptime(f"{date}-+0000", "%Y-%m-%d-%z")
        t1 = t0 + timedelta(days=1)
        where = "WHERE kafka_timestamp__alerts BETWEEN @t0 AND @t1"
        query_params.append(bigquery.ScalarQueryParameter("t0", "TIMESTAMP", t0))
        query_params.append(bigquery.ScalarQueryParameter("t1", "TIMESTAMP", t1))
    # where = f"{where} AND publish_time__alerts IS NOT NULL"

    groupby = "GROUP BY CAST(kafka_timestamp__alerts AS DATE)"

    query = f"{select} {frm} {where} {groupby}"
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    return (query, job_config)


# BILLING QUERIES
def where_date(lookback=30, date="today"):
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
    now = datetime.datetime.now(timezone.utc)
    if lookback is not None:
        where = "WHERE DATE(_PARTITIONTIME) BETWEEN @date1 AND @date2"
        query_params.append(
            bigquery.ScalarQueryParameter(
                "date1", "DATE", _datetime_to_date(now - timedelta(days=lookback))
            )
        )
        query_params.append(
            bigquery.ScalarQueryParameter("date2", "DATE", _datetime_to_date(now))
        )
    elif date == "today":
        where = "WHERE DATE(_PARTITIONTIME) = @date"
        query_params.append(
            bigquery.ScalarQueryParameter("date", "DATE", _datetime_to_date(now))
        )

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
