variable "project_id" {}
variable "region" {}

variable "service_name" {
  default = "syncnsweat-backend"
}

variable "artifact_repo_name" {
  default = "syncnsweat-repo"
}

variable "github_repo" {
  description = "username/repo"
}

variable "db_password" {
  sensitive = true
}

# Note: Secrets are managed via gcloud CLI in CI/CD
# This keeps secret values out of Terraform state
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