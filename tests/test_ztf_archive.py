#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This file provides tests for the ``broker.ztf_archive`` module."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from broker import ztf_archive as ztfa


class DataDownload(TestCase):
    """Test the downloading and parsing of ZTF data."""

    @classmethod
    def setUpClass(cls):
        """Create a temporary directory and download alerts from 6/26/2018"""

        cls.temp_dir = TemporaryDirectory()
        temp_dir_path = Path(cls.temp_dir.name)
        ztfa._parse_data.ZTF_DATA_DIR = temp_dir_path
        ztfa._download_data.ZTF_DATA_DIR = temp_dir_path
        ztfa._download_data.ALERT_LOG = temp_dir_path / 'alert_log.txt'

        # Metadata about the data downloaded by this test
        test_date = (2018, 6, 26)
        cls.file_name = 'ztf_public_20180626.tar.gz'
        cls.expected_num_alerts = 23553

        try:
            ztfa.download_data_date(*test_date)

        except:
            cls.temp_dir.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        """Remove any data downloaded during testing"""

        cls.temp_dir.cleanup()

    def test_download_date(self):
        """Test ``download_data_date``

        Check the downloaded filename is in ztfa.get_local_release_list()
        Check the correct number of alerts were unzipped
        """

        success = self.file_name in ztfa.get_local_release_list()
        self.assertTrue(success, 'Expected filename not in local release list')

        num_downloaded_alerts = len(ztfa.get_local_alert_list())
        self.assertEqual(num_downloaded_alerts, self.expected_num_alerts)

    def test_remote_release_list(self):
        """Test ``get_remote_release_list`` returns a list of filenames

        Check ``get_remote_release_list`` returns a list
        Check the list is not empty
        Check filenames are strings
        Check filenames end with `.tar.gz`
        """

        release_list = ztfa.get_remote_release_list()
        self.assertTrue(release_list)

        num_to_test = 10  # Number or releases to check
        file_names = release_list[0]
        for filename in file_names[:num_to_test]:
            self.assertIsInstance(filename, str)

    def test_local_release_list(self):
        """Test ``get_local_release_list`` returns a list of filenames

        Check ``get_remote_release_list`` returns a list
        Check the list is not empty
        Check filenames are strings
        Check filenames end with `.tar.gz`
        """

        release_list = ztfa.get_local_release_list()
        self.assertIsInstance(release_list, list)
        self.assertTrue(release_list)
        for filename in release_list[:10]:
            self.assertIsInstance(filename, str)
            self.assertTrue(filename.endswith('.tar.gz'))

    def test_local_alerts(self):
        """Test ``get_local_alert_list`` returns a list integers

        Check ``get_local_alert_list`` returns a list
        Check the list is not empty
        Check alert IDs are integers
        Check alert IDs are greater than
        """

        alert_list = ztfa.get_local_alert_list()
        self.assertIsInstance(alert_list, list)
        self.assertTrue(alert_list)
        for alert_id in alert_list[:10]:
            self.assertIsInstance(alert_id, int)

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
