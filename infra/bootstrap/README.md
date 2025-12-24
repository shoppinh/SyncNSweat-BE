# Bootstrap Infrastructure Module

This module contains infrastructure that requires elevated permissions and should **ONLY be run manually by administrators**.

## ⚠️ Security Notice

**DO NOT run this module in CI/CD pipelines.**

This module manages:
- GCP API enablement
- Service account creation
- Project-level IAM bindings
- Workload Identity Federation setup
- Terraform state storage

These operations require `roles/owner` or equivalent permissions and should be carefully reviewed before execution.

## Prerequisites

### Required Permissions

The user/service account running this module must have:
- `roles/owner` on the GCP project, OR
- A custom role with these permissions:
  - `resourcemanager.projects.setIamPolicy`
  - `iam.serviceAccounts.create`
  - `iam.serviceAccounts.setIamPolicy`
  - `serviceusage.services.enable`
  - `storage.buckets.create`
  - `secretmanager.secrets.create`

### Required Tools

- **Terraform** >= 1.5.0
- **gcloud CLI** installed and authenticated
- **jq** (for JSON parsing in scripts)

### Authentication

```bash
# Authenticate with your admin account
gcloud auth login

# Set the active project
gcloud config set project YOUR_PROJECT_ID
```

## Initial Setup

### 1. Create Configuration File

```bash
cd infra/bootstrap
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
project_id  = "your-gcp-project-id"
region      = "us-central1"
github_repo = "your-username/your-repo"  # e.g., "shoppinh/SyncNSweat-BE"
```

### 2. Run Bootstrap Script

The `apply.sh` script automates the bootstrap process:

```bash
./apply.sh
```

This script will:
1. Initialize Terraform with local state
2. Show a plan for review
3. Apply the infrastructure (after confirmation)
4. Migrate state to GCS bucket
5. Display GitHub secrets configuration checklist

### 3. Configure GitHub Secrets

After bootstrap completes, configure these secrets in GitHub:

**Navigate to:** `https://github.com/YOUR_ORG/YOUR_REPO/settings/secrets/actions`

Required secrets (values from Terraform outputs):
- `GCP_WORKLOAD_IDENTITY_PROVIDER` - Workload Identity provider resource name
- `GCP_SERVICE_ACCOUNT` - GitHub Actions service account email
- `GCP_PROJECT_ID` - Your GCP project ID
- `GCP_REGION` - Your GCP region
- `GCP_BUCKET_NAME` - Terraform state bucket name
- `GCP_CLOUD_SQL_DB_PASSWORD` - Database password (choose a secure value)

Application secrets (store in GitHub, deployed to Secret Manager by CI/CD):
- `SECRET_KEY` - Application secret key
- `SPOTIFY_CLIENT_ID` - Spotify API client ID
- `SPOTIFY_CLIENT_SECRET` - Spotify API client secret
- `EXERCISE_API_KEY` - Exercise API key
- `EXERCISE_API_HOST` - Exercise API host
- `GEMINI_API_KEY` - Gemini API key
- `DEFAULT_SPOTIFY_USER_PASSWORD` - Default user password

You can get the GitHub secrets checklist from Terraform output:

```bash
terraform output github_secrets_checklist
```

### 4. Update Deploy Module Configuration

Update the bucket name in deploy module files:

**infra/deploy/providers.tf:**
```hcl
terraform {
  backend "gcs" {
    bucket = "syncnsweat-terraform-state-YOUR_PROJECT_ID"  # Update this
    prefix = "terraform/deploy/state"
  }
}
```

**infra/deploy/data.tf:**
```hcl
data "terraform_remote_state" "bootstrap" {
  backend = "gcs"
  config = {
    bucket = "syncnsweat-terraform-state-YOUR_PROJECT_ID"  # Update this
    prefix = "terraform/bootstrap/state"
  }
}
```

## Making Changes to Bootstrap

### Process for Updates

1. **Review changes carefully** - Bootstrap changes affect IAM and security
2. **Test in a dev environment first** (if available)
3. **Create a plan:**
   ```bash
   terraform plan
   ```
4. **Get approval** from team lead or security team
5. **Apply changes:**
   ```bash
   terraform apply
   ```
6. **Verify outputs:**
   ```bash
   terraform output
   ```

### Common Changes

#### Adding a new API

Edit `main.tf` and add to the `google_project_service.services` list:

```hcl
resource "google_project_service" "services" {
  for_each = toset([
    # ...existing APIs...
    "newapi.googleapis.com",  # Add new API here
  ])
  # ...
}
```

#### Adding permissions to GitHub Actions SA

Edit `main.tf` and add to the `google_project_iam_member.github_actions_roles` list:

```hcl
resource "google_project_iam_member" "github_actions_roles" {
  for_each = toset([
    # ...existing roles...
    "roles/new.role",  # Add new role here
  ])
  # ...
}
```

## Outputs

Key outputs available after bootstrap:

```bash
# Service account emails
terraform output github_actions_service_account_email
terraform output cloudrun_service_account_email

# Workload Identity
terraform output workload_identity_provider

# State management
terraform output terraform_state_bucket

# Configuration
terraform output project_id
terraform output region

# Bootstrap status
terraform output bootstrap_complete
```

## Troubleshooting

### Error: APIs not enabled

If you see errors about APIs not being enabled:

```bash
# Manually enable required APIs
gcloud services enable \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project=YOUR_PROJECT_ID
```

Then retry `terraform apply`.

### Error: Permission denied

Ensure you're authenticated with an account that has sufficient permissions:

```bash
# Check current account
gcloud auth list

# Check project
gcloud config get-value project

# Re-authenticate if needed
gcloud auth login
```

### State migration failed

If state migration fails:

1. Check that the GCS bucket was created:
   ```bash
   gsutil ls -p YOUR_PROJECT_ID
   ```

2. Verify bucket permissions:
   ```bash
   gsutil iam get gs://BUCKET_NAME
   ```

3. Retry migration:
   ```bash
   terraform init -migrate-state
   ```

### Bootstrap completion marker missing

If the `BOOTSTRAP_COMPLETE` secret isn't created:

```bash
# Check secret exists
gcloud secrets describe BOOTSTRAP_COMPLETE --project=YOUR_PROJECT_ID

# Recreate if missing
terraform apply -target=google_secret_manager_secret.bootstrap_complete -target=google_secret_manager_secret_version.bootstrap_complete
```

## Security Best Practices

1. **Limit access** - Only grant bootstrap access to administrators
2. **Audit changes** - Review all changes before applying
3. **Use version control** - Track all changes in Git
4. **Separate environments** - Use different projects for dev/staging/prod
5. **Rotate credentials** - Periodically review and rotate service account keys (though we use Workload Identity, not keys)
6. **Monitor IAM** - Set up alerts for IAM policy changes

## Disaster Recovery

### Backing Up Bootstrap State

```bash
# Download current state
gsutil cp gs://YOUR_STATE_BUCKET/terraform/bootstrap/state/default.tfstate ./bootstrap-state-backup.tfstate

# Save outputs
terraform output -json > bootstrap-outputs-backup.json
```

### Restoring Bootstrap

If you need to rebuild the bootstrap infrastructure:

1. Ensure you have the state backup
2. Run `terraform init`
3. Import state if needed: `terraform state push bootstrap-state-backup.tfstate`
4. Verify with `terraform plan` (should show no changes)
5. If resources were deleted, run `terraform apply`

## Resources Created

This module creates:

- **10 GCP APIs** enabled
- **2 Service Accounts** (GitHub Actions, Cloud Run)
- **~10 IAM bindings** for service accounts
- **1 Workload Identity Pool** for GitHub Actions
- **1 Workload Identity Provider** (OIDC for GitHub)
- **1 GCS bucket** for Terraform state
- **1 Secret** (BOOTSTRAP_COMPLETE marker)

## Next Steps

After bootstrap is complete:

1. ✅ Configure GitHub secrets (see output from apply script)
2. ✅ Update deploy module bucket references
3. ✅ Test deploy module locally (optional)
4. ✅ Commit bootstrap infrastructure to Git
5. ✅ Push to GitHub to trigger deploy workflow

---

**Questions or issues?** Refer to the main [MIGRATION.md](../MIGRATION.md) guide or contact your infrastructure team.
