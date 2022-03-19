# Enables the Cloud Run API
resource "google_project_service" "run_api" {
  service = "run.googleapis.com"
  disable_on_destroy = true
}

# Create the Cloud Run service
resource "google_cloud_run_service" "run_service" {
  name = "bq_rest_api"
  location = "us-central1"

  # Waits for the Cloud Run API to be enabled
  depends_on = [google_project_service.run_api]

  template {
    spec {
      containers {
        image = "gcr.io/google-samples/bq_rest_api:latest"
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}
