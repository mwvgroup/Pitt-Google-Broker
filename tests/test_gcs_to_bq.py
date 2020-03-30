import os
from unittest import TestCase

from broker.alert_ingestion.GCS_to_BQ import main


class GCS2BQ_upload(TestCase):
    """Tests the Cloud Function that listens to a GCS bucket and uploads new
    files to a BQ table.
    """

    def test_upload_GCS_to_BQ(self):
        """ Tests that the `stream_GCS_to_BQ()` function successfully uploads an
        Avro file (stored in a GCS bucket) to a BigQuery table.
        """

        # Get info on the Avro file (with a valid schema) to be uploaded
        data = {
                'bucket': 'ardent-cycling-243415_testing_bucket',
                'name': 'ztf_3.3_validschema_1154446891615015011.avro'
        }
        context = {}

        # Test the function
        try:
            job_errors = main.stream_GCS_to_BQ(data, context)

        except Exception as e:
            self.error(str(e))

        else:
            self.assertIsNone(job_errors)
