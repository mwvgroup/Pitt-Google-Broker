module "broker_base" {
  source = "../base"

  survey = {
    name = "lsst"
    alerts_schema_version = var.alerts_schema_version
  }

  project = var.project
  environment = var.environment
}
