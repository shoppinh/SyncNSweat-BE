provider "google" {
  project = var.project_id
  region  = var.region
}

# Remote state backend for better security and collaboration
# Note: Uncomment AFTER running bootstrap.sh
terraform {
  backend "gcs" {
    bucket = "syncnsweat-terraform-state-syncnsweat-106"
    prefix = "terraform/state"
  }
}
