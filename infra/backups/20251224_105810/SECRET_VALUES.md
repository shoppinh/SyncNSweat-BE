# Secret Values Backup

**⚠️ SECURITY WARNING: This file will contain sensitive values. Handle with care.**

Document all current secret values from GCP Secret Manager before destroying infrastructure.

## How to populate this file:

```bash
# For each secret, retrieve and document the current value
gcloud secrets versions access latest --secret=SECRET_NAME --project=PROJECT_ID
```

## Secrets to Document:

### 1. DATABASE_URI
```
# Current value from Secret Manager:
postgresql://...
```

### 2. SECRET_KEY
```
# Current value from Secret Manager:
(your-secret-key-here)
```

### 3. SPOTIFY_CLIENT_ID
```
# Current value from Secret Manager:
(your-client-id-here)
```

### 4. SPOTIFY_CLIENT_SECRET
```
# Current value from Secret Manager:
(your-client-secret-here)
```

### 5. SPOTIFY_REDIRECT_URL
```
# Current value from Secret Manager:
(your-redirect-url-here)
```

### 6. EXERCISE_API_KEY
```
# Current value from Secret Manager:
(your-api-key-here)
```

### 7. EXERCISE_API_HOST
```
# Current value from Secret Manager:
(your-api-host-here)
```

### 8. API_URL
```
# Current value from Secret Manager:
(your-api-url-here)
```

### 9. GEMINI_API_KEY
```
# Current value from Secret Manager:
(your-gemini-key-here)
```

### 10. DEFAULT_SPOTIFY_USER_PASSWORD
```
# Current value from Secret Manager:
(your-password-here)
```

## Automated Retrieval Script

You can use this script to retrieve all values (CAREFUL - this outputs sensitive data):

```bash
PROJECT_ID="your-project-id"
SECRETS=("DATABASE_URI" "SECRET_KEY" "SPOTIFY_CLIENT_ID" "SPOTIFY_CLIENT_SECRET" \
         "SPOTIFY_REDIRECT_URL" "EXERCISE_API_KEY" "EXERCISE_API_HOST" "API_URL" \
         "GEMINI_API_KEY" "DEFAULT_SPOTIFY_USER_PASSWORD")

for secret in "${SECRETS[@]}"; do
  echo "=== $secret ==="
  gcloud secrets versions access latest --secret="$secret" --project="$PROJECT_ID" || echo "Not found"
  echo ""
done
```

## GitHub Secrets

Also document GitHub Actions secrets (stored in GitHub, not GCP):
- GCP_PROJECT_ID
- GCP_REGION
- GCP_WORKLOAD_IDENTITY_PROVIDER
- GCP_SERVICE_ACCOUNT
- GCP_CLOUD_SQL_DB_PASSWORD
- GCP_BUCKET_NAME

These can be retrieved from: https://github.com/YOUR_ORG/YOUR_REPO/settings/secrets/actions

