# Google Cloud Storage (GCS) configuration for ZTF

resource "google_storage_bucket" "broker_bucket" {
  name = "${var.project_id}-ztf-broker_files${local.dashed_test_suffix}"
  location = var.region

  uniform_bucket_level_access = true
}

resource "google_storage_bucket_object" "consumer_objects" {
  name   = "ztf"
  source = "consumer"
  bucket = google_storage_bucket.broker_bucket.name
}

resource "google_storage_bucket_object" "night_conductor_objects" {
  name   = "night_conductor"
  source = "night_conductor"
  bucket = google_storage_bucket.broker_bucket.name
}

resource "google_storage_bucket_object" "night_conductor_objects" {
  name   = "schema_maps"
  source = "schema_maps"
  bucket = google_storage_bucket.broker_bucket.name
}
