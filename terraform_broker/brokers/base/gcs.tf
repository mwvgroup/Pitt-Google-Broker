# Google Cloud Storage (GCS) configuration for ${VAR.SURVEY.NAME}

resource "google_storage_bucket" "broker_bucket" {
  name = "${var.project_id}-${var.survey.name}-broker_files${local.env.test_suffixes.dashed}"
  location = var.region

  uniform_bucket_level_access = true
}

resource "google_storage_bucket_object" "consumer_objects" {
  name   = "${var.survey.name}"
  source = "consumer"
  bucket = google_storage_bucket.broker_bucket.name
}
