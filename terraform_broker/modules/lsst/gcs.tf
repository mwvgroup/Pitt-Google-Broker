# Google Cloud Storage (GCS) configuration for LSST

resource "google_storage_bucket" "broker_bucket" {
  name = "${var.project_id}-lsst-broker_files${local.dashed_test_suffix}"
  location = var.region

  uniform_bucket_level_access = true
}

resource "google_storage_bucket_object" "consumer_objects" {
  name   = "lsst"
  source = "consumer"
  bucket = google_storage_bucket.broker_bucket.name
}
