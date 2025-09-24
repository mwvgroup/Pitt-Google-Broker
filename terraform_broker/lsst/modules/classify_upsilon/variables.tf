variable "project_id" {
  description = "GCP project number for the broker."
  type = string
  nullable = false
}
variable "prod" {
  description = "If true, set up for production. Otherwise, will be test."
  type = bool
  nullable = false
}
variable "test_suffix" {
  description = "Suffix to use for non-production resources. Only used if prod is false."
  type = string
  nullable = false
}
variable "region" {
  description = "Region for GCP resources."
  type = string
  nullable = false
}
variable "survey_dataset" {
  description = "BigQuery dataset to write classifier output to"
  type = string
  nullable = false
}
variable "dead_letter_topic" {
  description = "Dead letter topic to use for pubsub subscriptions."
  type = string
  nullable = false
}
variable "pubsub_output_viewer_role" {
  description = "Pub/Sub Output Topic Viewer"
  type = string
  nullable = false
}
variable "pubsub_output_viewers" {
  description = "Pub/Sub output viewers"
  type = list(string)
}
