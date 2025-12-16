resource "google_sql_database_instance" "postgres" {
  name             = "syncnsweat-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-f1-micro"
  }
}

resource "google_sql_database" "db" {
  name     = "syncnsweat_db"
  instance = google_sql_database_instance.postgres.name
}

resource "google_sql_user" "user" {
  name     = "syncnsweat_user"
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}
