locals {
  secret_names = toset(nonsensitive(keys(var.secrets)))
}

resource "google_secret_manager_secret" "secrets" {
  for_each = local.secret_names

  secret_id = each.value

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "versions" {
  for_each = local.secret_names

  secret      = google_secret_manager_secret.secrets[each.value].id
  secret_data = var.secrets[each.value]
}
