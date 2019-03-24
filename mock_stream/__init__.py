#!/usr/bin/env python2.7
# -*- coding: UTF-8 -*-

"""This module downloads and provides access to sample ZTF alerts.

To create a consumer and populate the alert stream:

  >>> from kafka import KafkaConsumer
  >>> consumer = KafkaConsumer('Demo-Topic', bootstrap_servers=['localhost:9092'])
  >>>
  >>> from mock_stream import prime_alerts
  >>> prime_alerts()
"""

import warnings as _warnings

from ._download_data import download_data
from ._download_data import get_number_local_alerts
from ._download_data import number_local_releases
from ._parse_data import get_alert_data
from ._parse_data import iter_alerts
from ._parse_data import plot_stamps

from kafka import KafkaProducer as _KafkaProducer

if number_local_releases() == 0:
    _warnings.warn('No local ZTF data available. Run `download_data()`.')

producer = None  # Placeholder variable


def prime_alerts(max_alerts=100, servers=['localhost:9092']):
    """Load locally available ZTF alerts into the Kafka stream

    Args:
        max_alerts (int): Number of maximum alerts to load (Default = 100)
        servers   (list): List of Kafka servers to connect to
                              (Default = ['localhost:9092']).
    """

    global producer
    producer = _KafkaProducer(bootstrap_servers=servers)

    print('Staging messages...')
    for i, alert in enumerate(iter_alerts(raw=True)):
        if i >= max_alerts:
            break

        producer.send('ztf-stream', alert)

    print('Waiting for messages to be delivered...')
    producer.flush()
