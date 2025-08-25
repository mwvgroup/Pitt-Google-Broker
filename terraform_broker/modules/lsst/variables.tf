variable "alerts_schema_version" {
  description = "BigQuery schema version to use."
  type = string
  default = "7.4"
  nullable = false
}
variable "project_id" {
  description = "GCP project number for the broker."
  type = string
  nullable = false
}
variable "prod" {
  description = "If true, set up for production. Otherwise, will be test."
  type = bool
  default = false
  nullable = false
}
variable "test_prefix" {
  description = "Prefix to use for non-production resources. Only used if prod is false."
  type = string
  default = "test"
  nullable = false
}
variable "project_number" {
  description = "GCP project number corresponding to project_id."
  type = number
  nullable = false
}
variable "region" {
  description = "Region for GCP resources."
  type = string
  default = "us-central1"
  nullable = false
}
variable "zone" {
  description = "Zone for resources."
  type = string
  default = "us-central1-a"
  nullable = false
}
