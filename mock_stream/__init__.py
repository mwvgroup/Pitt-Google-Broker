#!/usr/bin/env python2.7
# -*- coding: UTF-8 -*-

"""This module downloads and provides access to sample ZTF alerts."""

import warnings as _warnings
import json as _json

from ._download_data import download_data
from ._download_data import get_number_local_alerts
from ._download_data import number_local_releases
from ._parse_data import get_alert_data
from ._parse_data import iter_alerts
from ._parse_data import plot_stamps

from kafka import KafkaProducer as _KafkaProducer

if number_local_releases() == 0:
    _warnings.warn('No local ZTF data available. Run `download_data()`.')


def prime_alerts(max_alerts=10, servers=['localhost:9092']):
    """Load locally available ZTF alerts into the Kafka stream

    Args:
        max_alerts (int): Number of maximum alerts to load (Default = 10)
        servers   (list): List of Kafka servers to connect to.
    """

    _value_serializer = lambda v: _json.dumps(v).encode('utf-8')
    producer = _KafkaProducer(value_serializer=_value_serializer,
                              bootstrap_servers=servers,
                              compression_type='gzip')

    for i, alert in enumerate(iter_alerts()):
        if i >= max_alerts:
            break

        del alert['cutoutScience']
        del alert['cutoutTemplate']
        del alert['cutoutDifference']
        producer.send('Demo-Topic', alert)

# from kafka import KafkaConsumer
# consumer = _KafkaConsumer('Demo-Topic', bootstrap_servers=['localhost:9092'])
