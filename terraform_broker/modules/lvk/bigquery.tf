resource "google_bigquery_dataset" "dataset" {
  dataset_id = "lsst${local.underscored_test_suffix}"
  description = "Dataset for storing LSST tables"
  location = var.region

  labels = {
    env = var.prod ? "prod" : "test"
    test_suffix = var.prod ? "" : var.test_suffix
  }
}

resource "google_bigquery_table" "alerts_table" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id = join("_", ["alerts", replace(var.alerts_schema_version, ".", "_")])
  description = "Alert data from LSST. This table is an archive of the lsst-alerts Pub/Sub stream. It has the same schema as the original alert bytes, including nested and repeated fields."

  schema = file("${path.module}/bq_schemas/alerts_table.json")

  labels = {
    versiontag = var.alerts_schema_version
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

