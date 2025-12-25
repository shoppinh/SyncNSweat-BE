# ========================================
# Deploy Terraform Configuration
# ========================================
# This module contains application infrastructure that can be safely
# deployed by GitHub Actions with limited permissions.
#
# Resources managed here:
# - Cloud Run services
# - Cloud SQL databases
# - Artifact Registry repositories
# - Secret Manager secrets (containers only, not values)
#
# Prerequisites:
# - Bootstrap module must be applied first by an administrator
# - All required APIs must be enabled via bootstrap
# - Service accounts must exist via bootstrap
# ========================================

# ========================================
# Cloud Run Service
# ========================================

resource "google_cloud_run_service" "backend" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  template {
    spec {
      containers {
        # Placeholder image - actual image deployed via CI/CD
        image = "gcr.io/cloudrun/hello"
        ports {
          container_port = 8000
        }
      }
      # Use service account from bootstrap
      service_account_name = data.terraform_remote_state.bootstrap.outputs.cloudrun_service_account_email
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  # No depends_on for google_project_service - APIs enabled in bootstrap
}

# Allow unauthenticated access to Cloud Run service
resource "google_cloud_run_service_iam_member" "invoker_allUsers" {
  project  = var.project_id
  location = var.region
  service  = google_cloud_run_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ========================================
# Cloud SQL Database
# ========================================

resource "google_sql_database_instance" "postgres" {
  name             = "syncnsweat-db"
  database_version = "POSTGRES_15"
  region           = var.region
  project          = var.project_id

  settings {
    tier = "db-f1-micro"
  }

  # No depends_on for google_project_service - API enabled in bootstrap
}

resource "google_sql_database" "db" {
  name     = "syncnsweat_db"
  instance = google_sql_database_instance.postgres.name
  project  = var.project_id
}

resource "google_sql_user" "user" {
  name     = "syncnsweat_user"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
  project  = var.project_id
}

# ========================================
# Artifact Registry
# ========================================

resource "google_artifact_registry_repository" "docker" {
  repository_id = var.artifact_repo_name
  location      = var.region
  format        = "DOCKER"
  project       = var.project_id

  # No depends_on for google_project_service - API enabled in bootstrap
}

# ========================================
# Secret Manager
# ========================================
# Terraform only ensures secrets exist; values are managed via gcloud CLI
# This keeps secret values out of Terraform state for better security

resource "google_secret_manager_secret" "secrets" {
  for_each = toset(var.secret_names)

  secret_id = each.value
  project   = var.project_id

  replication {
    auto {}
  }

  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = true
  }

  # No depends_on for google_project_service - API enabled in bootstrap
}

# ========================================
# Cloud Build Logs Bucket
# ========================================

resource "google_storage_bucket" "cloudbuild_logs" {
  name          = "${var.project_id}-cloudbuild-logs"
  location      = var.region
  project       = var.project_id
  force_destroy = true

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}
