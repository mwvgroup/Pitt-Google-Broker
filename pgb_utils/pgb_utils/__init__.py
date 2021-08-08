#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""Tools to facilitate interaction with Pitt-Google Broker data products
and services.
"""

import pkg_resources  # part of setuptools
import os as _os
from warnings import warn as _warn

from . import bigquery, figures, pubsub, utils


__version__ = pkg_resources.require("pgb_utils")[0].version


env_vars = ['GOOGLE_CLOUD_PROJECT', 'GOOGLE_APPLICATION_CREDENTIALS']
for var in env_vars:
    if var not in _os.environ:
        _warn(
            f'The environment variable {var} is not set. '
            'This may impact your ability to connect to your '
            'Google Cloud Platform project.'
        )
