#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""``bigquery`` contains functions that facilitate querying
Pitt-Google Broker's BigQuery databases and reading the results.
"""

from google.cloud import bigquery
from tabulate import tabulate
from typing import Tuple, List, Optional, Union
import numpy as np
import pandas as pd
from pandas import DataFrame
from astropy.time import Time
import matplotlib.axes as mpl_axes
from matplotlib import pyplot as plt

bq_client = bigquery.Client()

pgb_project_id = 'ardent-cycling-243415'
bq_tables = {
    'ztf_alert_data': f'{pgb_project_id}:ztf_alerts.alerts',
    'ztf_salt2': f'{pgb_project_id}:ztf_alerts.salt2',
}
metacols = ['objectId',]
flatcols = ['schemavsn','publisher','candid',]

def lightcurve_sql_query(columns: List[str], objectIds: Optional[list] = None) -> str:
    """Convience function that generates the SQL string needed to
    query the alerts table and aggregate lightcurve data.
    When the resulting SQL query is executed, the query job will contain
    one row for each objectId, with the lightcurve data aggregated into
    arrays (one array per column in columns) ordered by the observation date.

    Note: Arrays may contain duplicated observations; it is the user's
    responsiblity to clean them.

    Args:
        columns: Names of columns to select from the alerts table.
                 The 'objectId' and 'candid' columns are automatically included
                 and do not need to be in this list.
        objectIds: IDs of ZTF objects to include in the query.

    Returns:
        query: SQL statement to query the alerts table and aggregate data by objectId.
    """
    dataset = 'ztf_alerts'
    table = 'alerts'
    # make sure 'candid' is in columns. 'objectId' will be handled later.
    columns = list(set(columns).union(set(['candid'])))

    # SELECT statement
    # create a list of strings that will aggregate columns into arrays
    aggcols = _list_aggcols_sql_statements(columns)
    selects = f'SELECT {", ".join(metacols + aggcols)}'

    # FROM statement
    froms = f'FROM `{pgb_project_id}.{dataset}.{table}`'

    # WHERE statement
    if objectIds is not None:
        # wrap each objectId in quotes and join to single string
        oids = ','.join([f'"{o}"' for o in objectIds])
        wheres = f'WHERE objectId IN ({oids})'
    else:
        wheres = ''

    # GROUP BY statement
    groupbys = f'GROUP BY objectId'

    # concat the statements into a SQL query statement
    sqlquery = ' '.join([selects, froms, wheres, groupbys])

    return sqlquery

def _list_aggcols_sql_statements(columns: List[str]) -> List[str]:
    """Create a list of SQL string query segments that will aggregate
    all columns not in metacols.
    """
    # list of requested flatcols
    fcols = list(set(columns) & set(flatcols))
    # list of requested columns nested under 'candidate'
    ncols = list(set(columns) - set(metacols) - set(flatcols))
    ncols = [f'candidate.{c}' for c in ncols]
    # complete list of columns to be aggregated (group by) objectId
    aggcols = fcols + ncols
    # attach the ARRAY_AGG, ORDER By, and AS statements to the aggcols
    aggcols = [f'ARRAY_AGG({c} ORDER BY candidate.jd) AS {c.split(".")[-1]}' for c in aggcols]

    return aggcols

#--- Query a BigQuery database table

def query_db(query: Union[str,dict], dry_run: bool = False):
    """
    """

    return

def dry_run(query: str):
    """Perform a dry run to find out how many bytes the query will process.
    Args:
        query: SQL query statement
    """
    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    query_job = bq_client.query(query, job_config=job_config)

    nbytes, TB = query_job.total_bytes_processed, 1e12
    print(f'\nQuery statement:')
    print(f'\n"{query}"\n')
    print(f'will process {nbytes} bytes of data.')
    print(f'({nbytes/TB*100:.3}% of your 1 TB free monthly allotment.)')

#---

#--- Format query results
def format_lightcurve_query_results(query_job: Optional[bigquery.job.QueryJob] = None, row: Optional[bigquery.table.Row] = None, format: str = 'pandas') -> Union[DataFrame,str]:
    """Converts the results of a BigQuery query to the desired format.
    Must pass either query_job or row.
    Any duplicate observations will be dropped.

    Args:
        query_job: Results from a lightcurve query job. SQL statement needed
                   to create the job can be obtained with lightcurve_sql_query().
                    Must supply either query_job or row.

        row: A single row from query_job. Must supply either row or query_job.

        format: One of 'pandas' or 'json'. Input lightcurves will be returned
                in this format.

    Returns:
        lightcurves: Input lightcurves converted to requested format
    """
    # make sure we have an appropriate param combination
    do_job, do_row = query_job is not None, row is not None
    good_format = format in ['pandas','json']
    good_combo = (do_job != do_row) and good_format
    if not good_combo:
        raise ValueError('Must pass one of query_job or row.')

    # convert query_job
    if do_job:
        lightcurves = _format_lightcurve_query_results_to_df(query_job)  # df
        if format == 'json':
            lightcurves = lightcurves.reset_index().to_json()  # str

    # convert row to df
    if do_row:
        lightcurves = _format_lightcurve_row_to_df(row)  # df
        if format == 'json':
            lightcurves['objectId'] = lightcurves.objectId  # persist metadata
            lightcurves = lightcurves.reset_index().to_json()  # str

    return lightcurves


def _format_lightcurve_query_results_to_df(query_job: bigquery.job.QueryJob):
    """Convert a query_job (containing multiple rows of object lightcurves)
    to a DataFrame.
    Any duplicate observations will be dropped.
    """
    dflist = []
    for r, row in enumerate(query_job):
        # convert to DataFrame
        df = _format_lightcurve_row_to_df(row)
        # add the objectId so we can use it to multi-index
        df['objectId'] = df.objectId
        # set the multi-index and append to the list
        dflist.append(df.reset_index().set_index(['objectId','candid']))

    lightcurves = pd.concat(dflist)

    return lightcurves


def _format_lightcurve_row_to_df(row: Union[dict,bigquery.table.Row]):
    """Convert a single object's lightcurve from a query row to a DataFrame.
    Any duplicate observations will be dropped.
    """
    d = dict(row.items())
    oid, cid = d.pop('objectId'), d.pop('candid')
    df = pd.DataFrame(data=d, index=pd.Index(cid, name='candid'))
    df.drop_duplicates(inplace=True)
    df.objectId = oid
    return df

#---

#--- Plot query results

def plot_lightcurve(dflc: DataFrame, ax: Optional[mpl_axes.Axes]=None, days_ago: bool=True):
    """Plot the lighcurve (per band) of a single ZTF object. Adapted from:
    https://github.com/ZwickyTransientFacility/ztf-avro-alert/blob/master/notebooks/Filtering_alerts.ipynb
    """

    filter_code = {1:'g', 2:'R', 3:'i'}
    filter_color = {1:'green', 2:'red', 3:'pink'}

    # set the x-axis (time) details
    if days_ago:
        now = Time.now().jd
        t = dflc.jd - now
        xlabel = 'Days Ago'
    else:
        t = dflc.jd
        xlabel = 'Time (JD)'

    if ax is None:
        plt.figure()

    # plot lightcurves by band
    for fid, color in filter_color.items():
        # plot detections in this filter:
        w = (dflc.fid == fid) & ~dflc.magpsf.isnull()
        if np.sum(w):
            label = f'{fid}: {filter_code[fid]}'
            kwargs = {'fmt':'.', 'color':color, 'label':label}
            plt.errorbar(t[w],dflc.loc[w,'magpsf'], dflc.loc[w,'sigmapsf'], **kwargs)
        # plot nondetections in this filter
        wnodet = (dflc.fid == fid) & dflc.magpsf.isnull()
        if np.sum(wnodet):
            plt.scatter(t[wnodet],dflc.loc[wnodet,'diffmaglim'], marker='v',color=color,alpha=0.25)

    plt.gca().invert_yaxis()
    plt.xlabel(xlabel)
    plt.ylabel('Magnitude')
    plt.legend()
    plt.title(f'objectId: {dflc.objectId}')

#---

#--- Get information about PGB datasets and tables

def get_table_info(table: Union[str,list] = 'all', dataset: str ='ztf_alerts'):
    """Retrieves and prints BigQuery table schemas.
    Args:
        table: Name of the BigQuery table, or list of the same.
               'all' will print the info for all tables in the dataset.
        dataset: Name of BigQuery dataset that the table(s) belong to.
    """

    # get the table names in a list
    if table == 'all':
        tables = get_dataset_table_names(dataset=dataset)
    elif type(table) == str:
        tables = [table]
    else:
        tables = table

    # get and print info about each table
    for t in tables:
        print(f'\nTable: {pgb_project_id}.{dataset}.{t}')
        df = get_table_columns(table=t)
        print(tabulate(df, headers='keys', tablefmt='psql'))

def get_table_columns(table: str, dataset: str ='ztf_alerts') -> DataFrame:
    """Retrieves information about the columns in a BigQuery table and returns
    it as a DataFrame.

    Args:
        table: Name of the BigQuery table
        dataset: Name of BigQuery dataset that the table(s) belong to.
    Returns
        df: Column information from the BigQuery table schema.
    """
    bqtable = bq_client.get_table(f'{pgb_project_id}.{dataset}.{table}')
    cols = [(s.name, s.description, s.field_type, s.mode) for s in bqtable.schema]
    colnames = ['column_name', 'description', 'type', 'mode']
    df = DataFrame(cols, columns=colnames)

    return df

def get_dataset_table_names(dataset: str ='ztf_alerts') -> List[str]:
    """
    Args:
        dataset: Name of the BigQuery dataset.

    Returns:
        tables: List of table names in the dataset.
    """

    query = (
        'SELECT * '
        f'FROM {pgb_project_id}.{dataset}.INFORMATION_SCHEMA.TABLES'
    )
    query_job = bq_client.query(query)
    tables = [row['table_name'] for row in query_job]
    return tables

#---
