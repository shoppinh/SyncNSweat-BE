#!/bin/bash
set -euo pipefail

# Pre-Migration Backup Script
# This script creates backups of:
# 1. Terraform state files
# 2. Cloud SQL database
# 3. Secret Manager secret values (template for manual documentation)
#
# Run this script BEFORE starting the infrastructure migration

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${SCRIPT_DIR}/backups/$(date +%Y%m%d_%H%M%S)"
PROJECT_ID="${1:-}"
SQL_INSTANCE_NAME="${2:-syncnsweat-db}"

echo "================================================"
echo "Pre-Migration Backup Script"
echo "================================================"
echo ""

# Validate inputs
if [ -z "$PROJECT_ID" ]; then
  echo "❌ Error: PROJECT_ID is required"
  echo "Usage: ./backup.sh <PROJECT_ID> [SQL_INSTANCE_NAME]"
  echo "Example: ./backup.sh syncnsweat-106 syncnsweat-db"
  exit 1
fi

echo "📋 Configuration:"
echo "   Project ID: $PROJECT_ID"
echo "   SQL Instance: $SQL_INSTANCE_NAME"
echo "   Backup Directory: $BACKUP_DIR"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# ========================================
# Step 1: Backup Terraform State
# ========================================
echo "📦 Step 1: Backing up Terraform state..."

if [ -f "$SCRIPT_DIR/terraform.tfstate" ]; then
  cp "$SCRIPT_DIR/terraform.tfstate" "$BACKUP_DIR/terraform.tfstate"
  echo "   ✅ Local state backed up"
fi

if [ -f "$SCRIPT_DIR/terraform.tfstate.backup" ]; then
  cp "$SCRIPT_DIR/terraform.tfstate.backup" "$BACKUP_DIR/terraform.tfstate.backup"
  echo "   ✅ Local state backup backed up"
fi

# Download remote state from GCS
echo "   Downloading remote state from GCS..."
if gsutil ls "gs://syncnsweat-terraform-state-${PROJECT_ID}/terraform/state/default.tfstate" &>/dev/null; then
  gsutil cp "gs://syncnsweat-terraform-state-${PROJECT_ID}/terraform/state/default.tfstate" \
    "$BACKUP_DIR/remote-terraform.tfstate" || echo "   ⚠️  Warning: Could not download remote state"
  echo "   ✅ Remote state downloaded"
else
  echo "   ℹ️  No remote state found in GCS"
fi

echo ""

# ========================================
# Step 2: Cloud SQL Backup
# ========================================
echo "📦 Step 2: Creating Cloud SQL backup..."

BACKUP_NAME="pre-migration-$(date +%Y%m%d-%H%M%S)"

echo "   Creating on-demand backup: $BACKUP_NAME"
if gcloud sql backups create \
  --instance="$SQL_INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --description="Pre-migration backup before bootstrap/deploy split" \
  2>&1 | tee "$BACKUP_DIR/sql-backup.log"; then
  echo "   ✅ Cloud SQL backup created: $BACKUP_NAME"
  echo "   📝 Backup log saved to: $BACKUP_DIR/sql-backup.log"
else
  echo "   ⚠️  Warning: Cloud SQL backup failed (check log above)"
fi

# List recent backups
echo ""
echo "   Recent Cloud SQL backups:"
gcloud sql backups list --instance="$SQL_INSTANCE_NAME" --project="$PROJECT_ID" --limit=5 \
  | tee "$BACKUP_DIR/sql-backup-list.txt"

echo ""

# Optional: Export database to Cloud Storage
echo "   💡 Consider also exporting database to GCS for additional safety:"
echo "      gcloud sql export sql $SQL_INSTANCE_NAME gs://YOUR-BUCKET/pre-migration-export.sql \\"
echo "        --database=syncnsweat_db --project=$PROJECT_ID"
echo ""

# ========================================
# Step 3: Document Secret Values
# ========================================
echo "📦 Step 3: Creating secret values documentation template..."

cat > "$BACKUP_DIR/SECRET_VALUES.md" <<'EOF'
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

These can be retrieved from: https://github.com/YOUR_ORG/YOUR_REPO/settings/secrets/actions

EOF

echo "   ✅ Secret values template created: $BACKUP_DIR/SECRET_VALUES.md"
echo ""
echo "   🔐 NEXT STEP: Manually populate SECRET_VALUES.md with actual values"
echo "      Run the retrieval script in the template or retrieve each secret individually"
echo ""

# ========================================
# Step 4: Create Backup Summary
# ========================================
cat > "$BACKUP_DIR/BACKUP_SUMMARY.txt" <<EOF
Backup Summary
==============

Timestamp: $(date)
Project ID: $PROJECT_ID
SQL Instance: $SQL_INSTANCE_NAME

Backup Location: $BACKUP_DIR

Files Backed Up:
----------------
$(ls -lh "$BACKUP_DIR")

Next Steps:
-----------
1. ✅ Terraform state backed up
2. ✅ Cloud SQL backup created
3. ⚠️  MANUAL: Populate SECRET_VALUES.md with actual secret values
4. ⚠️  MANUAL: Verify all backups are complete before proceeding

Restoration Instructions:
-------------------------
If you need to rollback after migration:

1. Restore Terraform state:
   terraform state push $BACKUP_DIR/terraform.tfstate

2. Restore Cloud SQL from backup:
   gcloud sql backups restore [BACKUP_ID] --backup-instance=$SQL_INSTANCE_NAME

3. Restore secrets:
   Use SECRET_VALUES.md to recreate secrets in Secret Manager

EOF

# ========================================
# Summary
# ========================================
echo "================================================"
echo "✅ Backup Complete!"
echo "================================================"
echo ""
echo "📁 All backups saved to: $BACKUP_DIR"
echo ""
cat "$BACKUP_DIR/BACKUP_SUMMARY.txt"
echo ""
echo "⚠️  IMPORTANT: Before proceeding with migration:"
echo "   1. Populate SECRET_VALUES.md with actual secret values from GCP"
echo "   2. Verify Cloud SQL backup completed successfully"
echo "   3. Store backups in a secure location"
echo "   4. Consider creating an additional database export to GCS"
echo ""
echo "================================================"
