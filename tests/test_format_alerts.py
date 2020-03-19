#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This file provides tests for the alert formatting performed prior to storage
in GCS. This includes testing the generation of the valid schema pickle file by
the ``alert_ingestion.valid_schemas.gen_valid_schema`` module, and the
correction of alert schemas by the ``alert_ingestion.consume`` module.

To test a new survey version, store the Avro files for a few alerts in the
``test_alerts`` directory. Include the name and version of the survey in the
file name, separated by underscores. For the version, prepend a "v" and replace
the period with a dash. For example, the filename for a ZTF version 3.3 alert
should be: ``ztf_v3-3_originalfilename.avro``.
"""

from pathlib import Path
from unittest import TestCase

from broker.alert_ingestion import consume
from broker.alert_ingestion.valid_schemas.gen_valid_schema import _load_Avro

test_alerts_dir = Path(__file__).parent / 'test_alerts'


# Quick thoughts on test outlines for alert formatting
class AlertFormattingDataUnchanged(TestCase):
    """Test data we retrieve from file before / after formatting is the same"""

    def get_survey_and_schema(self, filename: str) -> (str, float):
        """ Parses the filename to get the survey and version"""
        f = filename.split('_')
        survey = f[0]
        version = float('.'.join(f[1].strip('v').split('-')))
        return (survey, version)

    def test_data_unchanged(self):
        # Test all alerts in test_alerts_dir
        for path in test_alerts_dir.glob('*.avro'):
            # Get the original data
            __, original_data = _load_Avro(str(path))

            # Correct the schema
            survey, version = self.get_survey_and_schema(path.name)
            max_size = 150000
            with consume.TempAlertFile(max_size=max_size, mode='w+b') as temp_file:
                with open(path, 'rb') as f:
                    temp_file.write(f.read())
                temp_file.seek(0)
                consume.GCSKafkaConsumer.fix_schema(temp_file, survey, version)

                temp_file.seek(0)
                # Get the data after correcting the schema
                __, corrected_data = _load_Avro(temp_file)

            self.assertEqual(original_data, corrected_data)

#
#     @classmethod
#     def setUpClass(cls):
#         """Read in test alert data"""
#
#         cls.test_alerts = dict()
#         for path in test_alerts_dir.glob('*.avro'):
#             # Todo: add this logic
#             survey, schema_version = get_survey_and_schema(path.name)
#             alert_data = parse_alert_file(path)
#
#             cls.test_alerts.setdefault(survey, {})[schema_version] = alert_data
#
#     # Todo: Add method for each formatting function
#     def test_format_ztf_3_3(self):
#         """Test schema formatting for ZTF version 3.3"""
#
#         self.fail()
#
#
# class SchemaVersionGuessing(TestCase):
#     """Test functions for guessing schema versions from alert data"""
#
#     def test_guess_schema_version_known_versions(self):
#         """Test guess_schema_version returns correct versions for simulated data"""
#
#         self.fail()
#
#     def test_guess_schema_version_raises(self):
#         """Test guess_schema_version raises an error on failure to determine version"""
#
#         self.fail()
#
#
# class SchemasurveyGuessing(TestCase):
#     """Test functions for guessing survey names from alert data"""
#
#     def test_guess_schema_survey_known_surveys(self):
#         """Test guess_schema_survey returns correct survey for simulated data"""
#
#         self.fail()
#
#     def test_guess_schema_survey_raises(self):
#         """Test guess_schema_survey raises an error on failure to determine survey"""
#
#         self.fail()
#
#
# class FormatGenericAlert(TestCase):
#     """Test ``format_alert_schema`` can handle multiple survey / schema
#     version combos
#     """
#
#     def test_ztf(self):
#         """Test ``format_alert_schema`` handles known ZTF schema versions"""
#
#         self.fail()
