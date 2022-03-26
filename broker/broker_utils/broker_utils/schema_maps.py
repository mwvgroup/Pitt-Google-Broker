#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``schema_maps`` module loads and returns schema maps stored in
Cloud Storage.
"""

import os

# from typing import List, Tuple, Optional, Union, Generator
from typing import Optional
import yaml
from google.cloud import storage


# get project id from environment variable, else default to production project
# cloud functions use GCP_PROJECT
if "GCP_PROJECT" in os.environ:
    PROJECT_ID = os.getenv("GCP_PROJECT")
else:
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "ardent-cycling-243415")


def load_schema_map(survey: str, testid: str, schema: Optional[str] = None) -> dict:
    """
    Args:
        survey: Name of the survey associated with the broker instance.
                Along with the `testid`, this determines which GCS bucket the
                schema map will be loaded from. If `schema` is not provided,
                this will also determine which schema map is returned.
        testid: Name of the testid associated with the broker instance.
                Along with the `survey`, this determines which GCS bucket the
                schema map will be loaded from.
                If this is a bool, it must be False (indicates a production instance).
        schema: Survey name of the schema to be returned. If not provided, the
                map corresponding to `survey` will be returned.
    """
    if schema is None: schema = survey

    # load the map from the yaml in cloud storage
    broker_bucket_name = _broker_bucket_name(survey, testid)
    schema_file_name = _schema_file_name(schema)
    blob = storage.Client().bucket(broker_bucket_name).get_blob(schema_file_name)
    with blob.open("rt") as f:
        schema_map = yaml.safe_load(f)  # dict

    return schema_map


def _broker_bucket_name(survey, testid):
    if testid in ["False", False]:
        return f'{pgb_project_id}-{survey}-broker_files'
    else:
        return f'{pgb_project_id}-{survey}-broker_files-{testid}'


def _schema_file_name(survey):
    return f'schema_maps/{survey}.yaml'
