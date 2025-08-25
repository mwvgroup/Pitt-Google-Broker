# Pub/Sub configuration for LVK.

resource "google_pubsub_topic" "raw_alerts" {
  name = "lvk-alerts_raw${local.dashed_test_suffix}"
}
resource "google_pubsub_topic" "alerts" {
  name = "lvk-alerts${local.dashed_test_suffix}"
}
resource "google_pubsub_topic" "bq_import" {
  name = "lvk-bigquery-import${local.dashed_test_suffix}"
}
resource "google_pubsub_topic" "bq_deadletter" {
  name = "lvk-bigquery-import-deadletter${local.dashed_test_suffix}"
}

resource "google_pubsub_subscription" "alerts-reservoir" {
  name = "lvk-alerts-reservoir${local.dashed_test_suffix}"
  topic = google_pubsub_topic.alerts
}
resource "google_pubsub_subscription" "bq_deadletter" {
  name = google_pubsub_topic.bq_deadletter.name
  topic = google_pubsub_topic.bq_deadletter
}
resource "google_pubsub_subscription" "bq_import" {
  name = "lvk-bigquery-import${local.dashed_test_suffix}"
  topic = google_pubsub_topic.bq_import
  filter= <<EOF
    attributes.schema_version = "'"${google_bigquery_table.alerts_table.labels.versiontag}"'"'
  EOF

  bigquery_config {
    table = "${var.project_id}.${google_bigquery_table.alerts_table.dataset_id}.${google_bigquery_table.alerts_table.table_id}"
    use_table_schema=true
  }
  dead_letter_policy {
    dead_letter_topic = google_pubsub_topic.bq_deadletter.name
    max_delivery_attempts=5
  }
}
