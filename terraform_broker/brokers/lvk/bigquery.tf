resource "google_bigquery_dataset" "dataset" {
  dataset_id = "lvk${local.underscored_test_suffix}"
  description = "Dataset for storing LVK tables"
  location = var.region

  labels = {
    env = var.prod ? "prod" : "test"
    test_suffix = var.prod ? "" : var.test_suffix
  }
}

resource "google_bigquery_table" "alerts_table" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id = "alerts_${local.versiontag}${underscore_test_suffix}"
  description = "Alert data from LIGO/Virgo/KAGRA. This table is an archive of the lvk-alerts Pub/Sub stream. It has the same schema (excluding skymaps) as the original alert bytes, including nested and repeated fields."

  schema = file("${path.module}/bq_schemas/alerts_table.json")

  labels = {
    versiontag = var.alerts_schema_version
  }
}
