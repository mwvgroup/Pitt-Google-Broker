#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This file provides tests for the ``broker.alert_ingestion.format_alerts``
module.
"""

from pathlib import Path
from unittest import TestCase

test_alerts_dir = Path(__file__).parent / 'test_alerts'


# Quick thoughts on test outlines for alert formatting
class AlertFormattingDataUnchanged(TestCase):
    """Test data we retrieve from file before / after formatting is the same"""

    @classmethod
    def setUpClass(cls):
        """Read in test alert data"""

        cls.test_alerts = dict()
        for path in test_alerts_dir.glob('*.avro'):
            # Todo: add this logic
            survey, schema_version = get_survey_and_schema(path.name)
            alert_data = parse_alert_file(path)

            cls.test_alerts.setdefault(survey, {})[schema_version] = alert_data

    # Todo: Add method for each formatting function
    def test_format_ztf_3_3(self):
        """Test schema formatting for ZTF version 3.3"""

        self.fail()


class SchemaVersionGuessing(TestCase):
    """Test functions for guessing schema versions from alert data"""

    def test_guess_schema_version_known_versions(self):
        """Test guess_schema_version returns correct versions for simulated data"""

        self.fail()

    def test_guess_schema_version_raises(self):
        """Test guess_schema_version raises an error on failure to determine version"""

        self.fail()


class SchemasurveyGuessing(TestCase):
    """Test functions for guessing survey names from alert data"""

    def test_guess_schema_survey_known_surveys(self):
        """Test guess_schema_survey returns correct survey for simulated data"""

        self.fail()

    def test_guess_schema_survey_raises(self):
        """Test guess_schema_survey raises an error on failure to determine survey"""

        self.fail()


class FormatGenericAlert(TestCase):
    """Test ``format_alert_schema`` can handle multiple survey / schema
    version combos
    """

    def test_ztf(self):
        """Test ``format_alert_schema`` handles known ZTF schema versions"""

        self.fail()
