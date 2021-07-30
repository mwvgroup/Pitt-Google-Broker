#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``gcp_utils`` module contains common functions used to interact with
GCP resources.
"""

from google.cloud import bigquery, storage
from typing import List, Optional

pgb_project_id = 'ardent-cycling-243415'



def bq_insert_rows(table_id: str, rows: List[dict]):
    """
    Args:
        table_id:   Identifier for the BigQuery table in the form
                    {dataset}.{table}. For example, 'ztf_alerts.alerts'.
        rows:       Data to load in to the table. Keys must include all required
                    fields in the schema. Keys which do not correspond to a
                    field in the schema are ignored.
    """
    bq_client = bigquery.Client(project=pgb_project_id)
    table = bq_client.get_table(table_id)
    errors = bq_client.insert_rows(table, rows)


def cs_download_file(localdir: str, bucket_id: str, filename: Optional[str] = None):
    """
    Args:
        localdir:   Path to local directory where file(s) will be downloaded to.
        bucket_id:  Name of the GCS bucket, not including the project ID.
                    For example, pass 'ztf-alert_avros' for the bucket
                    'ardent-cycling-243415-ztf-alert_avros'.
        filename:   Name or prefix of the file(s) in the bucket to download.
    """
    # connect to the bucket and get an iterator that finds blobs in the bucket
    storage_client = storage.Client(pgb_project_id)
    bucket_name = f'{pgb_project_id}-{bucket_id}'
    print(f'Connecting to bucket {bucket_name}')
    bucket = storage_client.get_bucket(bucket_name)
    blobs = storage_client.list_blobs(bucket, prefix=filename)  # iterator

    # download the files
    for blob in blobs:
        local_path = f'{localdir}/{blob.name}'
        blob.download_to_filename(local_path)
        print(f'Downloaded {local_path}')

def cs_upload_file(local_file: str, bucket_id: str, bucket_filename: Optional[str] = None):
    """
    Args:
        local_file: Path of the file to upload.
        bucket_id:  Name of the GCS bucket, not including the project ID.
                    For example, pass 'ztf-alert_avros' for the bucket
                    'ardent-cycling-243415-ztf-alert_avros'.
        bucket_filename:    String to name the file in the bucket. If None,
                            bucket_filename = local_filename.
    """
    if bucket_filename is None:
        bucket_filename = local_file.split('/')[-1]

    # connect to the bucket
    storage_client = storage.Client(pgb_project_id)
    bucket_name = f'{pgb_project_id}-{bucket_id}'
    print(f'Connecting to bucket {bucket_name}')
    bucket = storage_client.get_bucket(bucket_name)

    # upload
    blob = bucket.blob(bucket_filename)
    blob.upload_from_filename(local_file)
    print(f'Uploaded {local_file} as {bucket_filename}')
