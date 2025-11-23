output "test_suffixes" {
  value = local.env.test_suffixes
  description = "Suffix to use for test resources (underscore)"
}

output "versiontag" {
  value = local.versiontag
}

output "alerts_dataset" {
  value = google_bigquery_dataset.alerts_dataset.id
}

output "inputs" {
  value = {
    survey = var.survey
    environment = var.environment
    project = var.project
  }
}
