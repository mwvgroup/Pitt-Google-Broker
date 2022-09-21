#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import datetime
from datetime import timedelta, timezone
from google.cloud import bigquery
import pandas as pd

from custom_classes import loaded_data
import transforms

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


def load_countdf_litebilldf_from_file(f='billing_20211203.csv') -> loaded_data:
    """Load pre-queried billing data that has been saved to file."""
    # load billdf
    billdf = pd.read_csv(f)
    billdf['usage_date'] = pd.to_datetime(billdf.usage_date, format='%Y-%m-%d').dt.date

    # create a lightened billdf containing only what we want to look at
    lite_df_cols = ['project_id', 'service', 'sku', 'cost', 'usage_date']
    litebilldf = billdf.loc[:, lite_df_cols]
    # get indexes where the sku is a live pipeline sku
    litebill_ispipelinesku = (litebilldf.apply(transforms.is_pipeline_sku, axis=1))

    # load alert counts per day
    f = "alert_counts_20211203.csv"
    countdf1 = pd.read_csv(f)
    f = "alert_counts_fill_missing_20211203.csv"
    countdf2 = pd.read_csv(f, comment="#")
    countdf = pd.concat([countdf1, countdf2])
    countdf['publish_date'] = pd.to_datetime(countdf.publish_date, format='%Y-%m-%d').dt.date
    countdf = countdf.set_index('publish_date').sort_index()

    return loaded_data(countdf, litebilldf, litebill_ispipelinesku)


# ALERT QUERIES
def count_alerts_by_date(lookback=None, date="today"):
    """Use UTC for everything."""
    query_params = []
    timecol = "candidate.jd"
    # timecol = "jd"

    select = "SELECT COUNT(candid) AS num_alerts"

    frm = f"FROM `{ALERTS_TABLE}`"
    # frm = f"FROM `{DIA_TABLE}`"

    # WHERE
    # t0 = 2459496.50000
    # t1 = 2459497.50000
    where = f"WHERE {timecol} BETWEEN @t0 AND @t1"
    query_params.append(bigquery.ScalarQueryParameter("t0", "FLOAT", t0))
    query_params.append(bigquery.ScalarQueryParameter("t1", "FLOAT", t1))

    query = f"{select} {frm} {where}"
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    return (query, job_config)


# def count_alerts_by_kafka_topic(lookback=None, date="today"):
#     query_params = []
#     timecol = "candidate.jd"
#     # timecol = "jd"
#
#     select = "SELECT COUNT(candid) AS num_alerts"
#
#     frm = f"FROM `{ALERTS_TABLE}`"
#     # frm = f"FROM `{DIA_TABLE}`"
#
#     # WHERE
#     # t0 = 2459496.50000
#     # t1 = 2459497.50000
#     where = f"WHERE {timecol} BETWEEN @t0 AND @t1"
#     query_params.append(bigquery.ScalarQueryParameter("t0", "FLOAT", t0))
#     query_params.append(bigquery.ScalarQueryParameter("t1", "FLOAT", t1))
#
#     query = f"{select} {frm} {where}"
#     job_config = bigquery.QueryJobConfig(query_parameters=query_params)
#     return (query, job_config)

def _where_datetime(timecol, query_params, lookback=None, date="2021-10-09"):
    if lookback is not None:
        today_0000 = datetime.datetime.combine(
            datetime.date.today(), datetime.time(), timezone.utc
        )
        t0 = today_0000 - timedelta(days=lookback)
        t1 = today_0000 + timedelta(days=1)

    elif date is not None:
        t0 = datetime.datetime.strptime(f"{date}-+0000", "%Y-%m-%d-%z")
        t1 = t0 + timedelta(days=2)

    where = f"WHERE {timecol} BETWEEN @t0 AND @t1"
    query_params.append(bigquery.ScalarQueryParameter("t0", "TIMESTAMP", t0))
    query_params.append(bigquery.ScalarQueryParameter("t1", "TIMESTAMP", t1))

    return where, query_params


def count_metadata_by_date(lookback=None, date="2021-10-09"):
    """Use UTC for everything."""
    query_params = []
    # timecol = "kafka_timestamp__alerts"
    timecol = "publish_time__alerts"

    select = f"""
        SELECT
            DATE({timecol}) AS publish_date,
            COUNT(candid) AS num_alerts
    """

    frm = f"FROM `{METADATA_TABLE}`"

    # WHERE
    if lookback is not None:
        where, query_params = _where_datetime(timecol, query_params, lookback=lookback)
    elif date is not None:
        where, query_params = _where_datetime(timecol, query_params, date=date)
    # where = f"{where} AND publish_time__alerts IS NOT NULL"

    groupby = "GROUP BY publish_date"

    query = f"{select} {frm} {where} {groupby}"
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    return (query, job_config)


# BILLING QUERIES
def billing(lookback=None, date="today"):
    query_params = []

    select = """
        SELECT
            project.id AS project_id,
            service.description AS service,
            resource.name AS resource,
            sku.description AS sku,
            location.location AS location,
            cost,
            usage.amount AS usage_amount,
            usage.unit AS usage_unit,
            DATE(usage_start_time) as usage_date,
            usage_start_time,
            usage_end_time
    """

    frm = f"FROM `{BILLING_TABLE}`"

    # WHERE
    # timecol = "DATE(_PARTITIONTIME)"
    timecol = "usage_start_time"
    if lookback is not None:
        where, query_params = _where_datetime(timecol, query_params, lookback=lookback)
    elif date is not None:
        where, query_params = _where_datetime(timecol, query_params, date=date)

    # now = _datetime_to_date(datetime.datetime.now(timezone.utc))
    # if lookback is not None:
    #     where = f"WHERE {timecol} > @date"
    #     t0 = now - timedelta(days=lookback)
    #     query_params.append(bigquery.ScalarQueryParameter("date", "DATE", t0))
    # elif date == "today":
    #     where = f"WHERE {timecol} = @date"
    #     query_params.append(bigquery.ScalarQueryParameter("date", "DATE", now))
    # else:
    #     y, m, d = date.split("-")
    #     t0 = datetime.date(int(y), int(m), int(d))
    #     where = f"WHERE {timecol} = @date"
    #     query_params.append(bigquery.ScalarQueryParameter("date", "DATE", t0))
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
