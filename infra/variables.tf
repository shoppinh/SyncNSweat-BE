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

variable "secrets" {
  description = "Map of secret_name => secret_value"
  type        = map(string)
  sensitive   = true
}