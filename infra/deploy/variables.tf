variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "syncnsweat-backend"
}

variable "artifact_repo_name" {
  description = "Artifact Registry repository name"
  type        = string
  default     = "syncnsweat-repo"
}

variable "db_password" {
  description = "Database password for Cloud SQL user"
  type        = string
  sensitive   = true
}

# Secret names to create in Secret Manager
# Values are populated by CI/CD, not Terraform
variable "secret_names" {
  description = "List of secret names to ensure exist in Secret Manager"
  type        = list(string)
  default = [
    "DATABASE_URI",
    "SECRET_KEY",
    "SPOTIFY_CLIENT_ID",
    "SPOTIFY_CLIENT_SECRET",
    "SPOTIFY_REDIRECT_URL",
    "EXERCISE_API_KEY",
    "EXERCISE_API_HOST",
    "API_URL",
    "GEMINI_API_KEY",
    "DEFAULT_SPOTIFY_USER_PASSWORD"
  ]
}
