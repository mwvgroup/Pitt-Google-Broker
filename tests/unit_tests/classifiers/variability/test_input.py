#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This file provides tests for the SuperNNova module. This includes loading simulated data from a local directory,
ensuring that the _create_dataframe() function works as expected, and that the _format_for_classifier() function
returns the expected output.
"""

import os
import json
import pandas as pd
from pathlib import Path
from pittgoogle import Alert


dataset_id = "testing_dataset"
max_alert_size = 150000  # for creating temporary files
test_alerts_dir = Path(__file__).parent / "test_alerts"
test_alert_path = {
    "lsst_10.0": test_alerts_dir / "lsst_10.0_1154308030015010004.avro",
}


def load_test_alert(path="tests/test_alert.json"):
    with open(path, "r") as f:
        data = json.load(f)
    # create an Alert object
    alert = Alert.from_dict(data, schema_name="default")
    return alert


def test_create_dataframe():
    """_create_dataframe should return a DataFrame with expected columns"""
    alert_lite = load_test_alert()
    alert_lite_dict = alert_lite.dict["alert_lite"]
    df = _create_dataframe(alert_lite_dict)

    # df should contain the following columns only
    expected_columns = ["psfFlux", "psfFluxErr", "midpointMjdTai", "band"]
    assert all(col in df.columns for col in expected_columns)

    # df should contain all rows from diaSource + prvDiaSources + prvDiaForcedSources
    expected_rows = 1
    if alert_lite_dict.get("prvDiaSources"):
        expected_rows += len(alert_lite_dict["prvDiaSources"])
    if alert_lite_dict.get("prvDiaForcedSources"):
        expected_rows += len(alert_lite_dict["prvDiaForcedSources"])
    assert len(df) == expected_rows


def test_format_for_snn():
    """_format_for_classifier should produce DataFrame with correct SuperNNova columns"""
    alert = load_test_alert()
    df = _format_for_classifier(alert)

    # df should contain the following columns only
    expected_columns = ["SNID", "FLT", "MJD", "FLUXCAL", "FLUXCALERR"]
    assert all(col in df.columns for col in expected_columns)

    # SNID should be repeated for every row
    snid = alert.dict["alert_lite"]["diaObject"]["diaObjectId"]
    assert all(df["SNID"] == snid)

    # field values should be the expected dtype
    assert pd.api.types.is_numeric_dtype(df["SNID"])
    assert pd.api.types.is_numeric_dtype(df["MJD"])
    assert pd.api.types.is_string_dtype(df["FLT"])
    assert pd.api.types.is_numeric_dtype(df["FLUXCAL"])
    assert pd.api.types.is_numeric_dtype(df["FLUXCALERR"])


def test_format_for_upsilon():
    """_format_for_classifier should produce DataFrame with correct SuperNNova columns"""
    alert = load_test_alert()
    df = _format_for_classifier(alert)

    # df should contain the following columns only
    expected_columns = ["SNID", "FLT", "MJD", "FLUXCAL", "FLUXCALERR"]
    assert all(col in df.columns for col in expected_columns)

    # SNID should be repeated for every row
    snid = alert.dict["alert_lite"]["diaObject"]["diaObjectId"]
    assert all(df["SNID"] == snid)

    # field values should be the expected dtype
    assert pd.api.types.is_numeric_dtype(df["SNID"])
    assert pd.api.types.is_numeric_dtype(df["MJD"])
    assert pd.api.types.is_string_dtype(df["FLT"])
    assert pd.api.types.is_numeric_dtype(df["FLUXCAL"])
    assert pd.api.types.is_numeric_dtype(df["FLUXCALERR"])
