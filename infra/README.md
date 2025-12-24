# Infrastructure Overview

This directory contains a **security-focused, production-grade GCP infrastructure** configuration split into two independent Terraform modules:

## Architecture

```
infra/
├── bootstrap/          ← IAM, APIs, Service Accounts (ADMIN ONLY)
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── providers.tf
│   ├── versions.tf
│   ├── apply.sh       ← Automated bootstrap script
│   └── README.md      ← Full documentation
│
├── deploy/             ← Application Infrastructure (CI/CD SAFE)
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── providers.tf
│   ├── versions.tf
│   ├── data.tf        ← Reads bootstrap outputs
│   ├── validate.sh    ← Pre-flight checks
│   └── README.md      ← Full documentation
│
├── backup.sh           ← Pre-migration backup script
└── MIGRATION.md        ← Complete migration guide
```

## Quick Start

### For Administrators (First Time Setup)

```bash
# 1. Run bootstrap (creates IAM, APIs, service accounts)
cd infra/bootstrap
./apply.sh

# 2. Configure GitHub secrets with bootstrap outputs
# See output from apply.sh for values

# 3. Deploy application infrastructure
cd ../deploy
terraform init
terraform apply
```

### For Developers (Daily Operations)

Application deployments happen automatically via GitHub Actions:

```bash
# Make changes to your code
git commit -m "Your changes"
git push

# GitHub Actions automatically:
# - Validates bootstrap completion
# - Runs terraform apply (deploy module)
# - Updates secrets
# - Builds container
# - Deploys to Cloud Run
```

## Security Model

### Bootstrap Module (Admin Only)

**Who can run:** Project owners / infrastructure admins only  
**When to run:** Manually, during initial setup or when IAM changes needed  
**Where:** Local machine with admin credentials

**Manages:**
- ✅ GCP API enablement
- ✅ Service account creation
- ✅ Project-level IAM role bindings
- ✅ Workload Identity Federation
- ✅ Terraform state bucket

**State:** `gs://STATE_BUCKET/terraform/bootstrap/state`

### Deploy Module (CI/CD Safe)

**Who can run:** GitHub Actions with limited service account  
**When to run:** Automatically on every push to main  
**Where:** GitHub Actions runners

**Manages:**
- ✅ Cloud Run services
- ✅ Cloud SQL databases
- ✅ Artifact Registry repositories
- ✅ Secret Manager secrets (containers only, not values)

**State:** `gs://STATE_BUCKET/terraform/deploy/state`

**Permissions (Least Privilege):**
- `roles/artifactregistry.writer` - Push Docker images
- `roles/run.developer` - Deploy Cloud Run
- `roles/cloudsql.client` - Database access
- `roles/secretmanager.secretAccessor` - Read secrets
- `roles/secretmanager.secretVersionManager` - Update secret values
- `roles/iam.serviceAccountUser` - Use service accounts
- `roles/storage.admin` - Access state bucket
- `roles/cloudbuild.builds.editor` - Trigger builds

**Explicitly CANNOT:**
- ❌ Modify project IAM
- ❌ Enable/disable APIs
- ❌ Create service accounts
- ❌ Change Workload Identity

## Resources Created

### Bootstrap Module

- **10 GCP APIs** enabled
- **2 Service Accounts** (github-actions-sa-runner, cloudrun-sa)
- **~10 IAM role bindings** for service accounts
- **1 Workload Identity Pool** + Provider
- **1 GCS bucket** for Terraform state
- **1 Secret** (BOOTSTRAP_COMPLETE marker)

### Deploy Module

- **1 Cloud Run service** (syncnsweat-backend)
- **1 Cloud SQL instance** (PostgreSQL 15, db-f1-micro)
- **1 Artifact Registry repository** (Docker format)
- **10 Secret Manager secrets** (empty containers)
- **Resource-level IAM bindings** (Cloud Run SA → secrets)

## Documentation

- **[bootstrap/README.md](bootstrap/README.md)** - How to run bootstrap, make IAM changes, troubleshooting
- **[deploy/README.md](deploy/README.md)** - How deploy works, CI/CD integration, local development
- **[MIGRATION.md](MIGRATION.md)** - Complete migration guide from old infrastructure

## GitHub Actions Integration

The [.github/workflows/backend-deployment.yml](../.github/workflows/backend-deployment.yml) workflow:

1. **Validates** bootstrap completion
2. **Runs** `terraform apply` in deploy module
3. **Updates** secret values in Secret Manager
4. **Builds** Docker image via Cloud Build
5. **Deploys** to Cloud Run

## Common Tasks

### Make IAM Changes (Admin)

```bash
cd infra/bootstrap
# Edit main.tf to add roles/APIs
terraform plan
terraform apply
```

### Update Application Infrastructure (Developer)

```bash
cd infra/deploy
# Edit main.tf to change Cloud Run config
git commit -m "Update Cloud Run memory"
git push  # Triggers GitHub Actions
```

### Add a New Secret

```bash
# 1. Add to deploy/variables.tf
cd infra/deploy
# Edit variable "secret_names" default list

# 2. Commit and push
git commit -m "Add new secret"
git push

# 3. Update GitHub Actions workflow to populate value
# Edit ../.github/workflows/backend-deployment.yml
# Add to "Update Secret Values" step
```

### Troubleshooting

**403 Permission Denied in GitHub Actions:**
```bash
# Check bootstrap completion
cd infra/deploy
./validate.sh YOUR_PROJECT_ID

# Verify GitHub secrets are configured
# https://github.com/YOUR_ORG/YOUR_REPO/settings/secrets/actions
```

**Remote state not found:**
```bash
# Verify bootstrap state exists
gsutil ls gs://YOUR_STATE_BUCKET/terraform/bootstrap/state/

# Re-run bootstrap if needed
cd infra/bootstrap
./apply.sh
```

**Cloud Run deployment failed:**
```bash
# Check logs
gcloud run services logs read syncnsweat-backend \
  --project=YOUR_PROJECT_ID \
  --limit=50
```

## Best Practices

### DO ✅

- Run bootstrap manually with admin credentials
- Review all bootstrap changes before applying
- Use GitHub Actions for deploy operations
- Keep secrets in Secret Manager, not Terraform
- Monitor Cloud Audit Logs for IAM changes
- Rotate credentials regularly
- Test changes in dev/staging first

### DON'T ❌

- Run bootstrap in CI/CD pipelines
- Grant `roles/owner` to CI service accounts
- Store secrets in Terraform state
- Make IAM changes without review
- Bypass the validation checks
- Commit sensitive values to Git

## Migration from Old Infrastructure

If you're migrating from the monolithic infrastructure:

1. **Read** [MIGRATION.md](MIGRATION.md) completely
2. **Run** `backup.sh` to backup current state
3. **Follow** step-by-step migration guide
4. **Validate** everything works before deleting old config

## State Management

### Bootstrap State
- **Location:** `gs://STATE_BUCKET/terraform/bootstrap/state`
- **Backend:** GCS (migrated after initial apply)
- **Access:** Admin only

### Deploy State
- **Location:** `gs://STATE_BUCKET/terraform/deploy/state`
- **Backend:** GCS (from initial apply)
- **Access:** GitHub Actions + admins

### State Bucket Features
- ✅ Versioning enabled (keep last 5 versions)
- ✅ Lifecycle rules (delete after 30 days)
- ✅ Uniform bucket-level access
- ✅ IAM-based access control

## Security Features

1. **Workload Identity Federation** - No service account keys
2. **Least Privilege IAM** - Minimal permissions for CI/CD
3. **Separation of Concerns** - IAM separate from application
4. **Secret Isolation** - Values not in Terraform state
5. **Audit Trail** - All IAM changes require manual approval
6. **State Encryption** - GCS encryption at rest

## Cost Optimization

Current configuration uses:
- **Cloud Run:** Pay-per-use, min instances = 0
- **Cloud SQL:** db-f1-micro (lowest tier)
- **Artifact Registry:** Pay for storage only
- **Secret Manager:** Free tier (< 6 secrets × 10K accesses)

**Estimated monthly cost:** $10-30 (depends on usage)

## Monitoring & Alerts

Recommended setup:
- Cloud Run metrics (latency, errors, instances)
- Cloud SQL metrics (CPU, connections, storage)
- GitHub Actions alerts (failed deployments)
- Budget alerts (unexpected cost increases)
- Cloud Audit Logs (IAM changes)

## Support & Contact

- **Bootstrap issues:** Contact infrastructure admin
- **Deploy issues:** Check GitHub Actions logs
- **Migration help:** See [MIGRATION.md](MIGRATION.md)
- **Emergency:** Refer to rollback procedures

## Version History

- **v1.0** (Dec 2025) - Initial bootstrap/deploy split
- Security-focused refactoring
- Production-grade GCP best practices
- Automated CI/CD pipeline

## License

[Your License Here]

---

**Last Updated:** December 24, 2025  
**Maintained By:** Infrastructure Team  
**Architecture:** Bootstrap/Deploy Split with Least-Privilege IAM
