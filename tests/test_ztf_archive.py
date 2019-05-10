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
        """Download ZTF data for June 12th 2018"""

        # Ignore existing local data by creating a temporary data directory
        cls._temp_dir = TemporaryDirectory()
        temp_dir_path = Path(cls._temp_dir.name)
        ztfa._download_data.DATA_DIR = temp_dir_path
        ztfa._download_data.ALERT_LOG = temp_dir_path / 'alert_log.txt'

        try:
            # Use the 23,553 alerts generated on 06/26/2018 for testing
            cls.number_alerts = 23553
            cls.file_name = 'ztf_public_20180626.tar.gz'
            ztfa.download_data_date(2018, 6, 26)

        except:
            cls._temp_dir.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        """Delete temporary files"""

        cls._temp_dir.cleanup()

    def test_remote_release_list(self):
        """Test the ``get_remote_release_list`` returns a reasonable number
        of remote release files (>100)"""

        release_list = ztfa.get_remote_release_list()
        self.assertGreater(
            len(release_list), 100, 'Unreasonably few releases returned.')

    def test_local_release_list(self):
        """Test ``get_local_release_list`` returns the expected list"""

        release_list = ztfa.get_local_release_list()
        self.assertListEqual(release_list, [self.file_name])

    def test_local_alerts(self):
        """Test ``get_local_alert_list`` returns a list of the correct size"""

        num_alerts = len(ztfa.get_local_alert_list())
        self.assertEqual(num_alerts, self.number_alerts)

    def test_iter_alerts(self):
        """Test ``iter_alerts`` returns an appropriately sized list of dicts"""

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
