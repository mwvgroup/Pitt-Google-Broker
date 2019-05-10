#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This file provides tests for the ``broker.ztf_archive`` module."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from broker import ztf_archive as ztfa


class DataAccess(TestCase):

    @classmethod
    def setUpClass(cls):
        """Download ZTF data for June 12th 2018"""

        # Ignore existing local alert data
        cls._temp_dir = TemporaryDirectory()
        ztfa._download_data.DATA_DIR = Path(cls._temp_dir.name)

        try:
            # Use the 23,553 alerts generated on 06/26/2018 for testing
            cls.number_alerts = 23553
            ztfa.download_data_date(2018, 6, 26)

        except:
            cls._temp_dir.cleanup()
            raise

    def tearDownClass(self):
        """Delete temporary files"""

        self._temp_dir.cleanup()

    def test_get_number_local_releases(self):
        """Tests for ``ztf_archive.get_number_local_releases``"""

        self.assertEqual(ztfa.get_number_local_releases(), 1)

    def test_get_number_local_alerts(self):
        """Tests for ``ztf_archive.get_number_local_alerts``"""

        self.assertEqual(ztfa.get_number_local_alerts(), self.number_alerts)

    def test_format_iter_alerts(self):
        """Tests for ``ztf_archive.iter_alerts``"""

        alert_list = next(ztfa.iter_alerts(1))
        self.assertIsInstance(alert_list, list)
        self.assertIsInstance(alert_list[0], dict)

        alert_list = ztfa.iter_alerts(10)
        self.assertEqual(len(alert_list), 10)
