# Infrastructure Migration Guide

This guide provides step-by-step instructions for migrating from the monolithic infrastructure configuration to the security-focused bootstrap/deploy split architecture.

## Table of Contents

1. [Overview](#overview)
2. [Migration Strategy](#migration-strategy)
3. [Prerequisites](#prerequisites)
4. [Pre-Migration Checklist](#pre-migration-checklist)
5. [Migration Steps](#migration-steps)
6. [Post-Migration Verification](#post-migration-verification)
7. [Rollback Procedure](#rollback-procedure)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### What's Changing?

**Before (Monolithic):**
- Single Terraform module managing everything
- IAM, APIs, and application infrastructure together
- Bootstrap runs in CI/CD (insecure)
- Service account has excessive permissions

**After (Separated):**
```
infra/
├── bootstrap/    ← IAM, APIs, service accounts (ADMIN ONLY)
└── deploy/       ← Application infrastructure (CI/CD SAFE)
```

### Why This Change?

✅ **Security**: IAM changes require manual admin approval  
✅ **Least Privilege**: CI/CD service account has minimal permissions  
✅ **Safety**: Reduced blast radius for automated deployments  
✅ **Compliance**: Follows GCP security best practices  
✅ **Auditability**: Clear separation of concerns  

### Architecture

```
┌─────────────────────────────────────────────────┐
│ BOOTSTRAP (Admin Only, Manual Execution)       │
│ ─────────────────────────────────────────────── │
│ • Enable GCP APIs                               │
│ • Create Service Accounts                       │
│ • Assign IAM Roles                              │
│ • Configure Workload Identity                   │
│ • Create State Bucket                           │
│                                                 │
│ State: gs://BUCKET/terraform/bootstrap/state    │
└─────────────────────────────────────────────────┘
                        ↓
                   (outputs)
                        ↓
┌─────────────────────────────────────────────────┐
│ DEPLOY (CI/CD, GitHub Actions)                  │
│ ─────────────────────────────────────────────── │
│ • Cloud Run Service                             │
│ • Cloud SQL Database                            │
│ • Artifact Registry                             │
│ • Secret Manager Secrets                        │
│                                                 │
│ State: gs://BUCKET/terraform/deploy/state       │
└─────────────────────────────────────────────────┘
```

---

## Migration Strategy

### Approach: Destroy and Recreate

We will:
1. **Backup** all current state and data
2. **Destroy** existing infrastructure
3. **Run bootstrap** (creates IAM, APIs, service accounts)
4. **Run deploy** (creates application infrastructure)
5. **Restore data** (secrets, database)
6. **Verify** everything works

**Note:** This approach ensures clean separation and avoids complex state manipulation.

### Downtime Expected

- **Estimated**: 30-60 minutes
- **Impact**: Application unavailable during migration
- **Mitigation**: Schedule during maintenance window

---

## Prerequisites

### Required Access

- **GCP Project Owner** or equivalent permissions
- **GitHub Repository Admin** access
- **gcloud CLI** authenticated as admin
- **Terraform** >= 1.5.0 installed

### Required Tools

```bash
# Verify tools are installed
terraform --version   # >= 1.5.0
gcloud --version
git --version
jq --version
```

### Authentication

```bash
# Authenticate with admin account
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Verify permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:YOUR_EMAIL"
```

---

## Pre-Migration Checklist

### 1. Communication

- [ ] Notify team of maintenance window
- [ ] Update status page (if applicable)
- [ ] Schedule migration during low-traffic period

### 2. Backup Current State

```bash
cd infra

# Run backup script
./backup.sh YOUR_PROJECT_ID syncnsweat-db
```

This creates:
- `backups/TIMESTAMP/terraform.tfstate` - Current Terraform state
- `backups/TIMESTAMP/remote-terraform.tfstate` - GCS state backup
- `backups/TIMESTAMP/sql-backup.log` - Cloud SQL backup log
- `backups/TIMESTAMP/SECRET_VALUES.md` - Template for secrets

**CRITICAL**: Populate `SECRET_VALUES.md` with actual secret values:

```bash
# For each secret, retrieve and document the value
gcloud secrets versions access latest --secret=SECRET_KEY --project=YOUR_PROJECT_ID
gcloud secrets versions access latest --secret=SPOTIFY_CLIENT_ID --project=YOUR_PROJECT_ID
# ... repeat for all 10 secrets
```

### 3. Export Database (Additional Safety)

```bash
# Export database to Cloud Storage
gsutil mb gs://YOUR_PROJECT_ID-migration-backup

gcloud sql export sql syncnsweat-db \
  gs://YOUR_PROJECT_ID-migration-backup/pre-migration-$(date +%Y%m%d).sql \
  --database=syncnsweat_db \
  --project=YOUR_PROJECT_ID
```

### 4. Document Current Configuration

```bash
cd infra

# Save current Terraform outputs
terraform output -json > ../migration-outputs-backup.json

# List current resources
terraform state list > ../migration-resources-backup.txt
```

### 5. Verify Backups

- [ ] Terraform state files exist in `backups/`
- [ ] Cloud SQL backup completed successfully
- [ ] Database export in Cloud Storage
- [ ] All secret values documented in `SECRET_VALUES.md`
- [ ] Current outputs saved

---

## Migration Steps

### Step 1: Destroy Existing Infrastructure

```bash
cd infra

# Review what will be destroyed
terraform plan -destroy

# Destroy (POINT OF NO RETURN)
terraform destroy -auto-approve \
  -var="project_id=YOUR_PROJECT_ID" \
  -var="region=YOUR_REGION" \
  -var="github_repo=YOUR_ORG/YOUR_REPO" \
  -var="db_password=PLACEHOLDER"
```

**Expected duration:** 5-10 minutes

Verify destruction:
```bash
# Check Cloud Run
gcloud run services list --project=YOUR_PROJECT_ID

# Check Cloud SQL
gcloud sql instances list --project=YOUR_PROJECT_ID

# Should show no resources (or only manually created ones)
```

### Step 2: Move Old Configuration to Archive

```bash
cd ..  # Back to repository root

# Create archive directory
mkdir -p infra-old

# Move old Terraform files
git mv infra/*.tf infra-old/
git mv infra/terraform.tfstate* infra-old/ 2>/dev/null || true
git mv infra/terraform.tfvars* infra-old/ 2>/dev/null || true

# Keep these in infra/:
# - backup.sh (already there)
# - backups/ (already there)
# - bootstrap/ (new)
# - deploy/ (new)

# Commit the move
git add -A
git commit -m "Archive old infrastructure configuration"
```

### Step 3: Run Bootstrap Module

```bash
cd infra/bootstrap

# Create configuration
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars
nano terraform.tfvars
```

Set these values:
```hcl
project_id  = "your-gcp-project-id"
region      = "us-central1"
github_repo = "your-org/your-repo"
```

Run bootstrap:
```bash
# Execute automated bootstrap script
./apply.sh
```

This will:
1. Initialize Terraform (local state)
2. Show plan for review
3. Apply infrastructure (after confirmation)
4. Migrate state to GCS
5. Display GitHub secrets checklist

**Expected duration:** 5-10 minutes

### Step 4: Configure GitHub Secrets

The bootstrap output provides a checklist. Configure these secrets at:
`https://github.com/YOUR_ORG/YOUR_REPO/settings/secrets/actions`

**Infrastructure secrets** (from bootstrap outputs):
```bash
GCP_WORKLOAD_IDENTITY_PROVIDER = <from terraform output>
GCP_SERVICE_ACCOUNT            = <from terraform output>
GCP_PROJECT_ID                 = <your project ID>
GCP_REGION                     = <your region>
GCP_CLOUD_SQL_DB_PASSWORD      = <choose secure password>
```

**Application secrets** (from SECRET_VALUES.md backup):
```bash
SECRET_KEY
SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET
EXERCISE_API_KEY
EXERCISE_API_HOST
GEMINI_API_KEY
DEFAULT_SPOTIFY_USER_PASSWORD
```

### Step 5: Update Deploy Module Configuration

```bash
cd ../deploy

# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars
nano terraform.tfvars
```

Set these values:
```hcl
project_id         = "your-gcp-project-id"
region             = "us-central1"
service_name       = "syncnsweat-backend"
artifact_repo_name = "syncnsweat-repo"
db_password        = "YOUR_SECURE_DB_PASSWORD"  # Same as GitHub secret
```

Update bucket references:
```bash
# Get bucket name from bootstrap
cd ../bootstrap
BUCKET_NAME=$(terraform output -raw terraform_state_bucket)
cd ../deploy

# Update providers.tf
sed -i.bak "s/syncnsweat-terraform-state-syncnsweat-106/${BUCKET_NAME}/" providers.tf

# Update data.tf
sed -i.bak "s/syncnsweat-terraform-state-syncnsweat-106/${BUCKET_NAME}/" data.tf

# Remove backup files
rm -f providers.tf.bak data.tf.bak
```

### Step 6: Run Deploy Module (Local Test)

```bash
# Validate bootstrap completion
./validate.sh YOUR_PROJECT_ID

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Apply
terraform apply -auto-approve
```

**Expected duration:** 10-15 minutes

### Step 7: Restore Secret Values

```bash
# The deploy module created empty secret containers
# Now populate them with actual values

# Using your SECRET_VALUES.md backup:
echo -n "YOUR_SECRET_KEY_VALUE" | gcloud secrets versions add SECRET_KEY \
  --data-file=- --project=YOUR_PROJECT_ID

echo -n "YOUR_SPOTIFY_CLIENT_ID" | gcloud secrets versions add SPOTIFY_CLIENT_ID \
  --data-file=- --project=YOUR_PROJECT_ID

# Repeat for all secrets...
# Or use the update script from the GitHub Actions workflow
```

**Tip:** You can get the actual DATABASE_URI from deploy outputs:
```bash
terraform output database_name
terraform output database_user
terraform output cloud_sql_connection_name
```

### Step 8: Restore Database Data (If Needed)

If you had existing data:

```bash
# Import from export
gcloud sql import sql syncnsweat-db \
  gs://YOUR_PROJECT_ID-migration-backup/pre-migration-YYYYMMDD.sql \
  --database=syncnsweat_db \
  --project=YOUR_PROJECT_ID
```

Or restore from backup:
```bash
# List backups
gcloud sql backups list --instance=syncnsweat-db --project=YOUR_PROJECT_ID

# Restore from backup
gcloud sql backups restore BACKUP_ID \
  --backup-instance=syncnsweat-db \
  --project=YOUR_PROJECT_ID
```

### Step 9: Commit Infrastructure Changes

```bash
cd ../../  # Back to repository root

# Add new infrastructure
git add infra/bootstrap/
git add infra/deploy/
git add infra/backup.sh
git add infra/MIGRATION.md

# Commit
git commit -m "Add bootstrap/deploy split infrastructure

- Separate IAM/services (bootstrap) from application infra (deploy)
- Bootstrap runs manually by admin only
- Deploy runs in CI/CD with limited permissions
- Follows GCP security best practices"

# Push to trigger GitHub Actions
git push origin feature/IaC-implementation
```

### Step 10: Monitor GitHub Actions Deployment

1. Go to: `https://github.com/YOUR_ORG/YOUR_REPO/actions`
2. Watch the "Build and Deploy to Cloud Run" workflow
3. Verify all steps complete successfully:
   - ✅ Bootstrap validation
   - ✅ Terraform apply (deploy module)
   - ✅ Secret updates
   - ✅ Container build
   - ✅ Cloud Run deployment

---

## Post-Migration Verification

### 1. Verify Infrastructure

```bash
cd infra/deploy

# Check deploy state
terraform show

# Verify outputs
terraform output
```

### 2. Verify Cloud Run Service

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe syncnsweat-backend \
  --project=YOUR_PROJECT_ID \
  --region=YOUR_REGION \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# Test health endpoint
curl "$SERVICE_URL/health"
```

### 3. Verify Database Connectivity

```bash
# Check Cloud Run logs for database connection
gcloud run services logs read syncnsweat-backend \
  --project=YOUR_PROJECT_ID \
  --region=YOUR_REGION \
  --limit=50
```

### 4. Verify Secrets

```bash
# List secrets
gcloud secrets list --project=YOUR_PROJECT_ID

# Verify secret values (be careful - this outputs sensitive data)
# gcloud secrets versions access latest --secret=SECRET_KEY --project=YOUR_PROJECT_ID
```

### 5. Test Application Functionality

- [ ] Can access application URL
- [ ] Health check returns 200
- [ ] Database operations work
- [ ] Spotify integration works
- [ ] Exercise API integration works
- [ ] Authentication works

### 6. Verify Bootstrap State

```bash
cd ../bootstrap

# Verify bootstrap state is in GCS
gsutil ls gs://YOUR_STATE_BUCKET/terraform/bootstrap/state/

# Check bootstrap outputs
terraform output
```

### 7. Verify GitHub Actions

- [ ] Workflow completes successfully
- [ ] No permission errors (403)
- [ ] Terraform apply succeeds
- [ ] Container builds and pushes
- [ ] Cloud Run deployment succeeds

---

## Rollback Procedure

If something goes wrong during migration:

### Option 1: Restore from Old Infrastructure (If Not Destroyed Yet)

```bash
cd infra-old

# Re-apply old configuration
terraform init
terraform apply
```

### Option 2: Restore from Backup (After Destruction)

```bash
# Restore Terraform state
cd infra-old
terraform state push ../backups/TIMESTAMP/terraform.tfstate

# Re-apply infrastructure
terraform apply

# Restore database
gcloud sql backups restore BACKUP_ID --backup-instance=syncnsweat-db

# Restore secrets manually from SECRET_VALUES.md backup
```

### Option 3: Roll Forward (Fix Issues)

If the issue is minor:
1. Fix the configuration
2. Re-run `terraform apply`
3. Verify fixes

---

## Troubleshooting

### Error: Bootstrap validation failed

**Symptom:** Deploy workflow fails with "Bootstrap not complete"

**Solution:**
```bash
cd infra/bootstrap
terraform apply
./apply.sh  # Ensure state migration completed
```

### Error: 403 Permission Denied in GitHub Actions

**Cause:** Workload Identity or IAM not configured correctly

**Solution:**
```bash
# Verify GitHub secrets are set
# Go to: https://github.com/YOUR_ORG/YOUR_REPO/settings/secrets/actions

# Verify Workload Identity binding
gcloud iam service-accounts describe github-actions-sa-runner@PROJECT_ID.iam.gserviceaccount.com

# Re-apply bootstrap if needed
cd infra/bootstrap
terraform apply -target=google_service_account_iam_member.wif
```

### Error: Remote state not found

**Symptom:** Deploy module can't read bootstrap outputs

**Solution:**
```bash
# Verify bootstrap state exists
gsutil ls gs://YOUR_STATE_BUCKET/terraform/bootstrap/state/

# If missing, re-run bootstrap state migration
cd infra/bootstrap
terraform init -migrate-state
```

### Error: Database connection failed

**Symptom:** Cloud Run can't connect to Cloud SQL

**Solution:**
```bash
# Verify Cloud SQL instance is running
gcloud sql instances describe syncnsweat-db --project=PROJECT_ID

# Verify DATABASE_URI secret is correct
gcloud secrets versions access latest --secret=DATABASE_URI --project=PROJECT_ID

# Should be format: postgresql://USER:PASS@/DB?host=/cloudsql/INSTANCE_CONNECTION_NAME

# Update if incorrect
cd infra/deploy
terraform output cloud_sql_connection_name
# Use this to construct correct DATABASE_URI
```

### Error: Cloud Run deployment failed

**Symptom:** Image not found or deployment fails

**Solution:**
```bash
# Check if image exists in Artifact Registry
gcloud artifacts docker images list REGION-docker.pkg.dev/PROJECT_ID/syncnsweat-repo

# If missing, trigger rebuild
git commit --allow-empty -m "Trigger rebuild"
git push

# Check Cloud Build logs
gcloud builds list --project=PROJECT_ID --limit=5
```

### Error: Secrets not accessible

**Symptom:** Cloud Run can't read secrets from Secret Manager

**Solution:**
```bash
# Verify Cloud Run SA has access
gcloud secrets get-iam-policy SECRET_KEY --project=PROJECT_ID

# Should show cloudrun-sa@PROJECT_ID.iam.gserviceaccount.com with secretAccessor role

# Re-apply deploy if missing
cd infra/deploy
terraform apply -target=google_secret_manager_secret_iam_member.cloudrun_access
```

---

## Success Criteria

Migration is complete when:

- [ ] Bootstrap module applied successfully by admin
- [ ] Deploy module applied successfully (local test)
- [ ] GitHub Actions workflow completes without errors
- [ ] Application is accessible and functional
- [ ] Database connectivity verified
- [ ] All secrets properly configured
- [ ] No 403 permission errors in CI/CD
- [ ] Old `infra-old/` directory archived
- [ ] Documentation updated
- [ ] Team notified of completion

---

## Next Steps After Migration

1. **Delete old infrastructure archive** (after validation period):
   ```bash
   git rm -r infra-old/
   git commit -m "Remove old infrastructure archive"
   ```

2. **Set up monitoring**:
   - Cloud Run metrics
   - Cloud SQL metrics
   - GitHub Actions alerts

3. **Document runbooks**:
   - How to make bootstrap changes (admin only)
   - How to deploy application changes (CI/CD)
   - Emergency procedures

4. **Security review**:
   - Audit IAM permissions
   - Review secret rotation policy
   - Set up Cloud Audit Logs

5. **Optimize costs**:
   - Right-size Cloud Run and Cloud SQL
   - Set up budget alerts
   - Clean up unused resources

---

## Support

**Questions or issues during migration?**

- Review [infra/bootstrap/README.md](bootstrap/README.md)
- Review [infra/deploy/README.md](deploy/README.md)
- Check GitHub Actions logs
- Check GCP Cloud Logging

**Emergency contact:** Your infrastructure team lead

---

**Migration Guide Version:** 1.0  
**Last Updated:** December 24, 2025  
**Maintained By:** Infrastructure Team
