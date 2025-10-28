locals {
  env = {
    "test_suffixes" {
      # Empty unless test, in which case the test_suffix is prefaced by _
      underscored = "%{ if !var.environment.prod }_${var.environment.test_suffix}%{ endif }"
      # Empty unless test, in which case the test_suffix is prefaced by -
      dashed = "%{ if !var.environment.prod }-${var.environment.test_suffix}%{ endif }"
    }
  }
}

# Version tag, derived from the version number
versiontag = format("v%s", replace(var.alerts_schema_version, ".", "_"))
