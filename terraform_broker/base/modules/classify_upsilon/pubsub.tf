resource "google_pubsub_topic" "output" {
  name = "lsst-upsilon{local.dashed_test_suffix}"
}
resource "google_pubsub_topic" "trigger" {
  name = "lsst-lite${local.dashed_test_suffix}"
}

resource "google_pubsub_subscription" "bq_import" {
  name = "lsst-upsilon-bigquery-import${local.dashed_test_suffix}"
  topic = google_pubsub_topic.output
  bigquery_config {
    table = "${vars.project_id}:${vars.survey_dataset}.upsilon"
    drop_unknown_fields = true
  }
  dead_letter_policy {
    dead_letter_topic = vars.dead_letter_topic
    max_delivery_attempts=5
  }
}

resource "google_pubsub_subscription" "trigger" {
  name = "lsst-upsilon-bigquery-import${local.dashed_test_suffix}"
  topic = google_pubsub_topic.trigger
  bigquery_config {
    table = "${vars.project_id}:${vars.survey_dataset}.upsilon"
    drop_unknown_fields = true
  }
  dead_letter_policy {
    dead_letter_topic = vars.dead_letter_topic
    max_delivery_attempts=5
  }
}

resource "google_pubsub_topic_iam_binding" "binding" {
  project = vars.project_id
  topic = google_pubsub_topic.output.name
  role = vars.pubsub_output_viewer
  members = vars.pubsub_output_viewers
}
