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
  table_id = concat(["alerts_", 
  description = "Alert data from LSST. This table is an archive of the lsst-alerts Pub/Sub stream. It has the same schema as the original alert bytes, including nested and repeated fields."

  schema = file(concat(["${path.module}/bq_lsst_alerts_", replace(var.schema_version, ".", "_"), "_schema.json"]))
}

