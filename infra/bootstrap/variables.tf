variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository in format: owner/repo"
  type        = string
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "syncnsweat-backend"
}
