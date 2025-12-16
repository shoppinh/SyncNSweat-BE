# Enable required GCP APIs
# These must be enabled before other resources can be created
resource "google_project_service" "services" {
  for_each = toset([
    "run.googleapis.com",              # Cloud Run
    "artifactregistry.googleapis.com", # Artifact Registry
    "iamcredentials.googleapis.com",   # IAM Credentials (for Workload Identity)
    "sqladmin.googleapis.com",         # Cloud SQL
    "secretmanager.googleapis.com",    # Secret Manager
    "compute.googleapis.com",          # Compute Engine (required for many services)
    "cloudbuild.googleapis.com",       # Cloud Build
    "sts.googleapis.com",              # Security Token Service (for Workload Identity)
    "iam.googleapis.com",              # IAM
    "cloudresourcemanager.googleapis.com" # Resource Manager
  ])

  project = var.project_id
  service = each.key

  # Don't disable the service if the resource is destroyed
  disable_on_destroy = false

  # Don't fail if the service is already enabled
  disable_dependent_services = false
}
