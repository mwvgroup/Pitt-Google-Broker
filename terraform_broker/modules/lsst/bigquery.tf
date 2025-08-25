resource "google_bigquery_dataset" "alerts_dataset" {
  dataset_id = concat(flatten(["lsst", (var.prod ? [""] : ["_", var.test_prefix])]))
  description = "Dataset for storing LSST alert data"
  location = var.region

  labels = {
    env = var.prod ? "prod" : "test"
    test_prefix = var.prod ? "" : var.test_prefix
    versiontag = replace(var.schema_version, ".", "_")
  }
}

resource "google_bigquery_table" "alerts_table" {
  dataset_id = google_bigquery_dataset.alerts_dataset.dataset_id
  table_id = concat(["alerts_", var.schema_version])
  description = "Alert data from LSST. This table is an archive of the lsst-alerts Pub/Sub stream. It has the same schema as the original alert bytes, including nested and repeated fields."

  schema = file("${path.module}/bq_schemas/alerts_table.json")
}

resource "google_bigquery_table" "supernnova_table" {
  dataset_id = google_bigquery_dataset.alerts_dataset.dataset_id
  table_id = "supernnova"
  description = "Binary classification results from SuperNNova."

  schema = file("${path.module}/bq_schemas/supernnova_table.json")
}

resource "google_bigquery_table" "variability_table" {
  dataset_id = google_bigquery_dataset.alerts_dataset.dataset_id
  table_id = "variability"

  schema = file("${path.module}/bq_schemas/variability_table.json")
}

resource "google_bigquery_table" "upsilon_table" {
  dataset_id = google_bigquery_dataset.alerts_dataset.dataset_id
  table_id = "upsilon"

  schema = file("${path.module}/bq_schemas/upsilon_table.json")
}

