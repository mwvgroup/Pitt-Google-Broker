# Install apache-beam.
```python
run('pip install --quiet apache-beam')
run('pip install google-apitools')

# [Note:] The correct command should be
# run('pip install apache-beam[gcp]')
# rather than the two installs above.
# But the [gcp] tag breaks something in this environment (see below for the error).
# The correct install method works fine on my local machine, and I've tried
# using the same Beam version here (and many other things).
# I've lost the StackOverflow answer that led me to this solution and
# can't find it again, but as I recall it wasn't particularly insightful.
# (Something like, "I tried this and it worked", which is exactly where I'm at.)

# [Error:] When executing `beam.transforms.userstate.BagStateSpec(<...>)`, it throws:
# `AttributeError: module 'apache_beam' has no attribute 'transforms'`
# ("Transforms" are fundamental objects in Beam, it should definitely know what this is.)
```

# BigQuery Links
<!-- fs -->
- [Python Client for Google BigQuery](https://googleapis.dev/python/bigquery/latest/index.html)

- https://stackoverflow.com/questions/50885946/python-bigquery-api-get-table-schema/50908479
- https://cloud.google.com/bigquery/docs/information-schema-tables#columns_view
- https://googleapis.dev/python/bigquery/latest/usage/queries.html
- https://cloud.google.com/bigquery/docs/bigquery-storage-python-pandas#download_query_results_using_the_client_library
- https://beam.apache.org/releases/pydoc/2.28.0/apache_beam.io.gcp.bigquery.html
- https://beam.apache.org/documentation/io/built-in/google-bigquery/#reading-with-a-query-string
- https://www.tutorialspoint.com/sql/sql-distinct-keyword.htm
- https://cloud.google.com/bigquery/docs/reference/standard-sql/aggregate_functions#avg
- https://cloud.google.com/bigquery/docs/best-practices-performance-input
- https://cloud.google.com/bigquery/docs/reference/standard-sql/data-types?hl=pl

- https://alerce-new-python-client.readthedocs.io/en/main/tutorials/ztf_api.html#query-lightcurve
- https://noao.gitlab.io/antares/client/tutorial/searching.html

<!-- fe BQ links -->


# PyPI setup
<!-- fs -->
- [Packaging Python Projects](https://packaging.python.org/tutorials/packaging-projects/)
- [Packaging and distributing projects](https://packaging.python.org/guides/distributing-packages-using-setuptools/)
- [Example Project](https://github.com/pypa/sampleproject)
- [Working in “development mode”](https://packaging.python.org/guides/distributing-packages-using-setuptools/#working-in-development-mode)  

## Setup:
```bash
pgbenv
python -m pip install --upgrade pip setuptools wheel
python -m pip install twine

python3 -m pip install --upgrade build
```

## Build the distribution and upload it
```bash
cd /Users/troyraen/Documents/PGB/repo/pgb_utils
python3 -m build
python3 -m twine upload --repository testpypi dist/*
```
View at: https://test.pypi.org/project/pgb-utils-alpha/0.0.1/


## Work in development ("editable") mode:
```bash
conda create --name pgbtest python=3.7 pip ipython
conda activate pgbtest
export GOOGLE_APPLICATION_CREDENTIALS=/Users/troyraen/Documents/PGB/repo/GCPauth_pitt-google-broker-prototype-0679b75dded0.json

cd /Users/troyraen/Documents/PGB/repo/pgb_utils
python -m pip install -e .
```
```python
import pgb_utils_alpha as pgb

```
<!-- fe PyPI setup -->
