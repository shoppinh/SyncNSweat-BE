provider "google" {
  project = var.project_id
  region  = var.region
}

# Remote state backend for better security and collaboration
# Note: Uncomment AFTER running bootstrap.sh
# terraform {
#   backend "gcs" {
#     bucket = "sync-n-sweat-terraform-state"
#     prefix = "terraform/state"
#   }
# }
