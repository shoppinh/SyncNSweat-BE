# Sync & Sweat Backend

This is the backend API for Sync & Sweat, built with FastAPI and PostgreSQL, deployed on Google Cloud Platform.

## Table of Contents

- [Getting Started (Local Development)](#getting-started-local-development)
- [Infrastructure Management with Terraform](#infrastructure-management-with-terraform)
- [API Documentation](#api-documentation)
- [Running Tests](#running-tests)
- [CI/CD Pipeline](#cicd-pipeline)

## Getting Started (Local Development)

1. Create and activate a virtual environment:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

Create a `.env` file with the following variables:
```
DATABASE_URL=postgresql://username:password@localhost:5432/syncnsweat
SECRET_KEY=your_secret_key
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
EXERCISEDB_API_KEY=your_exercisedb_api_key
```

4. Run database migrations:

```bash
alembic upgrade head
```

5. Start the development server:

```bash
uvicorn app.main:app --reload
```

## API Documentation

Once the server is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Running Tests

To run the tests:

```bash
pytest
```

To run tests with coverage:

```bash
pytest --cov=app
```

## Infrastructure Management with Terraform

> **⚠️ ACCESS CONTROL**: Infrastructure changes should only be performed by team members with **DevOps/Platform Engineer** role who have the required GCP IAM permissions (`roles/editor` or higher).

### Prerequisites

Before managing infrastructure, ensure you have:

1. **GCP Access**: Project Owner or Editor role
2. **Tools Installed**:
   ```bash
   # Check if tools are installed
   gcloud --version
   terraform --version
   ```
3. **Authenticated to GCP**:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

### Initial Infrastructure Bootstrap (One-Time Setup)

The bootstrap process creates the GCS bucket for Terraform state storage and sets up the foundation infrastructure.

> **Note**: This only needs to be done **once** when setting up the project for the first time or when migrating to remote state.

```bash
cd infra

# Run the automated bootstrap script
./bootstrap.sh
```

**What the bootstrap does:**
1. ✅ Creates GCS bucket for Terraform state (`sync-n-sweat-terraform-state`)
2. ✅ Enables versioning and security settings on the bucket
3. ✅ Initializes Terraform with local state
4. ✅ Creates the state bucket infrastructure via Terraform
5. ✅ Migrates state from local to remote GCS backend
6. ✅ Updates `providers.tf` with active backend configuration

**Manual Bootstrap (Alternative):**

If you prefer to run steps manually:

```bash
cd infra

# 1. Create the GCS bucket
gsutil mb -p YOUR_PROJECT_ID -l us-central1 gs://sync-n-sweat-terraform-state
gsutil versioning set on gs://sync-n-sweat-terraform-state

# 2. Initialize Terraform (local state first)
terraform init

# 3. Create the bucket infrastructure resource
terraform apply \
  -var="project_id=YOUR_PROJECT_ID" \
  -var="region=us-central1" \
  -var="github_repo=shoppinh/SyncNSweat-BE" \
  -var="db_password=temp-password" \
  -target=google_storage_bucket.terraform_state

# 4. Uncomment the backend configuration in providers.tf
# Edit providers.tf and uncomment the terraform backend block

# 5. Migrate to remote state
terraform init -migrate-state
```

### Local Infrastructure Development

When working with Terraform locally, follow these practices:

#### 1. Update terraform.tfvars

Create or update your local `terraform.tfvars`:

```bash
cd infra
cp terraform.tfvars terraform.tfvars.local  # Create local copy

# Edit terraform.tfvars.local with your values
nano terraform.tfvars.local
```

Example configuration:
```hcl
project_id  = "your-gcp-project-id"
region      = "us-central1"
github_repo = "shoppinh/SyncNSweat-BE"
db_password = "secure-database-password"
```

#### 2. Plan Infrastructure Changes

Always run `terraform plan` before applying changes:

```bash
cd infra

# Preview changes
terraform plan -var-file="terraform.tfvars.local"

# Or using command-line variables
terraform plan \
  -var="project_id=YOUR_PROJECT_ID" \
  -var="region=us-central1" \
  -var="github_repo=shoppinh/SyncNSweat-BE" \
  -var="db_password=YOUR_DB_PASSWORD"
```

#### 3. Apply Infrastructure Changes

After reviewing the plan:

```bash
# Apply changes
terraform apply -var-file="terraform.tfvars.local"

# Or with auto-approve (use cautiously!)
terraform apply -auto-approve -var-file="terraform.tfvars.local"
```

#### 4. Validate Infrastructure

```bash
# Validate configuration syntax
terraform validate

# Format code
terraform fmt -recursive

# Check current state
terraform show
```

#### 5. Target Specific Resources

When you only want to update specific resources:

```bash
# Apply changes to specific resource
terraform apply -target=google_cloud_run_service.backend

# Plan for specific module
terraform plan -target=module.database
```

### Managing Secrets (Infrastructure Team Only)

Secrets are managed outside of Terraform to keep them out of state files. See [SECRETS_MANAGEMENT.md](SECRETS_MANAGEMENT.md) for details.

To manually update a secret in GCP Secret Manager:

```bash
# Add a new secret version
echo -n "new-secret-value" | gcloud secrets versions add SECRET_NAME \
  --project="YOUR_PROJECT_ID" \
  --data-file=-

# View secret versions
gcloud secrets versions list SECRET_NAME --project="YOUR_PROJECT_ID"

# Access secret value (requires secretAccessor role)
gcloud secrets versions access latest --secret="SECRET_NAME"
```

### Infrastructure Best Practices

1. **Always Run Plan First**: Never apply without reviewing the plan
2. **Use Remote State**: The GCS backend is configured - don't disable it
3. **Lock State During Changes**: Terraform automatically handles state locking
4. **Review Diffs Carefully**: Pay attention to resource replacements (recreations)
5. **Coordinate with Team**: Check with team before making major infrastructure changes
6. **Document Changes**: Update this README or create an ADR for significant changes
7. **Test in Non-Prod First**: If possible, test infrastructure changes in a dev/staging environment

### Common Terraform Commands

```bash
# Initialize/update providers
terraform init -upgrade

# View current state
terraform state list
terraform state show <resource_name>

# Import existing resource
terraform import <resource_type>.<name> <resource_id>

# Remove resource from state (doesn't delete it)
terraform state rm <resource_name>

# Refresh state from actual infrastructure
terraform refresh

# Destroy specific resource
terraform destroy -target=<resource_name>

# View outputs
terraform output
terraform output -json
```

### Troubleshooting

**State Lock Issues:**
```bash
# If state is locked and you need to force unlock (use carefully!)
terraform force-unlock LOCK_ID
```

**Backend Configuration Issues:**
```bash
# Reconfigure backend
terraform init -reconfigure

# Migrate to different backend
terraform init -migrate-state
```

**Provider Issues:**
```bash
# Re-authenticate to GCP
gcloud auth application-default login

# Update providers
terraform init -upgrade
```

## CI/CD Pipeline

Infrastructure and application deployments are automated via GitHub Actions. See [.github/workflows/backend-deployment.yml](../.github/workflows/backend-deployment.yml).

**Pipeline Flow:**
1. 🔐 Authenticate to GCP via Workload Identity Federation
2. 🔑 Update secrets in GCP Secret Manager from GitHub Secrets
3. 🏗️ Run Terraform to provision/update infrastructure
4. 🐳 Build Docker image via Cloud Build
5. 🚀 Deploy to Cloud Run with secret references

**Required GitHub Secrets:**
- See [SECRETS_MANAGEMENT.md](SECRETS_MANAGEMENT.md) for the complete list

### Manual Deployment Trigger

To manually trigger a deployment:
1. Go to **Actions** tab in GitHub
2. Select **"Build and Deploy to Cloud Run"** workflow
3. Click **"Run workflow"**
4. Select branch and confirm
