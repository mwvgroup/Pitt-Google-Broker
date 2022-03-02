import os
from unittest import TestCase

from broker.cloud_functions.GCS_to_BQ import main

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
testing_bucket = f"{PROJECT_ID}_testing_bucket"
testing_file = "ztf_3.3_validschema_1154446891615015011.avro"


class GCS2BQ_upload(TestCase):
    """Tests the Cloud Function that listens to a GCS bucket and uploads new
    files to a BQ table.
    """

    def test_upload_GCS_to_BQ(self):
        """Tests that the `stream_GCS_to_BQ()` function successfully uploads an
        Avro file (stored in a GCS bucket) to a BigQuery table.
        """

        # Get info on the Avro file (with a valid schema) to be uploaded
        data = {
            "bucket": testing_bucket,
            "name": testing_file,  # must already exist in bucket
        }
        context = {}

        # Test the function
        try:
            job_errors = main.stream_GCS_to_BQ(data, context)

        except Exception as e:
            self.fail(str(e))

        else:
            self.assertIsNone(job_errors)
