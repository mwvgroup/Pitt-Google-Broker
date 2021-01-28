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

   testid = 'mytest'
   teardown = False

   # Run individual tasks
   gcp_setup.setup_bigquery(testid=testid, teardown=teardown)
   gcp_setup.setup_buckets(testid=testid, teardown=teardown)
   gcp_setup.setup_pubsub(testid=testid, teardown=teardown)

   # Run all tasks
   gcp_setup.auto_setup(testid=testid, teardown=teardown)


Module Documentation
--------------------
"""

import argparse
import os
from pathlib import Path
import sys
from warnings import warn
from google.api_core.exceptions import NotFound
from google.cloud import bigquery, pubsub_v1, logging, storage

PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')


def _resources(service, testid='test'):
    """ Names the GCP resources to be setup/torn down.

    Args:
        service (str): which GCP service resources to return.
        testid (False or str): False: Use production resources.
                                str: Use test resources. (This string is
                                appended to the resource names.)
    """

    if service == 'BQ':
        datasets = ['ztf_alerts', ]

        # append the testid
        if testid is not False:
            datasets = [f'{d}_{testid}' for d in datasets]
        return datasets

    if service == 'GCS':
        buckets = {  # '<bucket-name>': ['<file-name to upload>',]
                f'{PROJECT_ID}-broker_files': [],
                f'{PROJECT_ID}_dataflow': [],
                f'{PROJECT_ID}_testing_bucket':
                    ['ztf_3.3_validschema_1154446891615015011.avro'],
                f'{PROJECT_ID}_ztf_alert_avro_bucket': [],
                f'{PROJECT_ID}_ztf-sncosmo': [],
        }
        # Files are currently expected to reside in the
        # ``../../tests/test_alerts`` directory.
        # Note that if you want to upload an entire directory, it is easier to
        # use the commandline tool `gsutil`. See ``setup_broker.sh``.

        # append the testid
        if testid is not False:
            buckets = {f'{key}-{testid}': val for key, val in buckets.items()}
        return buckets

    if service == 'PS':
        topics = {  # '<topic_name>': ['<subscription_name>', ]
                'ztf_alert_avro_bucket':
                    ['ztf_alert_avro_bucket-counter'],
                'ztf_alert_data':
                    ['ztf_alert_data-counter', 'ztf_alert_data-test_seeder', ],
                'ztf_exgalac_trans':
                    ['ztf_exgalac_trans-counter'],
                'ztf_salt2':
                    ['ztf_salt2-counter'],
        }

        # append the testid
        if testid is not False:
            topics = {f'{key}-{testid}': val for key, val in topics.items()}
            for key, val in topics.items():
                topics[key] = [f'{v}-{testid}' for v in val]
        return topics

def _do_not_delete_production_resources(testid='test', teardown=True):
    """ If the user is requesting to delete resources used in production,
    throw an error.

    Args:
        testid (False or str): False: Use production resources.
                                str: Use test resources. (This string is
                                appended to the resource names.)
        teardown (bool): if True, delete resources rather than setting them up
    """
    if teardown and not testid:
        msg = (f'\nReceived teardown={teardown} and testid={testid}.\n'
               f'Exiting to prevent the teardown of production resources.\n')
        raise ValueError(msg)

def _confirm_options(testid, teardown):
    """ Require the user to confirm options that determine
    the behavior of this script.

    Args:
        testid (False or str): False: Use production resources.
                                str: Use test resources. (This string is
                                appended to the resource names.)
        teardown (bool): if True, delete resources rather than setting them up
    """
    behavior = 'DELETE' if teardown else 'SETUP'
    if not testid:
        resources = 'PRODUCTION resources'
    else:
        resources = f'TEST resources tagged with "{testid}"'
    msg = (f'\nsetup_gcp will {behavior} all bq, gcs, and ps {resources}.\n'
            'Continue?  [Y/n]:  ')
    continue_with_setup = input(msg) or 'Y'

    if continue_with_setup not in ['Y', 'y']:
        msg = 'Exiting setup_gcp.py'
        sys.exit(msg)


def setup_bigquery(testid='test', teardown=False) -> None:
    """Create the necessary Big Query datasets if they do not already exist
    Args:
        testid (False or str): False: Use production resources.
                                str: Use test resources. (This string is
                                appended to the resource names.)
        teardown (bool): if True, delete resources rather than setting them up

    New datasets include:
      ``ztf_alerts``
    """
    _do_not_delete_production_resources(testid=testid, teardown=teardown)

    datasets = _resources('BQ', testid=testid)
    bigquery_client = bigquery.Client()

    for dataset in datasets:
        if teardown:
            # Delete dataset
            kwargs = {'delete_contents':True, 'not_found_ok':True}
            bigquery_client.delete_dataset(dataset, **kwargs)
            print(f'Deleted dataset {dataset}')
        else:
            # Create dataset
            bigquery_client.create_dataset(dataset, exists_ok=True)
            print(f'Created dataset (skipped if previously existed): {dataset}')

def setup_buckets(testid='test', teardown=False) -> None:
    """Create new storage buckets and upload testing files.
    Files are expected to reside in the ``tests/test_alerts`` directory.

    Args:
        testid (False or str): False: Use production resources.
                                str: Use test resources. (This string is
                                appended to the resource names.)
        teardown (bool): if True, delete resources rather than setting them up
    """
    _do_not_delete_production_resources(testid=testid, teardown=teardown)

    buckets = _resources('GCS', testid=testid)
    storage_client = storage.Client()

    for bucket_name, files in buckets.items():
        #-- Create or delete buckets
        try:
            bucket = storage_client.get_bucket(bucket_name)
        except NotFound:
            if not teardown:
                # Create bucket
                storage_client.create_bucket(bucket_name)
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

        #-- Upload any files
        if not teardown and len(files)>0:
            bucket = storage_client.get_bucket(bucket_name)
            for filename in files:
                blob = bucket.blob(filename)
                inpath = Path('../../tests/test_alerts') / filename
                with inpath.open('rb') as infile:
                    blob.upload_from_file(infile)
                print(f'Uploaded {inpath} to {bucket_name}')

def setup_pubsub(testid='test', teardown=False) -> None:
    """ Create new Pub/Sub topics and subscriptions.
    Args:
        testid (False or str): False: Use production resources.
                                str: Use test resources. (This string is
                                appended to the resource names.)
        teardown (bool): if True, delete resources rather than setting them up
    """
    _do_not_delete_production_resources(testid=testid, teardown=teardown)

    topics = _resources('PS', testid=testid)
    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()

    for topic, subscriptions in topics.items():

        #-- Create or delete topic
        topic_path = publisher.topic_path(PROJECT_ID, topic)
        if teardown:
            # Delete topic
            try:
                publisher.delete_topic(request={"topic": topic_path})
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

        #-- Create or delete subscriptions
        for sub_name in subscriptions:
            sub_path = subscriber.subscription_path(PROJECT_ID, sub_name)
            if teardown:
                # Delete subscription
                try:
                    subscriber.delete_subscription(request={"subscription": sub_path})
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

def auto_setup(testid='test', teardown=False) -> None:
    """Create and setup GCP products required by the ``broker`` package.

    Args:
        testid (False or str): False: Use production resources.
                                str: Use test resources. (This string is
                                appended to the resource names.)
        teardown (bool): if True, delete resources rather than setting them up

    """
    _do_not_delete_production_resources(testid=testid, teardown=teardown)
    _confirm_options(testid, teardown)  # make user confirm script behavior

    setup_bigquery(testid=testid, teardown=teardown)
    setup_buckets(testid=testid, teardown=teardown)
    setup_pubsub(testid=testid, teardown=teardown)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # teardown
    parser.add_argument(
        "--teardown",
        dest='teardown',
        action='store_true',
        default=False,
        help="Delete resources rather than creating them.\n",
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

    known_args, __ = parser.parse_known_args()

    auto_setup(testid=known_args.testid, teardown=known_args.teardown)
