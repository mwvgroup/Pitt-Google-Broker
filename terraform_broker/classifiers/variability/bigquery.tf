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

