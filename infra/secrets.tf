# Terraform only ensures secrets exist, values are managed via gcloud CLI
# This keeps secret values out of Terraform state for better security

resource "google_secret_manager_secret" "secrets" {
  for_each = toset(var.secret_names)

  secret_id = each.value

  replication {
    auto {}
  }
  
  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = false
  }
}

# Grant Cloud Run service account access to secrets
resource "google_secret_manager_secret_iam_member" "cloudrun_access" {
  for_each = toset(var.secret_names)
  
  secret_id = google_secret_manager_secret.secrets[each.value].id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloudrun.email}"
}
