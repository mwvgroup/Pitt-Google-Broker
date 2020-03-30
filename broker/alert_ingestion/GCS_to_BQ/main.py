#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This module is intended to be deployed as a Google Cloud Function so that it
listens to a Google Cloud Storage (GCS) bucket. When a new file is detected in
the bucket (Avro file format expected), it will automatically load it into a
BigQuery (BQ) table. This code borrows heavily from
https://cloud.google.com/bigquery/docs/loading-data-cloud-storage-avro.

Usage Example
-------------

First, check that the buckets, datasets, and tables referenced in the
``bucket2table`` dictionary (below) point to the appropriate Google Cloud
Platform (GCP) resources. (These should have been initialized during the GCP
setup, see
https://pitt-broker.readthedocs.io/en/latest/installation.html#setting-up-gcp.)
Buckets and datasets must exist (with appropriate permissions) prior to
invoking this module. Tables are created automatically and on-the-fly if they
don't already exist.

Deploy the ``stream_GCS_to_BQ`` function by running the following command in
the directory where this module is located. Be sure to replace
``<YOUR_TRIGGER_BUCKET_NAME>`` with the name of the GCS bucket that this
function should listen to. For more information, see
https://cloud.google.com/functions/docs/calling/storage.

.. code-block:: bash
   :linenos:

   gcloud functions deploy stream_GCS_to_BQ --runtime python37 --trigger-resource <YOUR_TRIGGER_BUCKET_NAME> --trigger-event google.storage.object.finalize

The script ``broker/deploy_cloudfnc.sh`` automates the deployment.

Module Documentation
--------------------
"""

import logging
import os
from google.cloud import bigquery

log = logging.getLogger(__name__)
BQ = bigquery.Client()

# The bucket2table dictionary determines which BQ table the alert data will be
# uploaded to based on which GCS bucket the alert Avro file is stored in.
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')
streaming_bucket = '_'.join([PROJECT_ID, 'alert_avro_bucket'])
testing_bucket = '_'.join([PROJECT_ID, 'testing_bucket'])
bucket2table = {
    streaming_bucket: { 'BQ_DATASET': 'ztf_alerts',
                        'BQ_TABLE': 'alerts'
    },
    testing_bucket: {   'BQ_DATASET': 'testing_dataset',
                        'BQ_TABLE': 'test_GCS_to_BQ'
    }
}


def stream_GCS_to_BQ(data: dict, context: dict) -> str:
    """This function is executed whenever a file is added to Cloud Storage.
    Most of this function is taken from
    https://cloud.google.com/bigquery/docs/loading-data-cloud-storage-avro
    """

    # Create the job
    bucket_name = data['bucket']
    file_name = data['name']
    job_config = bigquery.LoadJobConfig()
    job_config.write_disposition = bigquery.WriteDisposition.WRITE_APPEND
    job_config.source_format = bigquery.SourceFormat.AVRO
    uri = f'gs://{bucket_name}/{file_name}'
    try:
        BQ_TABLE_ID = get_BQ_TABLE_ID(bucket_name)
    except KeyError as e:
        msg = (f'GCS bucket {e} does not have an associated BigQuery dataset '
               f'configured for the `stream_GCS_to_BQ` Cloud Function. '
               f'Data in {file_name} cannot be uploaded to BigQuery.')
        log.error(msg)
        return f'GCS bucket {e} not configured'  # used in testing

    # API request
    load_job = BQ.load_table_from_uri(uri, BQ_TABLE_ID, job_config=job_config)
    msg = (f'Starting stream_GCS_to_BQ job {load_job.job_id} | '
           f'file name: {file_name} | '
           f'GCS Bucket: {bucket_name} | '
           f'BQ Table ID: {BQ_TABLE_ID}'
           )
    log.info(msg)

    # Run the job
    load_job.result()  # Start job, wait for it to complete, get the result

    return load_job.error_result


def get_BQ_TABLE_ID(bucket_name: str) -> str:
    """ Returns the ID of the BQ table associated with the GCS bucket_name.
    """

    BQ_DATASET = bucket2table[bucket_name]['BQ_DATASET']
    BQ_TABLE = bucket2table[bucket_name]['BQ_TABLE']
    BQ_TABLE_ID = '.'.join([PROJECT_ID, BQ_DATASET, BQ_TABLE])

    return BQ_TABLE_ID
