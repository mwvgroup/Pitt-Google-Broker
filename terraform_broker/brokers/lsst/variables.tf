variable "alerts_schema_version" {
  description = "BigQuery schema version to use for the LSST alerts table."
  type = string
  default = "7.4"
  nullable = false
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
