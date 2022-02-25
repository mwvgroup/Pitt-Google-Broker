#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
"""Apache Beam IO transforms for connecting to Pitt-Google Broker data.
Most of these are essentially wrappers for Beam's native GCP IO transforms.
"""

import apache_beam as beam
from apache_beam.io import ReadFromPubSub

from dev_utils.pub_sub_client import decode_streams


class extract_ztf_alert_data(DoFn):
    """
    """
    def __init__(self, return_format='dict', strip_cutouts=True):
        super().__init__()
        self.return_format = return_format
        self.strip_cutouts = strip_cutouts

    def process(self, msg):
        kwargs = {
            'return_format': self.return_format,
            'strip_cutouts': self.strip_cutouts,
        }
        return [decode_streams.ztf_alert_data(msg, **kwargs)]


class ReadFromPubSubPGB(beam.PTransform):

    def __init__(self, source, source_configs):
        """
        Args:
            source (str): Pub/Sub topic id
            source_configs (dict):
        """
        super().__init__()
        self.source = source
        self.source_configs = source_configs

    def expand(self, alert_PColl):
        #-- Read from PS and extract data as dicts
        PSin = (pipeline | 'ReadFromPubSub' >>
                ReadFromPubSub(topic=self.source))

        if self.source == 'ztf_alert_data':
            alertDicts = (PSin | 'ExtractAlertDict' >>
                          beam.ParDo(extract_ztf_alert_data(**self.source_configs)))
            return alertDicts

        elif self.source == 'salt2':
            return
