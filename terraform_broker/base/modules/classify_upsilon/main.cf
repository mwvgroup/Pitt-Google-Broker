locals {
  # Empty unless test, in which case the test_suffix is prefaced by _
  underscored_test_suffix = "%{ if !var.prod }_${var.test_suffix}%{ endif }"
  # Empty unless test, in which case the test_suffix is prefaced by -
  dashed_test_suffix = "%{ if !var.prod }-${var.test_suffix}%{ endif }"
}
