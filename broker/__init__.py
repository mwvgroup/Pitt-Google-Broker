#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""A cloud-based, alert distribution service designed to provide near
real-time processing for alerts from the  Zwicky Transient Facility (ZTF) and
the Large Synoptic Survey Telescope (LSST).
"""

import os
from warnings import warn

from google.cloud import logging as cloud_logging

try:
    cloud_logging.Client().setup_logging()

except Exception as e:
    warn(f'Could not package logging to GCP: {e}')

required_vars = ('GOOGLE_CLOUD_PROJECT', 'GOOGLE_APPLICATION_CREDENTIALS')
missing_vars = [v for v in required_vars if v not in os.environ]
if missing_vars:
    warn(
        f'Environmental variables ``{missing_vars}`` not found. '
        f'Some package functionality may not be available.'
    )

del required_vars
del missing_vars

__version__ = 'development'
