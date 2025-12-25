# ========================================
# Remote State Data Source
# ========================================
# Read outputs from the bootstrap module to get service account emails,
# Workload Identity provider, and other bootstrap configuration

data "terraform_remote_state" "bootstrap" {
  backend = "gcs"

  config = {
    bucket = "syncnsweat-terraform-state-syncnsweat-100"  # Update with actual bucket name
    prefix = "terraform/bootstrap/state"
  }
}

# ========================================
# Bootstrap Outputs (for reference)
# ========================================
# Available from data.terraform_remote_state.bootstrap.outputs:
# - github_actions_service_account_email
# - cloudrun_service_account_email
# - workload_identity_provider
# - terraform_state_bucket
# - project_id
# - region
# - bootstrap_complete
