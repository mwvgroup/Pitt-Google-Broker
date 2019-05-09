#!/usr/bin/env python3.7
# -*- coding: UTF-8 -*-

"""This module downloads and provides access to ZTF alerts from the 24hr ZTF
alerts archive.

Examples:
>>> from broker import ztf_archive as ztfa
>>> from matplotlib import pyplot as plt
>>>
>>> # Download recent data from the ZTF archive.
>>> # Note: Daily releases can be as large as several Gb
>>> ztfa.download_data()
>>>
>>> # Retrieve the number of daily releases that have been downloaded
>>> print(ztfa.get_number_local_releases())
>>>
>>> # Retrieve the number of alerts that have been downloaded
>>> # from all combined daily releases.
>>> print(ztfa.get_number_local_alerts())
>>>
>>> # Iterate through local alert data
>>> for alert in ztfa.iter_alerts():
>>>     alert_id = alert['candid']
>>>     print(alert_id)
>>>     break
>>>
>>> # Get data for a specific alert id
>>> alert_data = ztfa.get_alert_data(alert_id)
>>> print(alert_data)
>>>
>>> # Plot stamp images for alert data
>>> from matplotlib import pyplot as plt
>>>
>>> fig = plot_stamps(alert_data)
>>> plt.show()
"""

from ._download_data import download_data
from ._download_data import get_number_local_alerts
from ._download_data import get_number_local_releases
from ._parse_data import get_alert_data
from ._parse_data import iter_alerts
from ._parse_data import plot_stamps
