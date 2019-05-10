#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This file provides tests for the ``broker.ztf_archive`` module."""

from unittest import TestCase

from broker import ztf_archive as ztfa


class DataAccess(TestCase):

    @classmethod
    def setUpClass(cls):
        """Download ZTF data for June 12th 2018"""

        ztfa.download_data_date(2018, 6, 12)

    def test_get_number_local_releases(self):
        """Tests for ``ztf_archive.get_number_local_releases``"""

        self.assertEqual(ztfa.get_number_local_releases(), 1)

    def test_get_number_local_alerts(self):
        """Tests for ``ztf_archive.get_number_local_alerts``"""

        self.assertEqual(ztfa.get_number_local_alerts(), 1)

    def test_format_iter_alerts(self):
        """Tests for ``ztf_archive.iter_alerts``"""

        for alert_list in ztfa.iter_alerts(1):
            self.assertIsInstance(alert_list, list)
            self.assertIsInstance(alert_list[0], dict)
            break

        for alert_list in ztfa.iter_alerts(10):
            self.assertEqual(len(alert_list), 10)
            break

