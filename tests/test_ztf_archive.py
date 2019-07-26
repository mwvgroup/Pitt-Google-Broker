#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This file provides tests for the ``broker.ztf_archive`` module."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from broker import ztf_archive as ztfa

temp_dir = TemporaryDirectory()

# Metadata about the data downloaded by this test
TEST_DATE = (2018, 6, 26)
TEST_FILE_NAME = 'ztf_public_20180626.tar.gz'
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

        num_downloaded_alerts = len(ztfa.get_local_alert_list())
        self.assertEqual(num_downloaded_alerts, NUM_TEST_ALERTS)

    def test_local_release_list(self):
        """Test ``get_local_release_list``

        Check ``get_local_release_list`` returns a list
        Check correct file name(s) are in that list
        Check first list entry is strings and ends with `.tar.gz`
        """

        release_list = ztfa.get_local_release_list()
        self.assertIsInstance(release_list, list)
        self.assertSequenceEqual(
            [TEST_FILE_NAME], release_list,
            'Expected filename not in local release list')

        self.assertTrue(release_list[0].endswith('.tar.gz'))

    def test_local_alert_list(self):
        """Test ``get_local_alert_list``

        Check the return a list
        Check the list is not empty
        Check first entry is an integer
        """

        alert_list = ztfa.get_local_alert_list()
        self.assertIsInstance(alert_list, list)
        self.assertTrue(alert_list)
        self.assertIsInstance(alert_list[0], int)


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

        test_alert = ztfa.get_local_alert_list()[0]

        test_data_dict = ztfa.get_alert_data(test_alert)
        self.assertIsInstance(test_data_dict, dict)

        test_data_bytes = ztfa.get_alert_data(test_alert, raw=True)
        self.assertIsInstance(test_data_bytes, bytes)
