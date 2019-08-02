#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This file provides tests for the ``broker.ztf_archive`` module."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import types
from broker import ztf_archive as ztfa

temp_dir = TemporaryDirectory()

# Metadata about the data downloaded by this test
TEST_DATE = (2018, 6, 26)
TEST_RELEASE = '20180626'
NUM_TEST_ALERTS = 23553


def setUpModule():
    """Download data to the local machine"""

    temp_dir_path = Path(temp_dir.name)
    ztfa._parse_data.DATA_DIR = temp_dir_path
    ztfa._download_data.DATA_DIR = temp_dir_path
    ztfa._download_data.ALERT_LOG = temp_dir_path / 'alert_log.txt'

    try:
        ztfa.download_data_date(*TEST_DATE)

    except:
        temp_dir.cleanup()
        raise


def tearDownModule():
    """Delete downloaded data from the local machine"""

    temp_dir.cleanup()


class DownloadLogging(TestCase):
    """Test the logging of downloaded ZTF data."""

    def test_alert_list(self):
        """Test ``get_local_alert_list``

        Check the correct number of alerts are returned
        """

        alert_list = list(ztfa.get_local_alerts())
        self.assertEqual(len(alert_list), NUM_TEST_ALERTS)

    def test_local_release_list(self):
        """Test ``get_local_release_list``

        Check ``get_local_release_list`` returns a generator
        Check correct releases are in that list
        """

        releases = ztfa.get_local_releases()
        self.assertIsInstance(releases, types.GeneratorType)
        self.assertSequenceEqual(
            [TEST_RELEASE], list(releases),
            'Expected release not in local release list')

    def test_local_alert_list(self):
        """Test ``get_local_alert_list``

        Check the return a generator
        Check first entry is an integer
        """

        alerts = ztfa.get_local_alerts()
        self.assertIsInstance(alerts, types.GeneratorType)
        self.assertIsInstance(next(alerts), int)


class DataParsing(TestCase):
    """Test the parsing of ZTF data."""

    def test_iter_alerts(self):
        """Test ``iter_alerts`` returns an appropriately sized list of dicts"""

        alert = next(ztfa.iter_alerts())
        self.assertIsInstance(alert, dict)

        alert_list = next(ztfa.iter_alerts(1))
        self.assertIsInstance(alert_list, list)
        self.assertIsInstance(alert_list[0], dict)

        alert_list = next(ztfa.iter_alerts(10))
        self.assertEqual(len(alert_list), 10)

    def test_get_alert_data(self):
        """Test ``get_alert_data`` returns the correct data type."""

        test_alert = next(ztfa.get_local_alerts())

        test_data_dict = ztfa.get_alert_data(test_alert)
        self.assertIsInstance(test_data_dict, dict)

        test_data_bytes = ztfa.get_alert_data(test_alert, raw=True)
        self.assertIsInstance(test_data_bytes, bytes)
