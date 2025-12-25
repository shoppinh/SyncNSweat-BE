# ========================================
# Bootstrap Terraform Configuration
# ========================================
# This module contains infrastructure that requires elevated permissions
# and should ONLY be run manually by administrators.
#
# Resources managed here:
# - GCP API enablement
# - Service accounts (GitHub Actions, Cloud Run)
# - IAM role bindings
# - Workload Identity Federation
# - Terraform state GCS bucket
#
# DO NOT run this in CI/CD pipelines.
# ========================================

# ========================================
# GCP API Enablement
# ========================================
# Enable required GCP APIs before any other resources
resource "google_project_service" "services" {
  for_each = toset([
    "run.googleapis.com",                 # Cloud Run
    "artifactregistry.googleapis.com",    # Artifact Registry
    "iamcredentials.googleapis.com",      # IAM Credentials (for Workload Identity)
    "sqladmin.googleapis.com",            # Cloud SQL
    "secretmanager.googleapis.com",       # Secret Manager
    "compute.googleapis.com",             # Compute Engine (required for many services)
    "cloudbuild.googleapis.com",          # Cloud Build
    "sts.googleapis.com",                 # Security Token Service (for Workload Identity)
    "iam.googleapis.com",                 # IAM
    "cloudresourcemanager.googleapis.com" # Resource Manager
  ])

  project = var.project_id
  service = each.key

  # Don't disable the service if the resource is destroyed
  disable_on_destroy = false

  # Don't fail if the service is already enabled
  disable_dependent_services = false
}

# ========================================
# Service Accounts
# ========================================

# GitHub Actions CI/CD Service Account
resource "google_service_account" "github_actions" {
  account_id   = "github-actions-sa-runner"
  display_name = "GitHub Actions Service Account"
  description  = "Service account for GitHub Actions CI/CD pipeline with least-privilege permissions"
}

# Cloud Run Application Service Account
resource "google_service_account" "cloudrun" {
  account_id   = "cloudrun-sa"
  display_name = "Cloud Run Service Account"
  description  = "Service account for Cloud Run application runtime"
}

# ========================================
# IAM Role Bindings - GitHub Actions SA
# ========================================
# Principle of least privilege: Only permissions needed for deployment

resource "google_project_iam_member" "github_actions_roles" {
  for_each = toset([
    "roles/artifactregistry.repoAdmin",         # Create repository, push Docker images
    "roles/artifactregistry.writer",            # Push Docker images
    "roles/run.admin",                          # Deploy Cloud Run services and manage IAM
    "roles/cloudsql.editor",                    # Create/manage Cloud SQL instances
    "roles/secretmanager.secretVersionManager", # Create/manage secrets
    "roles/secretmanager.secretAccessor",       # Read secrets for deployment
    "roles/secretmanager.viewer",               # View Secret Manager metadata
    "roles/iam.serviceAccountUser",             # Use service accounts
    "roles/storage.objectAdmin",                # Access Terraform state bucket
    "roles/cloudbuild.builds.editor",           # Trigger Cloud Build
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}

# ========================================
# IAM Role Bindings - Cloud Run SA
# ========================================
# Runtime permissions for the application

resource "google_project_iam_member" "cloudrun_roles" {
  for_each = toset([
    "roles/cloudsql.client",             # Connect to Cloud SQL
    "roles/secretmanager.secretAccessor" # Read application secrets
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.cloudrun.email}"
}

# ========================================
# Workload Identity Federation
# ========================================
# Allows GitHub Actions to authenticate without service account keys

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions Pool"
  description               = "Workload Identity Pool for GitHub Actions authentication"

  depends_on = [
    google_project_service.services["iam.googleapis.com"],
    google_project_service.services["iamcredentials.googleapis.com"],
    google_project_service.services["sts.googleapis.com"]
  ]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Provider"
  description                        = "OIDC provider for GitHub Actions"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  # Only allow tokens from the specified repository
  attribute_condition = "assertion.repository == \"${var.github_repo}\""
}

# Bind the GitHub Actions SA to the Workload Identity Pool
resource "google_service_account_iam_member" "wif" {
  service_account_id = google_service_account.github_actions.name
  role               = "roles/iam.workloadIdentityUser"

  member = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}

# ========================================
# Terraform State Storage
# ========================================

# GCS bucket for Terraform state files
resource "google_storage_bucket" "terraform_state" {
  name          = "syncnsweat-terraform-state-${var.project_id}"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  # Keep last 5 versions
  lifecycle_rule {
    condition {
      num_newer_versions = 5
    }
    action {
      type = "Delete"
    }
  }

  # Delete old versions after 30 days
  lifecycle_rule {
    condition {
      days_since_noncurrent_time = 30
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [
    google_project_service.services["storage-api.googleapis.com"]
  ]
}

# Grant GitHub Actions SA access to state bucket
resource "google_storage_bucket_iam_member" "terraform_state_admin" {
  bucket = google_storage_bucket.terraform_state.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_actions.email}"
}

# ========================================
# Bootstrap Completion Marker
# ========================================
# This secret acts as a marker that bootstrap has completed successfully
# The deploy workflow checks for this before running

resource "google_secret_manager_secret" "bootstrap_complete" {
  secret_id = "BOOTSTRAP_COMPLETE"

  replication {
    auto {}
  }

  depends_on = [
    google_project_service.services["secretmanager.googleapis.com"]
  ]
}

resource "google_secret_manager_secret_version" "bootstrap_complete" {
  secret = google_secret_manager_secret.bootstrap_complete.id

  secret_data = jsonencode({
    completed_at      = timestamp()
    bootstrap_version = "1.0"
    project_id        = var.project_id
    region            = var.region
  })
}
