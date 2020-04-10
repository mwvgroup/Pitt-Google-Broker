#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""This file provides tests for the alert formatting performed prior to storage
in GCS. This includes testing the generation of the valid schema pickle file by
the ``alert_ingestion.valid_schemas.gen_valid_schema`` module, and the
correction of alert schemas by the ``alert_ingestion.consume`` module.

To test a new survey version:
    1. Store an Avro file in the ``test_alerts`` directory. Include the name
    and version of the survey in the file name, separated by underscores
    (e.g., ``ztf_3.3_originalfilename.avro``).
    2. Register the test alert's path to the ``test_alert_path`` dictionary
    with a key formatted as f'{survey}_{version}'.
    3. Create new test functions. Use the following functions as templates and
    change the function name and the ``survey`` and ``version`` variables.
        1. ``test_data_unchanged_ztf_3_3()``
        2. ``test_BQupload_ztf_3_3()``
        3. ``test_guess_schema_version_ztf_3_3`()`
        4. ``test_guess_schema_survey_ztf_3_3()``

Module Documentation
--------------------
"""

import os
from pathlib import Path
from typing import BinaryIO
from unittest import TestCase
from google.cloud import bigquery

from broker import exceptions
from broker.alert_ingestion import consume
from broker.alert_ingestion.gen_valid_schema import _load_Avro


dataset_id = 'dataset_for_testing'
max_alert_size = 150000  # for creating temporary files
test_alerts_dir = Path(__file__).parent / 'test_alerts'
test_alert_path = {
            'ztf_3.3': test_alerts_dir / 'ztf_3.3_1154308030015010004.avro',
}


def run_consume_fix_schema(path: Path, temp_file: BinaryIO):
    """ Loads the file at path into the temp_file and runs
    consume.GCSKafkaConsumer.fix_schema() on the temp_file object.

    Usage Example
    -------------

    .. code-block:: python
       :linenos:

        with consume.TempAlertFile(max_size=max_alert_size, mode='w+b') as temp_file:
            run_consume_fix_schema(path, temp_file)
            # temp_file now contains the reformatted alert

    """
    survey, version, __ = path.stem.split('_')

    with open(path, 'rb') as f:
        temp_file.write(f.read())
    temp_file.seek(0)
    consume.GCSKafkaConsumer.fix_schema(temp_file, survey, version)

    temp_file.seek(0)

def load_Avro_bytes(path: Path) -> BinaryIO:
    """ Loads an Avro file to a bytes object and returns it.
    """

    with open(path, 'rb') as f:
        bytes = f.read()
        return bytes

class AlertFormattingDataUnchanged(TestCase):
    """Test data we retrieve from file before / after formatting with
    ``consume.GCSKafkaConsumer.fix_schema()`` is the same.
    """

    def test_data_unchanged_ztf_3_3(self):
        """ ZTF version 3.3 formatting, test that data is unchanged. """

        survey, version = 'ztf', '3.3'
        self.data_unchanged(test_alert_path[f'{survey}_{version}'])

    def data_unchanged(self, path: Path):
        """ Tests that the data in the path file is unchanged when reformatting
        the schema header with `consume.GCSKafkaConsumer.fix_schema()`.
        """
        survey, version, __ = path.stem.split('_')

        # Get the original data
        __, original_data = _load_Avro(str(path))

        # Correct the schema and get the data again
        with consume.TempAlertFile(max_size=max_alert_size, mode='w+b') as temp_file:
            run_consume_fix_schema(path, temp_file)
            __, corrected_data = _load_Avro(temp_file)

        # test data unchanged
        msg = (f'Data was changed while correcting the schema header'
               f' for {survey} version {version}')
        self.assertEqual(original_data, corrected_data, msg)


class AlertFormattedForBigQuery(TestCase):
    """ Test that the alerts are formatted properly for import into BigQuery.
    This test clears the BQ test table before uploading an alert and therefore
    does _NOT_ test whether different survey/version combinations are
    compatible for upload to the same BQ table.


    """

    @classmethod
    def setUpClass(cls):
        cls.client = bigquery.Client()
        cls.dataset_id = dataset_id
        cls.table_id = 'temp_table'  # created automatically if needed

        cls.dataset_ref = cls.client.dataset(cls.dataset_id)
        cls.table_ref = cls.dataset_ref.table(cls.table_id)
        cls.job_config = bigquery.LoadJobConfig()
        cls.job_config.source_format = bigquery.SourceFormat.AVRO
        cls.job_config.write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE
        cls.job_config.autodetect = True  # enable schema autodetection

    def test_BQupload_ztf_3_3(self):
        """ ZTF version 3.3 upload to BigQuery test. """

        survey, version = 'ztf', '3.3'
        path = test_alert_path[f'{survey}_{version}']

        # Correct the schema and upload to BQ
        with consume.TempAlertFile(max_size=max_alert_size, mode='r+b') as temp_file:
            run_consume_fix_schema(path, temp_file)
            self.assert_alert_uploads_to_BigQuery(temp_file)

    def assert_alert_uploads_to_BigQuery(self, temp_file):
        """ Tests whether an alert is formatted correctly for insertion into a
        BigQuery table.
        """

        temp_file.seek(0)
        job = self.client.load_table_from_file(temp_file,
                                               self.table_ref,
                                               job_config=self.job_config)

        try:
            job.result()  # Waits for table load to complete.
        except BadRequest as e:  # schema header is not formatted correctly
            self.fail(str(e))
        except Exception as e:
            self.error(str(e))

        # print(f'Loaded {job.output_rows} rows into {self.dataset_id}:{self.table_id}')


class SchemaVersionGuessing(TestCase):
    """Test functions for guessing schema versions from alert data"""

    def test_guess_schema_version_ztf_3_3(self):
        """Tests that guess_schema_version() returns correct version for an
        alert with a known version.
        """

        # load the alert as a bytes object
        survey, version = 'ztf', '3.3'
        path = test_alert_path[f'{survey}_{version}']
        alert_bytes = load_Avro_bytes(path)

        # extract the version and check that it is as expected
        try:
            schema_version = consume.guess_schema_version(alert_bytes)
        except exceptions.SchemaParsingError as e:
            self.fail(str(e))
        else:
            msg = f'guess_schema_version() failed for {survey} version {version}'
            self.assertEqual(version, schema_version, msg)


class SchemaSurveyGuessing(TestCase):
    """Test functions for guessing schema survey from alert data"""

    def test_guess_schema_survey_ztf_3_3(self):
        """Tests that guess_schema_survey() returns correct survey for an
        alert with a known survey.
        """

        # load the alert as a bytes object
        survey, version = 'ztf', '3.3'
        path = test_alert_path[f'{survey}_{version}']
        alert_bytes = load_Avro_bytes(path)

        # extract the survey and check that it is as expected
        try:
            schema_survey = consume.guess_schema_survey(alert_bytes)
        except exceptions.SchemaParsingError as e:
            self.fail(str(e))
        else:
            msg = f"guess_schema_survey() failed for {survey} version {version}"
            self.assertEqual(survey, schema_survey, msg)
