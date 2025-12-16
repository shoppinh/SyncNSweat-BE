resource "google_cloud_run_service" "backend" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  template {
    spec {
      containers {
        # Use a small public image so the service can be created during bootstrap.
        image = "gcr.io/cloudrun/hello"
        ports {
          container_port = 8000
        }
      }
      service_account_name = google_service_account.cloudrun.email
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.services["run.googleapis.com"],
  ]
}

resource "google_cloud_run_service_iam_member" "invoker_allUsers" {
  project = var.project_id
  location = var.region
  service = google_cloud_run_service.backend.name
  role    = "roles/run.invoker"
  member  = "allUsers"

  depends_on = [
    google_cloud_run_service.backend,
  ]
}
