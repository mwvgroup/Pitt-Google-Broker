#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``bigquery`` module facilitates querying Pitt-Google Broker's
BigQuery databases and reading the results.
"""

import astropy
from astropy import coordinates as coord
from google.cloud import bigquery
import pandas as pd
from tabulate import tabulate
from typing import List, Tuple, Optional, Union, Generator


pgb_project_id = 'ardent-cycling-243415'

#--- BigQuery Client
user_bq_client, user_project_id = None, None  # module's global Client, related id

def create_client(project_id: str):
    """Open a BigQuery Client.

    Args:
        project_id: User's Google Cloud Platform project ID
    """
    global user_bq_client
    global user_project_id

    # instantiate the client
    print(f'\nInstantiating a BigQuery client with project_id: {project_id}\n')
    user_bq_client = bigquery.Client(project=project_id)

    # if the user passed a bad project_id, we won't know it yet. Let's check
    _create_client_raise_exception_if_not_connected(project_id)

    # client is connected. set the global user_project_id
    user_project_id = project_id

def _create_client_raise_exception_if_not_connected(project_id: str):
    """Checks that the user's client can successfully connect to our tables
    by executing a dry run query.
    """
    global user_bq_client

    query = f'SELECT candid FROM `{pgb_project_id}.ztf_alerts.salt2`'
    try:
        dry_run(query, notify=False)
    except:
        user_bq_client = None  # reset so the user can try again
        msg = (
            'You have tried to create a BigQuery Client with the project_id:\n'
            f'\t{project_id}\n'
            'But the Client cannot connect to the Pitt-Google Broker.\n'
            'Check that your project_id is valid '
            '(e.g., it should not be wrapped in quotes).'
        )
        raise ValueError(msg)

def _check_client_isinstance():
    msg = ("You must create a BigQuery client first. "
           "Run `pgb.bigquery.create_client('your_project_id')`")
    assert isinstance(user_bq_client, bigquery.client.Client), msg

def _create_client_if_needed():
    stop = False  # will be set to True if the user chooses to exit

    try:
        _check_client_isinstance()

    except AssertionError:
        # help the user open a bigquery client
        msg = ('\nTo run queries, you must first open a BigQuery Client.\n'
               'Enter your Google Cloud Platform project ID now '
               'or exit (just press Enter) and run\n'
               '`pgb.bigquery.create_client(my_project_id)`\n'
               '\nProject ID: '
        )
        project_id = input(msg) or ''

        if project_id == '':
            stop = True  # user wants to exit rather than creating a client
        else:
            create_client(project_id)

    return stop


#--- Get information about PGB datasets and tables
def get_table_info(table: Union[str,list] = 'all', dataset: str ='ztf_alerts'):
    """Retrieves and prints BigQuery table schemas.

    Args:

        table: Name of the BigQuery table or list of the same.
               'all' will print the info for all tables in the dataset.

        dataset: Name of BigQuery dataset that the table(s) belong to.
    """
    # if a bigquery Client does not exist, help the user instantiate one
    stop = _create_client_if_needed()
    if stop:  # the user has chosen to exit rather than create a client
        return

    # get the table names in a list
    if table == 'all':
        tables = get_dataset_table_names(dataset=dataset)
    elif type(table) == str:
        tables = [table]
    else:
        tables = table

    # get and print info about each table
    for t in tables:
        df = get_table_schema(table=t, dataset=dataset)

        # print the metadata and column info
        print(df.table_name)
        print(tabulate(df, headers='keys', tablefmt='grid'))  # psql
        print(f'\n{df.table_name} has {df.num_rows} rows.\n')

def get_table_schema(table: str, dataset: str ='ztf_alerts') -> pd.DataFrame:
    """Retrieves information about the columns in a BigQuery table and returns
    it as a DataFrame.

    Args:
        table: Name of the BigQuery table
        dataset: Name of BigQuery dataset that the table(s) belong to.
    Returns
        df: Column information from the BigQuery table schema.
    """
    # if a bigquery Client does not exist, help the user instantiate one
    stop = _create_client_if_needed()
    if stop:  # the user has chosen to exit rather than create a client
        return

    bqtable = user_bq_client.get_table(f'{pgb_project_id}.{dataset}.{table}')
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
    # if a bigquery Client does not exist, help the user instantiate one
    stop = _create_client_if_needed()
    if stop:  # the user has chosen to exit rather than create a client
        return

    print(f'Getting table names for dataset: {dataset}')

    query = (
        'SELECT * '
        f'FROM {pgb_project_id}.{dataset}.INFORMATION_SCHEMA.TABLES'
    )
    query_job = user_bq_client.query(query)
    tables = [row['table_name'] for row in query_job].sort()
    return tables


#--- Setup to query for object histories
def get_history_column_names() -> List[str]:
    """
    Returns:
        historycols: Column names appropriate for querying object histories.

    Note: It would be convenient to also return the column descriptions, but
         that is more complicated, and this function will be completely
         obsolete if we change the database structure to store only the
         "candidate" observation and metadata.
    """
    objectcols = ['objectId',]
    flatcols = ['schemavsn','publisher','candid',]
    dropcols = ['prv_candidates', 'cutoutScience', 'cutoutDifference', 'cutoutTemplate']

    sdf = get_table_schema('alerts')
    schemacols = list(sdf['column_name'])

    # drop the prv_candidates and cutout columns
    historycols = [c for c in schemacols if c.split('.')[0] not in dropcols]

    # drop the full "candidate" RECORD column
    historycols.remove('candidate')

    # drop "candidate.candid" as it is simply a repeat of "candid"
    historycols.remove('candidate.candid')

    # strip out "candidate." from nested columns
    # query_objects() uses only the base names
    historycols = [c.replace('candidate.','') for c in historycols]

    return historycols

def check_history_column_names(columns: List[str]) -> Union[List[str],bool]:
    """Make sure user-submitted column names are appropriate to query object histories.
    """

def _split_good_bad_history_column_names(columns: List[str]) -> Tuple[List[str],List[str]]:
    """Split columns list into "good" and "bad" according to whether they are
    suitable for querying an object's history.
    """
    badcols = list(set(columns) - set(get_history_column_names()))
    goodcols = columns.copy()
    for bc in badcols:
        goodcols.remove(bc)
    return (goodcols, badcols)

def object_history_sql_statement(columns: List[str],
                                 objectIds: Optional[list] = None,
                                 limit: Optional[int] = None
                                 ) -> str:
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
        limit: Maximum number of rows to be returned.

    Returns:
        query: SQL statement to query the alerts table and aggregate data by objectId.
    """
    dataset = 'ztf_alerts'
    table = 'alerts'
    objectcols = ['objectId',]  # columns unique to an object
    # make sure 'candid' is in columns. (objectcols handled separately)
    columns = list(set(columns).union(set(['candid'])))

    # SELECT statement
    # create a list of strings that will aggregate columns into arrays
    aggcols = _list_aggcols_sql_statements(columns)
    selects = f'SELECT {", ".join(objectcols + aggcols)}'

    # FROM statement
    froms = f'FROM `{pgb_project_id}.{dataset}.{table}`'
    # concat the statements into the beginning of a SQL query statement
    sqlquery = ' '.join([selects, froms])

    # WHERE statement
    if objectIds is not None:
        # wrap each objectId in quotes and join to single string
        oids = ','.join([f'"{o}"' for o in objectIds])
        wheres = f'WHERE objectId IN ({oids})'
        # concat the statements into a SQL query statement
        sqlquery = ' '.join([sqlquery, wheres])

    # GROUP BY statement
    groupbys = f'GROUP BY objectId'
    sqlquery = ' '.join([sqlquery, groupbys])

    # LIMIT statement
    if limit is not None:
        limits = f'LIMIT {limit}'
        sqlquery = ' '.join([sqlquery, limits])

    return sqlquery

def _list_aggcols_sql_statements(columns: List[str]) -> List[str]:
    """Create a list of SQL string query segments that will aggregate
    all columns not in objectcols.
    """
    objectcols = ['objectId',]
    flatcols = ['schemavsn','publisher','candid',]

    # list of requested flatcols
    fcols = list(set(columns) & set(flatcols))
    # list of requested columns nested under 'candidate'
    ncols = list(set(columns) - set(objectcols) - set(flatcols))
    ncols = [f'candidate.{c}' for c in ncols]
    # complete list of columns to be aggregated (group by) objectId
    aggcols = fcols + ncols
    # attach the ARRAY_AGG, ORDER By, and AS statements to the aggcols
    aggcols = [f'ARRAY_AGG({c} ORDER BY candidate.jd) AS {c.split(".")[-1]}' for c in aggcols]

    return aggcols


#--- Dry runs
def dry_run(query: str, notify: bool = True):
    """Perform a dry run to find out how many bytes the query will process.
    Args:
        query: SQL query statement
    """
    global user_project_id
    _check_client_isinstance()  # make sure we have a bigquery.client

    job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
    query_job = user_bq_client.query(query, job_config=job_config)

    if notify:
        nbytes, TiB = query_job.total_bytes_processed, 2**40
        pTiB = nbytes/TiB*100  # nbytes as a percent of 1 TiB
        print(f'\nQuery statement:')
        print(f'\n"{query}"\n')
        print(f'will process {nbytes} bytes of data.')
        print(f'({pTiB:.3}% of your 1 TiB Free Tier monthly allotment.)')

def _dry_run_and_confirm(query: str) -> bool:
    # print dry run info
    dry_run(query)
    # ask user if they want to proceed
    cont = input('Continue? [y/N]: ') or 'N'
    do_the_query = cont in ['y','Y']
    return do_the_query


#--- Query for object histories
def query_objects(columns: List[str],
                  objectIds: Optional[list] = None,
                  limit: Optional[int] = None,
                  format: str = 'pandas',
                  iterator: bool = False,
                  dry_run: bool = True
                  ) -> Union[str,
                             pd.DataFrame,
                             bigquery.job.QueryJob,
                             Generator[Union[str, pd.DataFrame], None, None]]:
    """Query the alerts database for object histories.

    Args:
        columns: Names of columns to select from the alerts table.
                 The 'objectId' and 'candid' columns are automatically included
                 and do not need to be in this list.
        objectIds: IDs of ZTF objects to include in the query.
        limit: Limit the number of objects returned to N <= limit.
        format: One of 'pandas', 'json', or 'query_job'. Query results will be
                returned in this format. Results returned as 'query_job' may
                contain duplicate observations; else duplicates are dropped.
        iterator: If True, iterate over the objects and return one at a time.
                  Else return the full query results together.
                  This parameter is ignored if `format` == 'query_job'.
        dry_run: If True, `pgb.bigquery.dry_run` will be called first and the
                 user will be asked to confirm before continuing.

    Returns: Query results in the requested format. If `iterator` is True,
             yields one object at a time; else all results are returned together.
    """

    # make sure we have appropriate column names
    goodcols = _query_objects_check_history_column_names(columns)
    if len(goodcols) == 0:  # user submitted bad columns and wants to abort
        return

    # if a bigquery client does not exist, help the user instantiate one
    stop = _create_client_if_needed()
    if stop:  # the user has chosen to exit rather than create a client
        return

    # generate the SQL statement to query alerts db and aggregate histories
    query = object_history_sql_statement(goodcols, objectIds, limit=limit)  # str

    # print dry run results
    if dry_run:
        do_the_query = _dry_run_and_confirm(query)
        if not do_the_query:  # user has chosen to abort the query
            return

    # make the API call
    query_job = user_bq_client.query(query)

    # return the results
    if format == 'query_job':
        return query_job
    elif iterator:  # return a generator that cycles through the objects/rows
        return (format_history_query_results(row=row, format=format) for row in query_job)
    else:  # format and return all rows at once
        return format_history_query_results(query_job=query_job, format=format)

def _query_objects_check_history_column_names(columns: List[str]) -> List[str]:
    """Make sure user-submitted column names are appropriate for `query_objects()`.
    Returns one of:
        Columns stripped of bad column names.
        Empty list if there were bad columns and the user wants to abort the query.
    """
    goodcols, badcols = _split_good_bad_history_column_names(columns)

    try:
        assert len(badcols) == 0
    except AssertionError:
        msg = (
            '\nYou have requested columns that are not available to `query_objects()`.\n'
            '(To view available columns, use `pgb.bigquery.get_history_column_names()`)\n'
            f'\nRequested columns:\n\t{columns}\n'
            f'Unavailable columns:\n\t{badcols}\n'
            '\nProceed without the unavailable columns? [y/N] '
        )
        proceed = input(msg) or 'N'

        if proceed not in ['y','Y']:  # user wants to exit; return an empty list
            return []

    return goodcols


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


#--- Cone Search
def cone_search(center: astropy.coordinates.SkyCoord,
                radius: astropy.coordinates.Angle,
                columns: List[str],
                objectIds: Optional[list] = None,
                format: str = 'pandas',
                iterator: bool = False,
                dry_run: bool = True,
                ) -> Union[str,
                           pd.DataFrame,
                           Generator[Union[str, pd.DataFrame], None, None]]:
    """Perform a cone search on the alerts database and return object histories.
    This uses the coordinates of the most recent observation to determine
    whether an object is within the cone.

    Args:
        center: Center of the cone to search within.
        radius: Radius of the cone to search within.
        columns: Names of history columns to select from the alerts table.
                 The 'objectId' and 'candid' columns are automatically included
                 and do not need to be in this list.
        objectIds: IDs of ZTF objects to include in the query.
        format: One of 'pandas', or 'json'. Query results will be
                returned in this format. Duplicate observations are dropped.
        iterator: If True, iterate over the objects and return one at a time.
                  Else return the full query results together.
        dry_run: If True, `pgb.bigquery.dry_run` will be called first and the
                 user will be asked to confirm before continuing.

    Returns: Query results in the requested format. If `iterator` is True,
             returns a generator; else all results are returned together.
    """
    # make sure we have required columns
    for c in ['jd', 'ra', 'dec']:
        if c not in columns: columns.append(c)

    # Performing a dry run prints the SQL query statement, which does not account
    # for the cone search. We'll print some things to reduce user confusion.
    if dry_run: print('\nInitiating a cone search.')

    # Query the database for object histories.
    objects = query_objects(columns,
                            objectIds = objectIds,
                            format = 'pandas',
                            iterator=iterator,
                            dry_run=dry_run
                            )
    # == None if user chose to abort; else DataFrame or generator of same
    if objects is None:
        return

    if dry_run: print('\nFiltering for objects within the given cone.')

    # filter out objects not in the cone and return the rest
    objects_in_cone = _do_cone_search(objects, center, radius, format, iterator)
    return objects_in_cone


def _do_cone_search(objects: Union[pd.DataFrame,Generator[pd.DataFrame, None, None]],
                    center: astropy.coordinates.SkyCoord,
                    radius: astropy.coordinates.Angle,
                    format: str = 'pandas',
                    iterator: bool = False,
                    ) -> Union[str,
                               pd.DataFrame,
                               Generator[Union[str, pd.DataFrame], None, None]]:
    """Apply the cone search filter and return appropriate objects.
    """

    if iterator:  # objects is a generator, return a generator
        return _do_cone_search_iterator(objects, center, radius, format)

    else:  # objects is single df
        return _do_cone_search_all(objects, center, radius, format)

def _do_cone_search_iterator(objects: pd.DataFrame, center: astropy.coordinates.SkyCoord, radius: astropy.coordinates.Angle, format):
    """Iterate objects, format and yield those that are in the cone.

    Args:
        objects: DataFrame containing histories of multiple objectIds.
    """
    for df in objects:
        in_cone = object_is_in_cone(df, center, radius)

        if in_cone:  # format and yield
            if format == 'json':
                df['objectId'] = df.objectId  # else metadata is lost
                object = df.reset_index().to_json()  # str
            else:
                object = df
            yield object

def _do_cone_search_all(objects: pd.DataFrame, center: astropy.coordinates.SkyCoord, radius: astropy.coordinates.Angle, format):
    """Filter out objects not in the cone, format, and return.

    Args:
        objects: DataFrame containing histories of multiple objectIds.
    """
    gb = objects.groupby(level='objectId')
    objects_in_cone = gb.filter(lambda df: object_is_in_cone(df,center,radius))
    if format == 'json':
        objects_in_cone = objects_in_cone.reset_index().to_json()  # str
    return objects_in_cone

def object_is_in_cone(object: pd.DataFrame, center: astropy.coordinates.SkyCoord, radius: astropy.coordinates.Angle):
    """Checks whether the object's most recent observation has a position that
    is within a cone defined by center and radius.

    Args:
        object: DataFrame containing the history of a single objectId.
                Required columns: ['jd','ra','dec']
        center: Center of the cone to search within.
        radius: Radius of the cone to search within.

    Returns:
        in_cone: True if object is within radius of center, else False
    """
    # get the SkyCoords of the most recent observation
    # to do: use the epoch with highest S/N instead
    obs = object.loc[object['jd']==object['jd'].max(),:]
    obs_coords = coord.SkyCoord(obs['ra'], obs['dec'], frame='icrs', unit='deg')

    # check whether obs_coords are within the cone
    dist = center.separation(obs_coords)
    in_cone = dist < radius  # array with a single bool
    in_cone = in_cone[0]

    return in_cone
