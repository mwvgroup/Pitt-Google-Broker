variable "classifier" {
  description = "The survey's model settings"
  type = object ({
    name = string
    table_schema_file = string
  })
}

variable "broker" {
  description = "How the classifier will plug in to the broker"
  type = object({
    dataset_id = string
    pubsub_topic = string
  })
}

variable "project" {
  description = "Project configuration settings"
  type = object({
    id = string
    number = number
    region = string
    zone = string
    # IAM settings
    owners = list(string)
    editors = list(string)
    viewers = list(string)
  })
}

variable "environment" {
  description = "Environment configuration (prod, testing, etc.)"
  type = object({
    prod = bool
    # test_suffix is ignored if prod is true.
    test_suffix = string
  })
}

