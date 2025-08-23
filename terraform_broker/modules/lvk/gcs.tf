# Google Cloud Storage (GCS) configuration for LSST

resource "google_storage_bucket" "alert_objects" {
  name = concat(flatten([var.project_id, "-lsst-broker_files", var.prod ? "" : ["_", var.test_prefix]]))
  location = var.region

  uniform_bucket_level_access = true
}

resource "google_storage_bucket_object" "consumer_objects" {
  name   = "consumer"
  source = "consumer"
  bucket = alert_objects.name
}
