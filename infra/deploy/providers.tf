provider "google" {
  project = var.project_id
  region  = var.region
}

# Remote backend for Terraform state
terraform {
  backend "gcs" {
    bucket = "syncnsweat-terraform-state-syncnsweat-prod-101"  # Update with actual bucket name
    prefix = "terraform/deploy/state"
  }
}
