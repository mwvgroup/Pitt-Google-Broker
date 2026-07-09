locals {
  # Empty unless test, in which case the test_suffix is prefaced by _
  underscored_test_suffix = "%{ if !var.prod }_${var.test_suffix}%{ endif }"
  # Empty unless test, in which case the test_suffix is prefaced by -
  dashed_test_suffix = "%{ if !var.prod }-${var.test_suffix}%{ endif }"
  # Version tag, derived from the version number
  versiontag = format("v%s", replace(var.alerts_schema_version, ".", "_"))
}
