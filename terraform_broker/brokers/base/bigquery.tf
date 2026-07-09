resource "google_bigquery_dataset" "dataset" {
  dataset_id = "${var.survey.name}${local.test_suffixes.underscored}"
  description = "Dataset for storing ${var.survey.name} tables"
  location = var.region

  labels = {
    env = var.prod ? "prod" : "test"
    test_suffix = local.env.test_suffixes.underscored
  }
}

# Dataset is publicly viewable. Users will pay for their queries.
resource "google_bigquery_dataset_access" "dataset_access" {
  dataset_id    = google_bigquery_dataset.dataset.dataset_id
  role          = "VIEWER"
  user_by_email = "allUsers"
}

# PubSub can write into the dataset and manage it.
resource "google_bigquery_dataset_access" "dataset_access" {
  dataset_id    = google_bigquery_dataset.dataset.dataset_id
  role          = "OWNER"
  user_by_email = google_pubsub_subscription.bq_import.bigquery_config.service_account_email
}

resource "google_bigquery_table" "alerts_table" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id = "alerts_${local.versiontag}${local.env.test_suffixes.underscore}"
  description = "Alert data from ${var.survey.name}. This table is an archive of the ${var.survey.name}-alerts Pub/Sub stream. It has the same schema as the original alert bytes, including nested and repeated fields."

  schema = file("${path.module}/bq_schemas/alerts_table.json")

  labels = {
    versiontag = "v${var.alerts_schema_version}"
  }
}

resource "google_bigquery_table" "supernnova_table" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id = "supernnova"
  description = "Binary classification results from SuperNNova."

  schema = file("${path.module}/bq_schemas/supernnova_table.json")
}

resource "google_bigquery_table" "variability_table" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id = "variability"

  schema = file("${path.module}/bq_schemas/variability_table.json")
}

resource "google_bigquery_table" "upsilon_table" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id = "upsilon"

  schema = file("${path.module}/bq_schemas/upsilon_table.json")
}













