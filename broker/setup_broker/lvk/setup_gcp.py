#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``setup_gcp`` module is used to setup and teardown Google Cloud Platform (GCP)
resources for use by the broker, including:
1. BigQuery datasets
2. Cloud Storage buckets (includes uploading requested files to bucket)
3. Pub/Sub topics and subscriptions

All resources are named/defined in the ``_resources`` function.
To setup/teardown new resources, add them to this function.

Setup:
This is the default behavior of all relevant functions.
Setup tasks can be run individually, or collectively using the ``auto_setup`` function.
Resources that already exist are skipped _except_ that files are still
uploaded to buckets, overwritting existing files (this is a feature, not a bug).
It is therefore safe to update and/or re-run the setup functions to ensure that
all needed resources exist/are current.

Teardown:
Use the ``teardown`` keyword argument to delete resources.
This is intended to be used on non-production resources (currently, test resources).
To avoid deleting resources used in production, this option should not be
used with ``testid=False`` (see below).
To ensure that this is not done by accident, every function that can delete
resources first calls the function ``_do_not_delete_production_resources``,
which throws an error if it receives this combination of arguments.

Production or Testing Resources:
(See Usage Examples below.)
The default behavior is to operate on _testing_ resources, since they will be
setup/torndown much more frequently than production resources.
To control the tag that is appended to resource names, use the ``testid`` argument (e.g., ``testid=mytest``).
To operate on production resources:
- from the command line, use the ``--production`` argument
- in Python, use ``testid=False``


Usage Examples
-------------

From command line:

.. code-block: bash
    :linenos:

    # Setup production resources
    python3 setup_gcp.py --production

    # Setup test resources
    python3 setup_gcp.py --testid=mytest

    # Teardown test resources
    python3 setup_gcp.py --testid=mytest --teardown

In Python:

.. code-block:: python
   :linenos:

   from broker import gcp_setup

   survey = 'ztf'
   testid = 'mytest'
   teardown = False

   # Run individual tasks
   gcp_setup.setup_bigquery(survey=survey, testid=testid, teardown=teardown)
   gcp_setup.setup_buckets(survey=survey, testid=testid, teardown=teardown)
   gcp_setup.setup_pubsub(survey=survey, testid=testid, teardown=teardown)

   # Run all tasks
   gcp_setup.auto_setup(survey=survey, testid=testid, teardown=teardown)


Module Documentation
--------------------
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from warnings import warn

from google.api_core.exceptions import NotFound
from google.cloud import bigquery, pubsub_v1, storage

PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')


def _resources(service, survey='lvk', testid='test', versiontag="O4"):
    """ Names the GCP resources to be setup/torn down.

    Args:
        service (str): which GCP service resources to return.
        survey (str): which astronomical survey the broker instance will
                      connect to. Controls the names of resources and the
                      behavior of functions that rely on schemas.
        testid (False or str): False: Use production resources.
                                str: Use test resources. (This string is
                                appended to the resource names.)
        versiontag (str): Tag indicating Avro schema version. Appended to
                          some resource names.
    """

    if service == 'BQ':
        datasets = {
            survey: [
                f'alerts_{versiontag}',
            ]
        }
        table_data = {"class_descriptions": "class_descriptions_data"}

        # append the testid to the dataset name only
        if testid is not False:
            dtmp = {f'{key}_{testid}': val for key, val in datasets.items()}
            datasets = dtmp
        return (datasets, table_data)

    if service == 'GCS':
        buckets = {  # '<bucket-name>': ['<file-name to upload>',]
            # the avro bucket f'{PROJECT_ID}-{survey}_alerts_{versiontag}'
            # is managed in broker/cloud_functions/ps_to_gcs/deploy.sh
            f'{PROJECT_ID}-{survey}-broker_files': [],
        }

        # append the testid
        if testid is not False:
            btmp = {f'{key}-{testid}': val for key, val in buckets.items()}
            buckets = btmp
        return buckets

    if service == 'PS':
        topics = {  # '<topic_name>': ['<subscription_name>', ]
                # f'{survey}-alerts_raw':
                #     [],
                f'{survey}-BigQuery':
                    [],
                f'{survey}-alerts':
                    [f'{survey}-alerts-reservoir'],
        }

        # append the testid
        if testid is not False:
            ttmp = {f'{key}-{testid}': val for key, val in topics.items()}
            for key, val in ttmp.items():
                ttmp[key] = [f'{v}-{testid}' for v in val]
            topics = ttmp
        return topics


def _do_not_delete_production_resources(survey='lvk', testid='test', teardown=True):
    """ If the user is requesting to delete resources used in production,
    throw an error.

    Args:
        survey (str): which astronomical survey the broker instance will
                      connect to. Controls the names of resources and the
                      behavior of functions that rely on schemas.
        testid (False or str): False: Use production resources.
                                str: Use test resources. (This string is
                                appended to the resource names.)
        teardown (bool): if True, delete resources rather than setting them up
    """
    if teardown and not testid:
        msg = (f'\nReceived teardown={teardown} and testid={testid}.\n'
               f'Exiting to prevent the teardown of production resources.\n')
        raise ValueError(msg)


def _confirm_options(survey, testid, teardown):
    """ Require the user to confirm options that determine
    the behavior of this script.

    Args:
        survey (str): which astronomical survey the broker instance will
                      connect to. Controls the names of resources and the
                      behavior of functions that rely on schemas.
        testid (False or str): False: Use production resources.
                                str: Use test resources. (This string is
                                appended to the resource names.)
        teardown (bool): if True, delete resources rather than setting them up
    """
    behavior = 'DELETE' if teardown else 'SETUP'
    if not testid:
        resources = 'PRODUCTION resources'
    else:
        resources = f'"{survey}" resources tagged with "{testid}"'
    msg = (f'\nsetup_gcp will {behavior} all bq, gcs, and ps {resources}.\n'
           'Continue?  [Y/n]:  ')
    continue_with_setup = input(msg) or 'Y'

    if continue_with_setup not in ['Y', 'y']:
        msg = 'Exiting setup_gcp.py'
        sys.exit(msg)


def setup_bigquery(survey='lvk', testid='test', teardown=False, versiontag="O4", region="us-central1") -> None:
    """Create the necessary Big Query datasets if they do not already exist
    Args:
        survey (str): which astronomical survey the broker instance will
                      connect to. Controls the names of resources and the
                      behavior of functions that rely on schemas.
        testid (False or str): False: Use production resources.
                                str: Use test resources. (This string is
                                appended to the resource names.)
        teardown (bool): if True, delete resources rather than setting them up
        versiontag (str): Tag indicating Avro schema version. Appended to
                          some resource names.
        region (str): GCP region of the dataset.

    New datasets include:
      ``{survey}``
    """
    _do_not_delete_production_resources(survey=survey, testid=testid, teardown=teardown)

    (datasets, table_data) = _resources('BQ', survey=survey, testid=testid, versiontag=versiontag)
    bigquery_client = bigquery.Client(location=region)

    for dataset, tables in datasets.items():
        if teardown:
            # Delete dataset
            kwargs = {'delete_contents': True, 'not_found_ok': True}
            bigquery_client.delete_dataset(dataset, **kwargs)
            print(f'Deleted dataset {dataset}')
        else:
            # Create dataset
            try:
                bigquery_client.get_dataset(dataset)
                print(f"Skipping existing dataset: {dataset}")
            except NotFound:
                bigquery_client.create_dataset(dataset)
                print(f'Created dataset: {dataset}')

            # create the tables
            # use the bq CLI so we can create the table from a schema file
            for table in tables:
                try:
                    table_id = f'{PROJECT_ID}.{dataset}.{table}'
                    bigquery_client.get_table(table_id)
                    print(f'Skipping existing table: {table_id}.')
                except NotFound:
                    table_id = f"{PROJECT_ID}:{dataset}.{table}"
                    schema = f"templates/bq_{survey}_{table}_schema"
                    if table_data.get(table):
                        # make the table and load the data
                        data = f"templates/bq_{survey}_{table_data[table]}.csv"
                        flags = f"--schema={schema}.json --source_format=CSV"
                        bqload = f'bq load {flags} {table_id} {data}'
                        out = subprocess.check_output(shlex.split(bqload))
                        print(f'{out}')  # should be a success message
                    else:
                        # no data to load, just create the table
                        bqmk = f'bq mk --table {table_id} {schema}.json'
                        out = subprocess.check_output(shlex.split(bqmk))
                        print(f'{out}')  # should be a success message

def setup_buckets(survey='lvk', testid='test', teardown=False, versiontag="O4", region="us-central1") -> None:
    """Create new storage buckets and upload testing files.
    Files are expected to reside in the ``tests/test_alerts`` directory.

    Args:
        survey (str): which astronomical survey the broker instance will
                      connect to. Controls the names of resources and the
                      behavior of functions that rely on schemas.
        testid (False or str): False: Use production resources.
                                str: Use test resources. (This string is
                                appended to the resource names.)
        teardown (bool): if True, delete resources rather than setting them up
        versiontag (str): Tag indicating Avro schema version. Appended to
                          some resource names.
        region (str): GCP region of the bucket.
    """
    _do_not_delete_production_resources(survey=survey, testid=testid, teardown=teardown)

    buckets = _resources('GCS', survey=survey, testid=testid, versiontag=versiontag)
    storage_client = storage.Client()

    for bucket_name, files in buckets.items():
        # -- Create or delete buckets
        try:
            bucket = storage_client.get_bucket(bucket_name)
        except NotFound:
            if not teardown:
                # Create bucket
                storage_client.create_bucket(bucket_name, location=region)
                print(f'Created bucket {bucket_name}')
        else:
            if teardown:
                # Delete bucket
                try:
                    bucket.delete(force=True)
                except ValueError as e:
                    warn(f'Cannot delete {bucket_name}.\n{e}')
                    pass
                else:
                    print(f'Deleted bucket {bucket_name}')
            else:
                print(f'Skipped existing bucket: {bucket_name}')

        # -- Upload any files
        if not teardown and len(files) > 0:
            bucket = storage_client.get_bucket(bucket_name)
            for filename in files:
                blob = bucket.blob(filename)
                inpath = Path('../../tests/test_alerts') / filename
                with inpath.open('rb') as infile:
                    blob.upload_from_file(infile)
                print(f'Uploaded {inpath} to {bucket_name}')


def setup_pubsub(survey='lvk', testid='test', teardown=False) -> None:
    """ Create new Pub/Sub topics and subscriptions.
    Args:
        survey (str): which astronomical survey the broker instance will
                      connect to. Controls the names of resources and the
                      behavior of functions that rely on schemas.
        testid (False or str): False: Use production resources.
                                str: Use test resources. (This string is
                                appended to the resource names.)
        teardown (bool): if True, delete resources rather than setting them up
    """
    _do_not_delete_production_resources(survey=survey, testid=testid, teardown=teardown)

    topics = _resources('PS', survey=survey, testid=testid)
    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()

    for topic, subscriptions in topics.items():

        # -- Create or delete topic
        topic_path = publisher.topic_path(PROJECT_ID, topic)
        if teardown:
            # Delete topic
            try:
                publisher.delete_topic(topic=topic_path)
            except NotFound:
                pass
            else:
                print(f'Deleted topic {topic}')
        else:
            try:
                publisher.get_topic(topic=topic_path)
            except NotFound:
                # Create topic
                publisher.create_topic(name=topic_path)
                print(f'Created topic {topic}')

        # -- Create or delete subscriptions
        for sub_name in subscriptions:
            sub_path = subscriber.subscription_path(PROJECT_ID, sub_name)
            if teardown:
                # Delete subscription
                try:
                    subscriber.delete_subscription(subscription=sub_path)
                except NotFound:
                    pass
                else:
                    print(f'Deleted subscription {sub_name}')
            else:
                try:
                    subscriber.get_subscription(subscription=sub_path)
                except NotFound:
                    # Create subscription
                    subscriber.create_subscription(name=sub_path, topic=topic_path)
                    print(f'Created subscription {sub_name}')


def auto_setup(
    survey='lvk', testid='test', teardown=False, confirmed=False, versiontag="O4", region="us-central1"
) -> None:
    """Create and setup GCP products required by the ``broker`` package.

    Args:
        survey (str): which astronomical survey the broker instance will
                      connect to. Controls the names of resources and the
                      behavior of functions that rely on schemas.
        testid (False or str): False: Use production resources.
                                str: Use test resources. (This string is
                                appended to the resource names.)
        teardown (bool): if True, delete resources rather than setting them up
        confirmed (bool): if True, assumes user has already confirmed settings
                          and tries not to ask again.

    """
    _do_not_delete_production_resources(survey=survey, testid=testid, teardown=teardown)
    if not confirmed:
        _confirm_options(survey, testid, teardown)

    setup_bigquery(survey=survey, testid=testid, teardown=teardown, versiontag=versiontag, region=region)
    setup_buckets(survey=survey, testid=testid, teardown=teardown, versiontag=versiontag, region=region)
    setup_pubsub(survey=survey, testid=testid, teardown=teardown)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # survey
    # when calling this script, use one of `--testid=<mytestid>` or `--production`
    parser.add_argument(
        '--survey',  # set testid = <mytestid>
        dest='survey',
        default='lvk',
        help='which astronomical survey the broker instance will connect to.\n',
    )
    # testid
    # when calling this script, use one of `--testid=<mytestid>` or `--production`
    parser.add_argument(
        '--testid',  # set testid = <mytestid>
        dest='testid',
        default='test',
        help='Setup testing resources tagged with this ID. Example useage `--testid=mytest`\n',
    )
    parser.add_argument(
        '--production',  # set testid = False
        dest='testid',
        action='store_false',
        default='test',
        help='Use production resources.\n',
    )
    # teardown
    parser.add_argument(
        "--teardown",
        dest='teardown',
        action='store_true',
        default=False,
        help="Delete resources rather than creating them.\n",
    )
    parser.add_argument(
        '--confirmed',  # set testid = False
        dest='confirmed',
        action='store_true',
        default=False,
        help="User has already confirmed settings; try not to ask again.\n",
    )
    parser.add_argument(
        '--versiontag',
        dest='versiontag',
        default='O4',
        help='Tag indicating Avro schema version. Appended to some resource names.\n',
    )
    parser.add_argument(
        '--region',
        dest='region',
        default='us-central1',
        help='GCP region for resource locations.\n',
    )
    known_args, __ = parser.parse_known_args()

    auto_setup(survey=known_args.survey,
               testid=known_args.testid,
               teardown=known_args.teardown,
               confirmed=known_args.confirmed,
               versiontag=known_args.versiontag,
               region=known_args.region,
               )
