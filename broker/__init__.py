#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""A ZTF data broker"""

import os as _os
from warnings import warn as _warn

from . import alert_ingestion, gcp_setup, ztf_archive

if 'BROKER_PROJ_ID' not in _os.environ:
    _warn('GCP project id is not set in the current environment. Please see '
          'documentation for instructions on setting BROKER_PROJ_ID')
