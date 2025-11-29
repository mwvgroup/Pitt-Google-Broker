output "test_suffixes" {
  value = base.test_suffixes
  description = "Suffix to use for test resources (underscore)"
}

output "versiontag" {
  value = base.versiontag
}

output "alerts_dataset" {
  value = base.alerts_dataset.id
}

output "inputs" {
  value = {
    survey = var.survey
    environment = var.environment
    project = var.project
  }
}
