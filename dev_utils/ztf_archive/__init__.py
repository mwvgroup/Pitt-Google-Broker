#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""The ``ztf_archive`` module downloads and provides access to ZTF alerts from
the ZTF Public Alerts Archive.

Usage Example
-------------

.. code-block:: python
   :linenos:

   from broker import ztf_archive as ztfa

   # Get a list of files available on the ZTF Alerts Archive
   md5_table = ztfa.get_remote_md5_table()
   print(md5_table)

   # Download data from the ZTF archive for a given day.
   ztfa.download_data_date(year=2018, month=6, day=26)

   # Download the most recent day of available data
   ztfa.download_recent_data(max_downloads=1)

   # Delete any data downloaded to your local machine
   ztfa.delete_local_data()

Module Documentation
--------------------
"""

import os as _os
from warnings import warn as _warn

from ._download_data import *
from ._parse_data import *

if "PGB_DATA_DIR" not in _os.environ:
    _warn(
        "The ZTF data directory not set in the current environment. "
        "This can lead to duplicate data being downloaded to your machine. "
        "Please see the documentation for instructions on setting"
        "``PGB_DATA_DIR`` in your environment"
    )
