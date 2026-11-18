terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "7.4.0"
    }
  }
}

provider "google" {
  project = var.project.id
  region = var.project.region
  zone = var.project.zone
}
