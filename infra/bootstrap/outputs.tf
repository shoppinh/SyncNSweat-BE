# ========================================
# Bootstrap Module Outputs
# ========================================
# These outputs are consumed by the deploy module via remote state

# ========================================
# Service Account Outputs
# ========================================

output "github_actions_service_account_email" {
  description = "Email of the GitHub Actions service account"
  value       = google_service_account.github_actions.email
}

output "cloudrun_service_account_email" {
  description = "Email of the Cloud Run service account"
  value       = google_service_account.cloudrun.email
}

# ========================================
# Workload Identity Outputs
# ========================================

output "workload_identity_provider" {
  description = "Full resource name of the Workload Identity Provider for GitHub Actions"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "workload_identity_pool_id" {
  description = "ID of the Workload Identity Pool"
  value       = google_iam_workload_identity_pool.github.workload_identity_pool_id
}

# ========================================
# Terraform State Outputs
# ========================================

output "terraform_state_bucket" {
  description = "Name of the GCS bucket storing Terraform state"
  value       = google_storage_bucket.terraform_state.name
}

output "terraform_state_bucket_url" {
  description = "URL of the Terraform state bucket"
  value       = google_storage_bucket.terraform_state.url
}

# ========================================
# Project Configuration Outputs
# ========================================

output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP Region"
  value       = var.region
}

output "github_repo" {
  description = "GitHub repository in format: owner/repo"
  value       = var.github_repo
}

# ========================================
# Bootstrap Completion Marker
# ========================================

output "bootstrap_complete_secret_id" {
  description = "Secret ID of the bootstrap completion marker"
  value       = google_secret_manager_secret.bootstrap_complete.secret_id
}

output "bootstrap_complete" {
  description = "Indicates that bootstrap has completed successfully"
  value       = true
}

# ========================================
# GitHub Actions Setup Information
# ========================================

output "github_secrets_checklist" {
  description = "Checklist of GitHub secrets that need to be configured"
  value = <<-EOT
  
  Configure these secrets in GitHub Actions:
  https://github.com/${var.github_repo}/settings/secrets/actions
  
  Required secrets:
  ----------------
  GCP_WORKLOAD_IDENTITY_PROVIDER = ${google_iam_workload_identity_pool_provider.github.name}
  GCP_SERVICE_ACCOUNT            = ${google_service_account.github_actions.email}
  GCP_PROJECT_ID                 = ${var.project_id}
  GCP_REGION                     = ${var.region}
  GCP_CLOUD_SQL_DB_PASSWORD      = <your-database-password>
  
  Application secrets (managed via Secret Manager):
  -------------------------------------------------
  These are NOT stored in GitHub - they are managed in GCP Secret Manager
  and will be populated by the deploy workflow:
  - SECRET_KEY
  - SPOTIFY_CLIENT_ID
  - SPOTIFY_CLIENT_SECRET
  - EXERCISE_API_KEY
  - EXERCISE_API_HOST
  - GEMINI_API_KEY
  - DEFAULT_SPOTIFY_USER_PASSWORD
  
  EOT
}
