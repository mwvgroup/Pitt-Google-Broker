variable "survey" {
  description = "Survey the broker is operating on."
  type = object({
    name = string
    alerts_schema_version = string
    # Service accounts
    publisher_sa = string
    runner_sa = string
    appengine_deployer_sa = string
    consumer {
      admin_properties_file = string
    }
  })
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

