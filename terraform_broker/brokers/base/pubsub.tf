# Pub/Sub configuration for LSST.

resource "google_pubsub_topic" "raw_alerts" {
  name = "lsst-alerts_raw${local.env.test_suffixes.dashed}"
}
resource "google_pubsub_topic" "alerts" {
  name = "lsst-alerts${local.env.test_suffixes.dashed}"
}
resource "google_pubsub_topic" "bq_import" {
  name = "lsst-bigquery-import${local.env.test_suffixes.dashed}"
}
resource "google_pubsub_topic" "bq_deadletter" {
  name = "lsst-bigquery-import-deadletter${local.env.test_suffixes.dashed}"
}

resource "google_pubsub_subscription" "alerts-reservoir" {
  name = "lsst-alerts-reservoir${local.env.test_suffixes.dashed}"
  topic = google_pubsub_topic.alerts
}
resource "google_pubsub_subscription" "bq_deadletter" {
  name = google_pubsub_topic.bq_deadletter.name
  topic = google_pubsub_topic.bq_deadletter
}
resource "google_pubsub_subscription" "bq_import" {
  name = "lsst-bigquery-import${local.env.test_suffixes.dashed}"
  topic = google_pubsub_topic.bq_import
  filter= <<EOF
    attributes.schema_version = "'"${google_bigquery_table.alerts_table.labels.versiontag}"'"'
  EOF

  bigquery_config {
    table = "${var.project.id}.${google_bigquery_table.alerts_table.dataset_id}.${google_bigquery_table.alerts_table.table_id}"
    use_table_schema=true
  }
  dead_letter_policy {
    dead_letter_topic = google_pubsub_topic.bq_deadletter.name
    max_delivery_attempts=5
  }
}
