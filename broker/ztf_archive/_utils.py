#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""General utilities for common tasks performed across the
``broker.ztf_archive`` module.
"""

import os
from pathlib import Path


def get_ztf_data_dir() -> Path:
    """Return the directory path where local ZTF alerts are stored

    Returns:
        A ``Path`` object
    """

    if 'PGB_DATA_DIR' in os.environ:
        directory = Path(os.environ['PGB_DATA_DIR']) / 'ztf_archive'

    else:
        directory = Path(__file__).resolve().parent / 'ztf_archive/data'

    directory.mkdir(exist_ok=True, parents=True)
    return directory
