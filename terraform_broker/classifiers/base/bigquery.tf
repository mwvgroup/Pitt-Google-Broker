resource "google_bigquery_table" "supernnova_table" {
  dataset_id = var.dataset_id
  table_id = var.classifier.name

  schema = file("${path.module}/bq_schemas/supernnova_table.json")
}
