#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""The ``schema_maps`` module loads and returns schema maps stored in
Cloud Storage.
"""

import os
from pathlib import Path
from typing import Optional, Union

from google.cloud import storage
from google.cloud.storage.blob import Blob
import yaml


# get project id from environment variable, else default to production project
# cloud functions use GCP_PROJECT
if "GCP_PROJECT" in os.environ:
    PROJECT_ID = os.getenv("GCP_PROJECT")
else:
    PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "ardent-cycling-243415")


def load_schema_map(
    survey: str,
    testid: str,
    schema: Optional[Union[Path, str]] = None,
) -> dict:
    """Return a dict mapping the survey's field names to an internal broker standard.

    Args:
        survey: Name of the survey associated with the broker instance.
                If `schema` is a `pathlib.Path`, `survey` is ignored
                (left as an arg for backward compatibility).
                Otherwise, it determines (in conjunction with `testid`) which GCS bucket
                the schema map will be loaded from. If `schema` is `None`,
                this will also determine which survey's schema map is returned.
        testid: If `schema` is a `pathlib.Path`, `testid` is ignored
                (left as an arg for backward compatibility).
                Otherwise, it determines (in conjunction with `survey`) which GCS bucket
                the schema map will be loaded from.
                If this is a bool, it must be False (indicating a production instance).
        schema: If this is a `pathlib.Path`: path to a local yaml file to be loaded.
                In this case, `survey` and `testid` are ignored.
                If this is a `str`: name of the survey who's schema map
                is to be loaded. It will be retrieved from a Cloud Storage bucket.
                If this is `None`, the schema map corresponding to `survey` will be
                will be retrieved from a Cloud Storage bucket.

    Returns:
        Dictionary mapping the survey's field names to an internal broker standard.
    """
    if not schema:
        # set schema to the survey name, map will be retrieved from a bucket
        schema = survey  # str

    if isinstance(schema, str):
        # download from storage bucket
        return _download_schema_map(survey, testid, schema)

    # else load from local file
    return load_yaml(schema)


def _download_schema_map(survey: str, testid: str, schema: str) -> dict:
    """Download the schema map from Cloud Storage and return as a dict.

    Args:
        survey: Name of the survey associated with the broker instance.
                Determines (in conjunction with `testid`) which GCS bucket
                the schema map will be loaded from. If `schema` is `None`,
                this will also determine which survey's schema map is returned.
        testid: Determines (in conjunction with `survey`) which GCS bucket
                the schema map will be loaded from.
                If this is a bool, it must be False (indicating a production instance).
        schema: Name of the survey who's schema map
                is to be loaded. It will be retrieved from a Cloud Storage bucket.

    Returns:
        Dictionary mapping the survey's field names to an internal broker standard.
    """
    # some setup
    bucket = _broker_bucket_name(survey, testid)
    schema = _schema_object_name(schema)
    client = storage.Client()

    # try to get the object from storage. blob = `None` if unsuccessful
    blob = client.bucket(bucket).get_blob(schema)  # 403 error (Forbidden) if not auth'd

    if not blob:
        # raise an error
        _ = client.get_bucket(bucket)  # 404 error (NotFound) if bucket doesn't exist
        raise ValueError(f"Bucket {bucket} exists but the object {schema} does not.")

    return load_yaml(blob)


def _broker_bucket_name(survey, testid):
    if testid in ["False", False]:
        return f'{PROJECT_ID}-{survey}-broker_files'
    else:
        return f'{PROJECT_ID}-{survey}-broker_files-{testid}'


def _schema_object_name(survey):
    return f'schema_maps/{survey}.yaml'


def load_yaml(fin: Union[Path, str, Blob]) -> dict:
    """Load a yaml file and return as a dict.

    Args:
        fin: Path-like or `google.cloud.storage.blob.Blob` object. Assumes yaml format.

    Returns:
        Dictionary mapping the survey's field names to an internal broker standard.
    """
    if isinstance(fin, Blob):
        with fin.open("rt") as f:
            return yaml.safe_load(f)  # dict

    with open(fin, "rb") as f:
        return yaml.safe_load(f)  # dict


def get_value(key: str, alert_dict: dict, schema_map: dict) -> Union[int, str]:
    """Return the alert_dict value corresponding to schema_map and key."""
    fullkey = schema_map.get(key)

    if isinstance(fullkey, str):
        return alert_dict.get(fullkey)

    elif isinstance(fullkey, list):
        if len(fullkey) == 1:
            return alert_dict.get(fullkey[0])

        elif len(fullkey) == 2:
            return alert_dict.get(fullkey[0]).get(fullkey[1])

        elif len(fullkey) == 3:
            return alert_dict.get(fullkey[0]).get(fullkey[1]).get(fullkey[2])


def get_key(key: str, schema_map: dict) -> Union[int, str]:
    """Return the key or final element in list corresponding to schema_map and key."""
    fullkey = schema_map.get(key)

    if isinstance(fullkey, str):
        return fullkey

    elif isinstance(fullkey, list):
        return fullkey[-1]
