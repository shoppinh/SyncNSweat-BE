# Deploy Infrastructure Module

This module contains application infrastructure that can be safely deployed by **GitHub Actions with limited permissions**.

## Security Model

This module:
- ✅ **CAN** be run by GitHub Actions with a low-privilege service account
- ✅ **DOES NOT** manage project-level IAM or API enablement
- ✅ **DEPENDS ON** the bootstrap module having been run first by an administrator
- ✅ Uses service accounts created by bootstrap (via remote state)

## Prerequisites

### Bootstrap Module Must Be Complete

The bootstrap module **must** be run by an administrator before this module can be used:

```bash
cd ../bootstrap
./apply.sh
```

See [../bootstrap/README.md](../bootstrap/README.md) for bootstrap instructions.

### GitHub Secrets Must Be Configured

Required GitHub secrets (values from bootstrap outputs):
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_SERVICE_ACCOUNT`
- `GCP_PROJECT_ID`
- `GCP_REGION`
- `GCP_CLOUD_SQL_DB_PASSWORD`

Application secrets (deployed to Secret Manager):
- `SECRET_KEY`
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `EXERCISE_API_KEY`
- `EXERCISE_API_HOST`
- `GEMINI_API_KEY`
- `DEFAULT_SPOTIFY_USER_PASSWORD`

## Local Development

### Validation

Before running Terraform locally, validate that bootstrap is complete:

```bash
./validate.sh YOUR_PROJECT_ID
```

This script checks:
- Bootstrap completion marker exists
- Terraform state bucket exists
- Required APIs are enabled
- Service accounts exist

### Running Locally

```bash
# 1. Create configuration
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# 2. Validate bootstrap
./validate.sh YOUR_PROJECT_ID

# 3. Initialize Terraform
terraform init

# 4. Plan changes
terraform plan

# 5. Apply changes (if needed)
terraform apply
```

### Configuration

Update `terraform.tfvars` with your values:

```hcl
project_id         = "your-gcp-project-id"
region             = "us-central1"
service_name       = "syncnsweat-backend"
artifact_repo_name = "syncnsweat-repo"
db_password        = "your-secure-database-password"
```

## CI/CD Deployment

### GitHub Actions Workflow

This module is automatically deployed by GitHub Actions when changes are pushed to the main branch.

The workflow:
1. Validates bootstrap completion
2. Runs `terraform apply` in the deploy module
3. Updates secret values in Secret Manager
4. Builds and pushes Docker image
5. Deploys to Cloud Run

### Workflow File

See [../../.github/workflows/backend-deployment.yml](../../.github/workflows/backend-deployment.yml)

Key sections:
- **Bootstrap validation** - Ensures bootstrap is complete
- **Terraform apply** - Deploys infrastructure (deploy module only)
- **Secret management** - Updates secret values via `gcloud`
- **Cloud Build** - Builds and pushes container image
- **Cloud Run deployment** - Updates the service

### Service Account Permissions

The GitHub Actions service account (created by bootstrap) has these permissions:

- `roles/artifactregistry.writer` - Push Docker images
- `roles/run.developer` - Deploy Cloud Run services
- `roles/cloudsql.client` - Connect to Cloud SQL
- `roles/secretmanager.secretAccessor` - Read secrets
- `roles/secretmanager.secretVersionManager` - Update secret values
- `roles/iam.serviceAccountUser` - Use service accounts
- `roles/storage.admin` - Access Terraform state
- `roles/cloudbuild.builds.editor` - Trigger builds

**Note:** These are the minimum required permissions. The service account:
- ❌ **CANNOT** modify project IAM
- ❌ **CANNOT** enable/disable APIs
- ❌ **CANNOT** create service accounts
- ❌ **DOES NOT** have `roles/owner`

## Resources Managed

This module creates and manages:

### Cloud Run
- **Service**: `syncnsweat-backend`
- **Runtime SA**: From bootstrap (read via remote state)
- **Public access**: Unauthenticated invoker access
- **Secrets mounted**: From Secret Manager

### Cloud SQL
- **Instance**: `syncnsweat-db` (PostgreSQL 15, db-f1-micro)
- **Database**: `syncnsweat_db`
- **User**: `syncnsweat_user`

### Artifact Registry
- **Repository**: `syncnsweat-repo` (Docker format)
- **Location**: Matches region variable

### Secret Manager
- **10 secrets** (empty containers):
  - `DATABASE_URI`
  - `SECRET_KEY`
  - `SPOTIFY_CLIENT_ID`
  - `SPOTIFY_CLIENT_SECRET`
  - `SPOTIFY_REDIRECT_URL`
  - `EXERCISE_API_KEY`
  - `EXERCISE_API_HOST`
  - `API_URL`
  - `GEMINI_API_KEY`
  - `DEFAULT_SPOTIFY_USER_PASSWORD`

**Note:** Secret values are NOT managed by Terraform. They are populated by GitHub Actions using `gcloud` CLI to keep them out of Terraform state.

## Remote State

This module reads outputs from the bootstrap module via Terraform remote state:

**data.tf:**
```hcl
data "terraform_remote_state" "bootstrap" {
  backend = "gcs"
  config = {
    bucket = "syncnsweat-terraform-state-YOUR_PROJECT_ID"
    prefix = "terraform/bootstrap/state"
  }
}
```

**Available bootstrap outputs:**
- `cloudrun_service_account_email` - Used by Cloud Run
- `github_actions_service_account_email` - For reference
- `workload_identity_provider` - For GitHub Actions auth
- `project_id` - Project configuration
- `region` - Region configuration

## Making Changes

### Process

1. **Make changes** to Terraform files
2. **Test locally** (optional):
   ```bash
   terraform plan
   ```
3. **Commit and push** to trigger GitHub Actions:
   ```bash
   git add infra/deploy/
   git commit -m "Update deploy infrastructure"
   git push
   ```
4. **Monitor** GitHub Actions workflow
5. **Verify** deployment via Cloud Run URL

### Common Changes

#### Update Cloud Run configuration

Edit `main.tf`:

```hcl
resource "google_cloud_run_service" "backend" {
  # ... existing config ...
  
  template {
    spec {
      containers {
        # ... existing config ...
        
        # Add environment variables
        env {
          name  = "NEW_VAR"
          value = "value"
        }
        
        # Update resources
        resources {
          limits = {
            memory = "1Gi"
            cpu    = "2"
          }
        }
      }
    }
  }
}
```

#### Add a new secret

1. Add to `variables.tf`:
   ```hcl
   variable "secret_names" {
     default = [
       # ... existing secrets ...
       "NEW_SECRET_NAME"
     ]
   }
   ```

2. Update GitHub Actions workflow to populate the new secret

3. Apply changes via commit/push

#### Update database tier

Edit `main.tf`:

```hcl
resource "google_sql_database_instance" "postgres" {
  settings {
    tier = "db-custom-2-7680"  # 2 vCPU, 7.5 GB RAM
  }
}
```

## Outputs

Available outputs after deployment:

```bash
# Application URLs and service info
terraform output cloud_run_url
terraform output cloud_run_service_name

# Database connection
terraform output cloud_sql_connection_name
terraform output database_name
terraform output database_user

# Artifact Registry
terraform output artifact_registry_url

# Secret Manager
terraform output secret_names
terraform output secret_ids

# Bootstrap references
terraform output cloudrun_service_account_email
terraform output github_actions_service_account_email
```

## Troubleshooting

### Error: Bootstrap not complete

**Error message:**
```
Error: Failed to load state from backend
```

**Solution:**
Run the validation script to diagnose:
```bash
./validate.sh YOUR_PROJECT_ID
```

Follow the instructions to complete bootstrap or fix the issue.

### Error: 403 Permission Denied

**Possible causes:**
1. **Bootstrap not run** - Service accounts don't exist
2. **GitHub secrets not configured** - Workload Identity not working
3. **IAM propagation delay** - Wait a few minutes and retry

**Diagnosis:**
```bash
# Check if you're authenticated correctly
gcloud auth list

# Check current project
gcloud config get-value project

# Verify service account exists
gcloud iam service-accounts describe github-actions-sa-runner@PROJECT_ID.iam.gserviceaccount.com
```

### Error: Remote state not found

**Error message:**
```
Error reading backend state: storage: object doesn't exist
```

**Solution:**
The bootstrap state hasn't been migrated to GCS. An administrator needs to:
1. Complete the bootstrap apply script
2. Ensure state migration succeeded
3. Verify state file exists:
   ```bash
   gsutil ls gs://STATE_BUCKET/terraform/bootstrap/state/
   ```

### Error: Resource already exists

**Error message:**
```
Error: Error creating [...]: googleapi: Error 409: Already Exists
```

**Solution:**
Import the existing resource:
```bash
terraform import google_cloud_run_service.backend projects/PROJECT_ID/locations/REGION/services/SERVICE_NAME
```

Or if doing a fresh deployment after migration, follow the migration runbook to destroy old resources first.

### Terraform state lock

**Error message:**
```
Error: Error acquiring the state lock
```

**Solution:**
1. Check if another GitHub Actions workflow is running
2. Wait for it to complete
3. If stuck, force unlock (with caution):
   ```bash
   terraform force-unlock LOCK_ID
   ```

### Cloud Run deployment fails

**Common issues:**
1. **Image doesn't exist** - Check Artifact Registry for the image
2. **Permissions** - Cloud Run SA needs secrets access
3. **Database connection** - Verify Cloud SQL instance is running

**Debug:**
```bash
# Check Cloud Run logs
gcloud run services logs read syncnsweat-backend --project=PROJECT_ID --limit=50

# Check Cloud Run service details
gcloud run services describe syncnsweat-backend --project=PROJECT_ID --region=REGION
```

## Security Best Practices

1. **Never commit secrets** - Use Secret Manager, not environment variables in Terraform
2. **Review IAM** - Periodically review service account permissions
3. **Monitor deployments** - Set up alerts for failed deployments
4. **Rotate credentials** - Regularly rotate database passwords and API keys
5. **Least privilege** - Only grant necessary permissions to service accounts
6. **Audit logs** - Enable and review Cloud Audit Logs

## Disaster Recovery

### Backing Up Application Data

```bash
# Database backup (automatic daily backups enabled)
gcloud sql backups list --instance=syncnsweat-db --project=PROJECT_ID

# Create on-demand backup
gcloud sql backups create --instance=syncnsweat-db --project=PROJECT_ID

# Export database
gcloud sql export sql syncnsweat-db gs://YOUR_BUCKET/backup.sql \
  --database=syncnsweat_db
```

### Restoring from Backup

```bash
# Restore from backup
gcloud sql backups restore BACKUP_ID \
  --backup-instance=syncnsweat-db

# Import from export
gcloud sql import sql syncnsweat-db gs://YOUR_BUCKET/backup.sql \
  --database=syncnsweat_db
```

## Performance Optimization

### Cloud Run

- **Concurrency**: Adjust concurrent requests per instance
- **Memory**: Increase if seeing OOM errors
- **CPU**: Add more vCPUs for CPU-intensive tasks
- **Min instances**: Set min instances to reduce cold starts

### Cloud SQL

- **Instance tier**: Upgrade for more CPU/memory
- **Connection pooling**: Use in application
- **Read replicas**: Add for read-heavy workloads
- **Backup window**: Schedule during low-traffic times

## Cost Optimization

- **Cloud Run**: Use `--min-instances=0` for dev/staging
- **Cloud SQL**: Use smaller tiers for non-prod
- **Artifact Registry**: Clean up old images regularly
- **Monitoring**: Set up budget alerts

## Next Steps

After deploy module is working:

1. ✅ Monitor the first deployment in GitHub Actions
2. ✅ Verify application is accessible via Cloud Run URL
3. ✅ Test database connectivity
4. ✅ Verify secrets are properly mounted
5. ✅ Set up monitoring and alerting
6. ✅ Document any environment-specific configurations

---

**Questions or issues?** Refer to the main [MIGRATION.md](../MIGRATION.md) guide or contact your infrastructure team.
