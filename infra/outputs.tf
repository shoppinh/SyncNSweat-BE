output "service_account_email" {
  description = "GitHub Actions service account email"
  value       = google_service_account.github_actions.email
}

output "workload_identity_provider" {
  description = "Workload Identity Provider resource name"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository name"
  value       = google_artifact_registry_repository.docker.repository_id
}

output "artifact_registry_url" {
  description = "Full Artifact Registry URL for Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}

output "cloud_run_service_name" {
  description = "Cloud Run service name"
  value       = var.service_name
}

# Secret Manager outputs - used by CI/CD to populate secret values
output "secret_names" {
  description = "List of all secret names managed by Terraform"
  value       = var.secret_names
}

output "secret_ids" {
  description = "Map of secret names to their full resource IDs"
  value = {
    for name in var.secret_names :
    name => google_secret_manager_secret.secrets[name].id
  }
}

output "cloudrun_service_account" {
  description = "Cloud Run service account email"
  value       = google_service_account.cloudrun.email
}

output "cloud_sql_connection_name" {
  description = "Cloud SQL instance connection name for Cloud Run"
  value       = google_sql_database_instance.postgres.connection_name
}

output "cloud_sql_instance_id" {
  description = "Cloud SQL instance ID"
  value       = google_sql_database_instance.postgres.name
}

output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP Region"
  value       = var.region
}

# output "cloud_run_url" {
output "cloud_run_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_service.backend.status[0].url
}

output "database_user" {
  description = "Database user for Cloud SQL"
  value       = google_sql_user.user.name
}

output "database_name" {
  description = "Database name for Cloud SQL"
  value       = google_sql_database.db.name
}

