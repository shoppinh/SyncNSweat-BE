# ========================================
# Deploy Module Outputs
# ========================================

# ========================================
# Cloud Run Outputs
# ========================================

output "cloud_run_service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_service.backend.name
}

output "cloud_run_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_service.backend.status[0].url
}

output "cloud_run_service_account" {
  description = "Cloud Run service account email (from bootstrap)"
  value       = data.terraform_remote_state.bootstrap.outputs.cloudrun_service_account_email
}

# ========================================
# Artifact Registry Outputs
# ========================================

output "artifact_registry_repository" {
  description = "Artifact Registry repository name"
  value       = google_artifact_registry_repository.docker.repository_id
}

output "artifact_registry_url" {
  description = "Full Artifact Registry URL for Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker.repository_id}"
}

# ========================================
# Cloud SQL Outputs
# ========================================

output "cloud_sql_connection_name" {
  description = "Cloud SQL instance connection name for Cloud Run"
  value       = google_sql_database_instance.postgres.connection_name
}

output "cloud_sql_instance_id" {
  description = "Cloud SQL instance ID"
  value       = google_sql_database_instance.postgres.name
}

output "database_name" {
  description = "Database name"
  value       = google_sql_database.db.name
}

output "database_user" {
  description = "Database user"
  value       = google_sql_user.user.name
}

# ========================================
# Secret Manager Outputs
# ========================================

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

# ========================================
# Configuration Outputs
# ========================================

output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP Region"
  value       = var.region
}

output "service_name" {
  description = "Cloud Run service name"
  value       = var.service_name
}

# ========================================
# Bootstrap References
# ========================================

output "github_actions_service_account" {
  description = "GitHub Actions service account email (from bootstrap)"
  value       = data.terraform_remote_state.bootstrap.outputs.github_actions_service_account_email
}

output "workload_identity_provider" {
  description = "Workload Identity Provider resource name (from bootstrap)"
  value       = data.terraform_remote_state.bootstrap.outputs.workload_identity_provider
}
