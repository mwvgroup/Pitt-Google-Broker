# Pub/Sub configuration for LSST.

resource "google_pubsub_topic" "raw_alerts" {
  name = concat(flatten(["lsst-alerts_raw", var.prod ? "" : ["_", var.test_prefix]]))
}
resource "google_pubsub_topic" "alerts" {
  name = concat(flatten(["lsst-alerts", var.prod ? "" : ["_", var.test_prefix]]))
}
resource "google_pubsub_topic" "bq_import" {
  name = concat(flatten(["lsst-bigquery-import-", var.prod ? "" : ["_", var.test_prefix]]))
}
resource "google_pubsub_topic" "bq_deadletter" {
  name = concat(flatten(["lsst-bigquery-import-deadletter-", replace(var.schema_version, ".", "_"), var.prod ? "" : ["_", var.test_prefix]]))
}

resource "google_pubsub_subscription" "alerts-reservoir" {
  name = concat(flatten(["lsst-alerts-reservoir", var.prod ? "" : ["_", var.test_prefix]]))
  topic = google_pubsub_topic.alerts
}
resource "google_pubsub_subscription" "bq_deadletter" {
  name = google_pubsub_topic.bq_deadletter.name
  topic = google_pubsub_topic.bq_deadletter
}
resource "google_pubsub_subscription" "bq_import" {
  name = concat(flatten(["lsst-bigquery-import-", replace(var.schema_version, ".", "_"), var.prod ? "" : ["_", var.test_prefix]]))
  topic = google_pubsub_topic.bq_import
  filter= <<EOF
    attributes.schema_version = "'"${google_bigquery_dataset.alerts_dataset.labels.versiontag}"'"'
  EOF

  bigquery_config {
    table = "${var.project_id}.${google_bigquery_table.alerts_table.dataset_id}.${google_bigquery_table.alerts_table.table_id}"
    use_table_schema=true
  }
  dead_letter_policy {
    topic = google_pubsub_topic.deadletter.id
    max_delivery_attempts=5
  }
}
