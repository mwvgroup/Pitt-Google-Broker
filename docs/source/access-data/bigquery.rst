BigQuery Databases
==================

-  `Prerequisites`_
-  `Python`_

   -  `Setup and basics`_
   -  `Query lightcurves and other history`_

      -  `Plot a lightcurve`_

   -  `Cone search`_
   -  `Using google.cloud.bigquery`_

-  `Command line`_

This tutorial covers downloading and working with data from our BigQuery
databases via two methods: the pgb-utils Python package, and the bq CLI.

For more information, see: - `Google Cloud BigQuery Python client
documentation <https://googleapis.dev/python/bigquery/latest/index.html>`__
(the pgb-utils functions used below are thin wrappers for this API) -
`bq CLI
reference <https://cloud.google.com/bigquery/docs/reference/bq-cli-reference>`__

Prerequisites
-------------

1. Complete the :doc:`initial-setup`. Be sure to:

   -  set your environment variables
   -  enable the BigQuery API
   -  install the pgb-utils package if you want to use Python
   -  install the CLI if you want to use the command line

Python
------

Setup and basics
~~~~~~~~~~~~~~~~

Imports

.. code:: python

    import pgb_utils as pgb
    import os

Create a Client for the BigQuery connections below

.. code:: python

    my_project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
    pgb.bigquery.create_client(my_project_id)

View the available tables and their schemas

.. code:: python

    # see which tables are available
    pgb.bigquery.get_dataset_table_names()

    # look at the schema and basic info of a table
    table = 'DIASource'
    pgb.bigquery.get_table_info(table)

Query lightcurves and other history
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Setup

.. code:: python

    # Choose the history data you want returned
    columns = ['jd', 'fid', 'magpsf', 'sigmapsf']
    # 'objectId' and 'candid' will be included automatically
    # options are columns in the 'DIASource' table
    # pgb.bigquery.get_table_info('DIASource')

    # Optional
    # choose specific objects
    objectIds = ['ZTF18aczuwfe', 'ZTF18aczvqcr', 'ZTF20acqgklx', 'ZTF18acexdlh']
    # limit to a sample of the table
    # limit = 1000  # add this keyword to query_objects() below

To retrieve lightcurves and other history, we must query for objects'
"DIASource" observations and aggregate the results by ``objectId``.

``pgb.bigquery.query_objects()`` is a convenience wrapper that let's you
grab all the results at once, or step through them using a generator.
It's options are demonstrated below.

.. code:: python

    # Option 1: Get a single DataFrame of all results

    lcs_df = pgb.bigquery.query_objects(columns, objectIds=objectIds)
    # This will execute a dry run and tell you how much data will be processed.
    # You will be asked to confirm before proceeding.
    # In the future we'll skip this using
    dry_run = False

    lcs_df.sample(10)
    # cleaned of duplicates

Congratulations! You've now retrieved your first data from the transient
table. It is a DataFrame containing the candidate observations for every
object we requested, indexed by ``objectId`` and ``candid`` (candidate
ID). It includes the columns we requested in the query.

``fid`` is the filter, mapped to an integer. You can see the filter's
common name in the table schema we looked at earlier, or you can use
``pgb.utils.ztf_fid_names()`` which returns a dictionary of the mapping.

.. code:: python

    # map fid column to the filter's common name
    fid_names = pgb.utils.ztf_fid_names()  # dict
    print(fid_names)

    lcs_df['filter'] = lcs_df['fid'].map(fid_names)
    lcs_df.head()

Queries can return large datasets. You may want to use a generator to
step through objects individually, and avoid loading the entire dataset
into memory at once. ``query_objects()`` can return one for you:

.. code:: python

    # Option 2: Get a generator that yields a DataFrame for each objectId

    iterator = True
    objects = pgb.bigquery.query_objects(
        columns, objectIds=objectIds, iterator=iterator, dry_run=dry_run
    )
    # cleaned of duplicates

    for lc_df in objects:
        print(f'\nobjectId: {lc_df.objectId}')  # objectId in metadata
        print(lc_df.sample(5))

Each DataFrame contains data on a single object, and is indexed by
``candid``. The ``objectId`` is in the metadata.

``query_objects()`` can also return a json formatted string of the query
results:

.. code:: python

    # Option 3: Get a single json string with all the results

    format = 'json'
    lcsjson = pgb.bigquery.query_objects(
        columns, objectIds=objectIds, format=format, dry_run=dry_run
    )
    # cleaned of duplicates
    print(lcsjson)

    # read it back in
    df = pd.read_json(lcsjson)
    df.head()

.. code:: python

    # Option 4: Get a generator that yields a json string for a single objectId

    format = 'json'
    iterator = True
    jobj = pgb.bigquery.query_objects(
        columns, objectIds=objectIds, format=format, iterator=iterator, dry_run=dry_run
    )
    # cleaned of duplicates

    for lcjson in jobj:
        print(lcjson)
        # lc_df = pd.read_json(lcjson)  # read back to a df

Finally, ``query_objects()`` can return the raw query job object that it
gets from its API call using ``google.cloud.bigquery``'s ``query()``
method.

.. code:: python

    # Option 5: Get the `query_job` object
    #           (see the section on using google.cloud.bigquery directly)

    query_job = pgb.bigquery.query_objects(
        columns, objectIds=objectIds, format="query_job", dry_run=dry_run
    )
    # query_job is iterable
    # each element contains the aggregated history for a single objectId
    # Beware: this has not been cleaned of duplicate entries

.. code:: python

    # Option 5 continued: parse query_job results row by row

    for row in query_job:
        # values can be accessed by field name or index
        print(f"objectId={row[0]}, magpsf={row['magpsf']}")

        # pgb can cast to a DataFrame or json string
        # this option also cleans the duplicates
        lc_df = pgb.bigquery.format_history_query_results(row=row)
        print(f'\nobjectId: {lc_df.objectId}')  # objectId in metadata
        print(lc_df.head(1))
        lcjson = pgb.bigquery.format_history_query_results(row=row, format='json')
        print('\n', lcjson)

        break

Plot a lightcurve
^^^^^^^^^^^^^^^^^

.. code:: python

    # Get an object's lightcurve DataFrame with the minimum required columns
    columns = ['jd','fid','magpsf','sigmapsf','diffmaglim']
    objectId = 'ZTF20acqgklx'
    lc_df = pgb.bigquery.query_objects(columns, objectIds=[objectId], dry_run=False)

    # make the plot
    pgb.figures.plot_lightcurve(lc_df, objectId=objectId)

Cone search
~~~~~~~~~~~

To perform a cone search, we query for object histories and then check
whether they are within the cone. ``pgb.bigquery.cone_search()`` is a
convenience wrapper provided
for demonstration, but note that it is very inefficient.

First we set the search parameters.

.. code:: python

    center = coord.SkyCoord(76.91, 6.02, frame='icrs', unit='deg')
    radius = coord.Angle(2, unit=u.deg)

    columns = ['jd', 'fid', 'magpsf', 'sigmapsf']
    # 'objectId' and 'candid' will be included automatically
    # options are in the 'DIASource' table
    # pgb.bigquery.get_table_info('DIASource')
    dry_run = False

    # we'll restrict to a handful of objects to reduce runtime, but this is optional
    objectIds = ['ZTF18aczuwfe', 'ZTF18aczvqcr', 'ZTF20acqgklx', 'ZTF18acexdlh']

``cone_search()`` has similar options to ``query_objects()``.
Here we demonstrate one.

.. code:: python

    # Option 1: Get a single df of all objects in the cone

    objects_in_cone = pgb.bigquery.cone_search(
        center, radius, columns, objectIds=objectIds, dry_run=dry_run
    )
    objects_in_cone.sample(5)


--------------

Using google.cloud.bigquery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The previous sections demonstrated convenience wrappers for querying
with ``google.cloud.bigquery``. Here we demonstrate using these tools
directly with some basic examples. View the pgb\_utils source code for
more examples.

Links to more information:

-   `Query syntax in Standard
    SQL <https://cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax>`__
-   `google.cloud.bigquery
    docs <https://googleapis.dev/python/bigquery/latest/index.html>`__

Query setup:

.. code:: python

    # Create a BigQuery Client to handle the connections
    bq_client = bigquery.Client(project=my_project_id)

.. code:: python

    # Write the standard SQL query statement

    # pgb.bigquery.get_dataset_table_names()  # view available tables
    # pgb.bigquery.get_table_info('<table>')  # view available column names

    # construct the full table name
    pgb_project_id = 'ardent-cycling-243415'
    table = 'salt2'
    dataset = 'ztf_alerts'
    full_table_name = f'{pgb_project_id}.{dataset}.{table}'

    # construct the query
    query = (
        f'SELECT objectId, candid, t0, x0, x1, c, chisq, ndof '
        f'FROM `{full_table_name}` '
        f'WHERE ndof>0 and chisq/ndof<2 '
    )

    # note: if you want to query object histories you can get the
    # query statement using `pgb.bigquery.object_history_sql_statement()`

.. code:: python

    # Let's create a function to execute a "dry run"
    # and tell us how much data will be processed.
    # This is essentially `pgb.bigquery.dry_run()`
    def dry_run(query):
        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        query_job = bq_client.query(query, job_config=job_config)
        nbytes, TiB = query_job.total_bytes_processed, 2**40
        pTiB = nbytes/TiB*100  # nbytes as a percent of 1 TiB
        print(f'\nQuery statement:')
        print(f'\n"{query}"\n')
        print(f'will process {nbytes} bytes of data.')
        print(f'({pTiB:.3}% of your 1 TiB Free Tier monthly allotment.)')

.. code:: python

    # Find out how much data will be processed
    dry_run(query)

Query:

.. code:: python

    # Make the API request
    query_job = bq_client.query(query)
    # Beware: the results may contain duplicate entries

Format and view results:

.. code:: python

    # Option 1: dump results to a pandas.DataFrame
    df = query_job.to_dataframe()

    # some things you might want to do with it
    df = df.drop_duplicates()
    df = df.set_index(['objectId','candid']).sort_index()

    df.hist()
    df.head()

.. code:: python

    # Option 2: parse results row by row
    for r, row in enumerate(query_job):

        # row values can be accessed by field name or index
        print(f"objectId={row[0]}, t0={row['t0']}")

        if r>5: break

--------------

Command line
------------

Links to more information:

-   `Quickstart using the bq command-line
    tool <https://cloud.google.com/bigquery/docs/quickstarts/quickstart-command-line>`__
-   `Reference of all bq commands and
    flags <https://cloud.google.com/bigquery/docs/reference/bq-cli-reference>`__
-   `Query syntax in Standard
    SQL <https://cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax>`__

.. code:: bash

    # Get help
    bq help query

.. code:: bash

    # view the schema of a table
    bq show --schema --format=prettyjson ardent-cycling-243415:ztf_alerts.DIASource
    # bq show --schema --format=prettyjson ardent-cycling-243415:ztf_alerts.alerts

    # Note: The first time you make a call with `bq` you will ask you to
    # initialize a .bigqueryrc configuration file. Follow the directions.

.. code:: bash

    # Query: dry run

    # first we do a dry_run by including the flag --dry_run
    bq query \
    --dry_run \
    --use_legacy_sql=false \
    'SELECT
        objectId, candid, t0, x0, x1, c, chisq, ndof
    FROM
        `ardent-cycling-243415.ztf_alerts.salt2`
    WHERE
        ndof>0 and chisq/ndof<2
    LIMIT
        10'

.. code:: bash

    # execute the Query
    bq query \
    --use_legacy_sql=false \
    "SELECT
        objectId, candid, t0, x0, x1, c, chisq, ndof
    FROM
        `ardent-cycling-243415.ztf_alerts.salt2`
    WHERE
        ndof>0 and chisq/ndof<2
    LIMIT
        10"
