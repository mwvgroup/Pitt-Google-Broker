variable "dataset_id" {
  description = "Survay BigQuery Dataset ID"
  type = string
}

variable "pubsub_topic" {
  description = "The survey's Pub/Sub topic to subscribe to for data."
  type = string
}

variable "classifier" {
  description = "The survey's model settings"
  type = object ({
    name = string
    table_schema_file = string
  })
}
