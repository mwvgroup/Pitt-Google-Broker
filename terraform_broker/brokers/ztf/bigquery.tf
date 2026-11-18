resource "google_bigquery_dataset" "dataset" {
  dataset_id = "ztf${local.underscored_test_suffix}"
  description = "Dataset for storing ZTF tables"
  location = var.region

  labels = {
    env = var.prod ? "prod" : "test"
    test_suffix = var.prod ? "" : var.test_suffix
  }
}

resource "google_bigquery_table" "alerts_table" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id = "alerts_${local.versiontag}${underscore_test_suffix}"
  description = "Alert data from ZTF."

  schema = file("${path.module}/bq_schemas/alerts_table.json")

  labels = {
    versiontag = "v${var.alerts_schema_version}"
  }
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

