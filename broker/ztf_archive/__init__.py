#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""This module downloads and provides access to sample ZTF alerts."""

from ._download_data import download_data
from ._download_data import get_number_local_alerts
from ._download_data import number_local_releases
from ._parse_data import get_alert_data
from ._parse_data import iter_alerts
from ._parse_data import plot_stamps
