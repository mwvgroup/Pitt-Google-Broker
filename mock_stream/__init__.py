#!/usr/bin/env python2.7
# -*- coding: UTF-8 -*-

"""This module downloads and provides access to sample ZTF alerts."""

from ._download_data import download_data
from ._download_data import get_number_local_alerts
from ._download_data import number_local_releases
from ._parse_data import get_alert_data
from ._parse_data import iter_alerts
from ._parse_data import plot_stamps

from kafka import KafkaProducer as _KafkaProducer
from kafka import KafkaConsumer as _KafkaConsumer

producer = _KafkaProducer(bootstrap_servers=['localhost:9092'])
consumer = _KafkaConsumer('Demo-Topic', bootstrap_servers=['localhost:9092'])

for i, alert in iter_alerts():
    if i >= 10:
        break

    producer.send('Demo-Topic', alert)
