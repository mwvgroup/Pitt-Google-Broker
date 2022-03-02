#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""A cloud-based, alert distribution service designed to provide near
real-time processing of message streams from astronomical surveys.
"""

import os
from warnings import warn

if "PGB_OFFLINE" not in os.environ:
    from google.cloud import logging as cloud_logging

    cloud_logging.Client().setup_logging()

for _var in ("GOOGLE_CLOUD_PROJECT", "GOOGLE_APPLICATION_CREDENTIALS"):
    if _var not in os.environ:
        warn(
            f"Environmental variable ``{_var}`` not found. "
            f"Some package functionality may not be available."
        )

__version__ = "development"
