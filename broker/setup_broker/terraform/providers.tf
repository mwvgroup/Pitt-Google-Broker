# ------------------------------------------------------------
#   BACKEND BLOCK
#   
#   Bucket must exist before configuring the backend
# ------------------------------------------------------------

terraform {
  backend "gcs" {
    bucket = "gcs-tf-state-bucket"
    prefix = "bucket/dir/prefix/"
  }

  required_providers {
    google      = "~> 3.1"
    google-beta = "~> 3.1"
  }
}
