resource "google_artifact_registry_repository" "docker" {
  repository_id = var.artifact_repo_name
  location      = var.region
  format        = "DOCKER"

  depends_on = [
    google_project_service.services["artifactregistry.googleapis.com"]
  ]
}
