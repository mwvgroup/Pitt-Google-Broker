#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""``bigquery`` contains functions that facilitate querying
Pitt-Google Broker's BigQuery databases and reading the results.
"""

from astropy.time import Time
from google.cloud import bigquery
import matplotlib as mpl
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from tabulate import tabulate
from typing import List, Optional, Union, Iterator


pgb_project_id = 'ardent-cycling-243415'
pgb_bq_client = bigquery.Client(project=pgb_project_id)
# use this to get project level info like table schemas
# actual queries will use `user_bq_client`, instantiated below
bq_tables = {
    'ztf_alert_data': f'{pgb_project_id}:ztf_alerts.alerts',
    'ztf_salt2': f'{pgb_project_id}:ztf_alerts.salt2',
}
metacols = ['objectId',]
flatcols = ['schemavsn','publisher','candid',]

#--- BigQuery Client
user_bq_client, user_project_id = None, None
def create_client(project_id: str):
    """Open a BigQuery Client.

    Args:
        project_id: User's Google Cloud Platform project ID
    """
    global user_bq_client
    global user_project_id

    # make sure we have a non-empty project_id
    assert len(project_id)>0, 'You must pass a valid project_id to open a client.'
    user_project_id = project_id

    # instantiate the client
    print(f'\nInstantiating a BigQuery client with project_id: {user_project_id}\n')
    user_bq_client = bigquery.Client(project=user_project_id)

def _check_client():
    msg = ("You must create a BigQuery client first. "
           "Run `pgb.bigquery.create_client('your_project_id')`")
    assert isinstance(user_bq_client, bigquery.client.Client), msg

def _create_client_if_needed():
    stop = False  # will be set to True if the user chooses to exit

    try:
        _check_client()

    except AssertionError:
        # help the user open a bigquery client
        msg = ('\nTo run queries, you must first open a BigQuery Client.\n'
               'This can be done directly using `pgb.bigquery.create_client(project_id)`\n'
               '\tTo run this command now, enter your Google Cloud Platform project ID.\n'
               '\tTo exit, simply press "Enter".\n'
               '\nProject ID: '
        )
        project_id = input(msg) or ''

        if project_id == '':
            stop = True  # user wants to exit rather than creating a client
        else:
            create_client(project_id)

    return stop



#--- Query for object histories
def query_objects(columns: List[str], objectIds: Optional[list] = None, format: str = 'pandas', iterator: bool = False) -> Union[str,pd.DataFrame,bigquery.job.QueryJob,Iterator[Union[str,pd.DataFrame]]]:
    """Query the alerts database for object histories.

    Args:
        columns: Names of columns to select from the alerts table.
                 The 'objectId' and 'candid' columns are automatically included
                 and do not need to be in this list.
        objectIds: IDs of ZTF objects to include in the query.
        format: One of 'pandas', 'json', or 'query_job'. Query results will be
                returned in this format. Results returned as 'query_job' may
                contain duplicate observations; else duplicates are dropped.
        iterator: If True, iterate over the objects and return one at a time.
                  Else return the full query results together.
                  This parameter is ignored if `format` == 'query_job'.

    Returns: Query results in the requested format. If `iterator` is True,
             yields one object at a time; else all results are returned together.
    """
    # if a bigquery client does not exist, help the user instantiate one
    stop = _create_client_if_needed()
    if stop:  # the user has chosen to exit rather than create a client
        return

    # generate the SQL statement to query alerts db and aggregate histories
    query = object_history_sql_statement(columns, objectIds)  # str

    # print dry run results; proceed if the user confirms, else return
    do_the_query = _dry_run_and_confirm(query)
    if not do_the_query:
        return

    # make the API call
    query_job = user_bq_client.query(query)

    # return the results
    if format == 'query_job':
        return query_job
    elif iterator:  # return a generator that cycles through the objects/rows
        # return (i for i in iterate_query_objects(query_job, format))
        return (format_history_query_results(row=row, format=format) for row in query_job)
    else:  # format and return all rows at once
        return format_history_query_results(query_job=query_job, format=format)

# def iterate_query_objects(query_job: bigquery.job.QueryJob, format: str = 'pandas') -> Union[str,pd.DataFrame]:
#     """Iterates through the rows of query_job and returns them in the requested format.
#     Args:
#         query_job: Results of a query on object histories.
#         format: One of 'pandas', or 'json'. Query results will be
#                 returned in this format.
#     """
#     # while i < query_job.result().total_rows:
#     #     pass
#     # for r, row in enumerate(query_job):
#     #     yield format_history_query_results(row=row, format=format)
#     return [format_history_query_results(row=row, format=format) for row in query_job]

def dry_run(query: str):
    """Perform a dry run to find out how many bytes the query will process.
    Args:
        query: SQL query statement
    """
    _check_client()  # make sure we have a bigquery.client
    global user_project_id

    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    query_job = user_bq_client.query(query, job_config=job_config)

    nbytes, TB = query_job.total_bytes_processed, 1e12
    pTB = nbytes/TB*100  # nbytes as a percent of 1 TB
    print(f'\nQuery statement:')
    print(f'\n"{query}"\n')
    print(f'will process {nbytes} bytes of data.')
    print(f'({pTB:.3}% of your 1 TB free monthly allotment.)')

def _dry_run_and_confirm(query: str) -> bool:
    # print dry run info
    dry_run(query)
    # ask user if they want to proceed
    cont = input('Continue? [y/N]: ') or 'N'
    do_the_query = cont in ['y','Y']
    return do_the_query

def object_history_sql_statement(columns: List[str], objectIds: Optional[list] = None) -> str:
    """Convience function that generates the SQL string needed to
    query the alerts table and aggregate data by objectId.
    When the resulting SQL query is executed, the query job will contain
    one row for each objectId, with the object's data aggregated into
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


#--- Format query results
def format_history_query_results(query_job: Optional[bigquery.job.QueryJob] = None, row: Optional[bigquery.table.Row] = None, format: str = 'pandas') -> Union[pd.DataFrame,str]:
    """Converts the results of a BigQuery query to the desired format.
    Must pass either query_job or row.
    Any duplicate observations will be dropped.

    Args:
        query_job: Results from a object history query job. SQL statement needed
                   to create the job can be obtained with object_history_sql_statement().
                   Must supply either query_job or row.

        row: A single row from query_job. Must supply either row or query_job.

        format: One of 'pandas' or 'json'. Input query results will be returned
                in this format.

    Returns:
        histories: Input query results converted to requested format
    """
    # make sure we have an appropriate param combination
    do_job, do_row = query_job is not None, row is not None
    good_format = format in ['pandas','json']
    good_combo = (do_job != do_row) and good_format
    if not good_combo:
        raise ValueError('Must pass one of query_job or row.')

    # convert query_job
    if do_job:
        histories = _format_history_query_results_to_df(query_job)  # df
        if format == 'json':
            histories = histories.reset_index().to_json()  # str

    # convert row
    if do_row:
        histories = _format_history_row_to_df(row)  # df
        if format == 'json':
            histories['objectId'] = histories.objectId  # persist metadata
            histories = histories.reset_index().to_json()  # str

    return histories

def _format_history_query_results_to_df(query_job: bigquery.job.QueryJob):
    """Convert a query_job (containing multiple rows of object history data)
    to a DataFrame.
    Any duplicate observations will be dropped.
    """
    dflist = []
    for r, row in enumerate(query_job):
        # convert to DataFrame
        df = _format_history_row_to_df(row)
        # add the objectId so we can use it to multi-index
        df['objectId'] = df.objectId
        # set the multi-index and append to the list
        dflist.append(df.reset_index().set_index(['objectId','candid']))

    histories = pd.concat(dflist)

    return histories

def _format_history_row_to_df(row: Union[dict,bigquery.table.Row]):
    """Convert a single object's history from a query row to a DataFrame.
    Any duplicate observations will be dropped.
    """
    d = dict(row.items())
    oid, cid = d.pop('objectId'), d.pop('candid')
    df = pd.DataFrame(data=d, index=pd.Index(cid, name='candid'))
    df.drop_duplicates(inplace=True)
    df.objectId = oid
    return df

#--- Plot query results
def plot_lightcurve(dflc: pd.DataFrame, ax: Optional[mpl.axes.Axes]=None, days_ago: bool=True):
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

#--- Get information about PGB datasets and tables
def get_table_info(table: Union[str,list] = 'all', dataset: str ='ztf_alerts'):
    """Retrieves and prints BigQuery table schemas.
    Adapted from:
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
        df = _get_table_columns(table=t)

        # print the metadata and column info
        print(df.table_name)
        print(tabulate(df, headers='keys', tablefmt='grid'))  # psql
        print(f'\n{df.table_name} has {df.num_rows} rows.\n')

def _get_table_columns(table: str, dataset: str ='ztf_alerts') -> pd.DataFrame:
    """Retrieves information about the columns in a BigQuery table and returns
    it as a DataFrame.

    Args:
        table: Name of the BigQuery table
        dataset: Name of BigQuery dataset that the table(s) belong to.
    Returns
        df: Column information from the BigQuery table schema.
    """

    bqtable = pgb_bq_client.get_table(f'{pgb_project_id}.{dataset}.{table}')
    cols = []
    for field in bqtable.schema:
        cols.append((field.name, field.description, field.field_type))

        if field.field_type == 'RECORD':
            for subfield in field.fields:
                cols.append((f'{field.name}.{subfield.name}', subfield.description, subfield.field_type))

    # cols = [(s.name, s.description, s.field_type, s.mode) for s in bqtable.schema]
    colnames = ['column_name', 'description', 'type']
    df = pd.DataFrame(cols, columns=colnames)

    # add some metadata
    df.table_name = f'{bqtable.project}.{bqtable.dataset_id}.{bqtable.table_id}'
    df.num_rows = bqtable.num_rows

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
    query_job = pgb_bq_client.query(query)
    tables = [row['table_name'] for row in query_job]
    return tables
