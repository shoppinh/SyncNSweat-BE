#!/bin/bash
set -euo pipefail

# ========================================
# Bootstrap Infrastructure Apply Script
# ========================================
# This script applies the bootstrap Terraform module and migrates
# the state to GCS bucket for persistent storage.
#
# IMPORTANT: This script requires elevated permissions and should
# ONLY be run by administrators, NEVER in CI/CD pipelines.
#
# Prerequisites:
# - gcloud CLI installed and authenticated as admin
# - Terraform >= 1.5.0 installed
# - Project owner or equivalent permissions
# - terraform.tfvars file configured with your values
# ========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================"
echo "Bootstrap Infrastructure Setup"
echo "========================================"
echo ""
echo "⚠️  WARNING: This script requires elevated permissions"
echo "    and should only be run by administrators."
echo ""
echo "📋 This script will:"
echo "   1. Initialize Terraform with local state"
echo "   2. Apply bootstrap infrastructure"
echo "   3. Migrate state to GCS bucket"
echo "   4. Display GitHub secrets configuration"
echo ""

# Check if terraform.tfvars exists
if [ ! -f "$SCRIPT_DIR/terraform.tfvars" ]; then
  echo "❌ Error: terraform.tfvars not found"
  echo ""
  echo "Please create terraform.tfvars with your configuration:"
  echo "  cp terraform.tfvars.example terraform.tfvars"
  echo "  # Edit terraform.tfvars with your values"
  echo ""
  exit 1
fi


echo ""
echo "========================================"
echo "Step 1: Initialize Terraform (local state)"
echo "========================================"
cd "$SCRIPT_DIR"
terraform init
echo "✅ Terraform initialized with local state"
echo ""

echo "========================================"
echo "Step 2: Terraform Plan"
echo "========================================"
terraform plan -out=tfplan
echo ""

read -p "Review the plan above. Apply these changes? (yes/no): " apply_confirm
if [ "$apply_confirm" != "yes" ]; then
  echo "❌ Bootstrap cancelled"
  rm -f tfplan
  exit 0
fi

echo ""
echo "========================================"
echo "Step 3: Apply Bootstrap Infrastructure"
echo "========================================"
terraform apply tfplan
rm -f tfplan
echo ""
echo "✅ Bootstrap infrastructure created"
echo ""

# Get the bucket name from Terraform output
BUCKET_NAME=$(terraform output -raw terraform_state_bucket)
PROJECT_ID=$(terraform output -raw project_id)

echo "========================================"
echo "Step 4: Migrate State to GCS"
echo "========================================"
echo ""
echo "📦 State bucket: $BUCKET_NAME"
echo ""

# Uncomment the backend configuration in providers.tf
if grep -q "^# terraform {" providers.tf; then
  echo "   Enabling GCS backend configuration..."
  
  # Create a backup of providers.tf
  cp providers.tf providers.tf.backup
  
  # Uncomment the backend block and update bucket name
  sed -i.bak \
    -e 's/^# terraform {/terraform {/' \
    -e 's/^#   backend "gcs" {/  backend "gcs" {/' \
    -e "s|^#     bucket = \".*\"|    bucket = \"$BUCKET_NAME\"|" \
    -e 's/^#     prefix = "terraform\/bootstrap\/state"/    prefix = "terraform\/bootstrap\/state"/' \
    -e 's/^#   }/  }/' \
    -e 's/^# }/}/' \
    providers.tf
  
  rm -f providers.tf.bak
  
  echo "   ✅ Backend configuration enabled"
fi

echo "   Migrating state to GCS..."
terraform init -migrate-state -force-copy
echo ""
echo "✅ State migrated to gs://$BUCKET_NAME/terraform/bootstrap/state"
echo ""

# Clean up local state files
if [ -f terraform.tfstate ]; then
  mv terraform.tfstate terraform.tfstate.local.backup
  echo "   📦 Local state backed up to terraform.tfstate.local.backup"
fi

if [ -f terraform.tfstate.backup ]; then
  rm -f terraform.tfstate.backup
fi

echo ""
echo "========================================"
echo "Step 5: Verify Bootstrap Completion"
echo "========================================"
echo ""

# Verify the bootstrap completion marker secret exists
if gcloud secrets describe BOOTSTRAP_COMPLETE --project="$PROJECT_ID" &>/dev/null; then
  echo "✅ Bootstrap completion marker created successfully"
  echo ""
  echo "   Bootstrap metadata:"
  gcloud secrets versions access latest \
    --secret=BOOTSTRAP_COMPLETE \
    --project="$PROJECT_ID" | jq .
else
  echo "⚠️  Warning: Bootstrap completion marker not found"
fi

echo ""
echo "========================================"
echo "Step 6: GitHub Secrets Configuration"
echo "========================================"
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
  echo "❌ Error: GitHub CLI (gh) is not installed"
  echo ""
  echo "Install it with:"
  echo "  brew install gh"
  echo ""
  echo "Then manually configure secrets at:"
  echo "  https://github.com/$(terraform output -raw github_repo)/settings/secrets/actions"
  echo ""
  terraform output github_secrets_checklist
  exit 1
fi

# Check if logged in to gh
if ! gh auth status &> /dev/null; then
  echo "⚠️  Not logged in to GitHub CLI"
  echo ""
  read -p "Login to GitHub CLI now? (yes/no): " gh_login
  if [ "$gh_login" == "yes" ]; then
    gh auth login
  else
    echo ""
    echo "❌ Cannot configure secrets without authentication"
    echo ""
    echo "Login later with: gh auth login"
    echo "Then manually configure secrets at:"
    echo "  https://github.com/$(terraform output -raw github_repo)/settings/secrets/actions"
    echo ""
    terraform output github_secrets_checklist
    exit 1
  fi
fi

GITHUB_REPO=$(terraform output -raw github_repo)
WORKLOAD_IDENTITY_PROVIDER=$(terraform output -raw workload_identity_provider)
SERVICE_ACCOUNT_EMAIL=$(terraform output -raw github_actions_service_account_email)
REGION=$(terraform output -raw region)

echo "   Configuring GitHub secrets for repository: $GITHUB_REPO"
echo ""

# Set secrets using gh CLI
echo "   Setting GCP_PROJECT_ID..."
echo "$PROJECT_ID" | gh secret set GCP_PROJECT_ID --repo="$GITHUB_REPO"

echo "   Setting GCP_REGION..."
echo "$REGION" | gh secret set GCP_REGION --repo="$GITHUB_REPO"

echo "   Setting GCP_WORKLOAD_IDENTITY_PROVIDER..."
echo "$WORKLOAD_IDENTITY_PROVIDER" | gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER --repo="$GITHUB_REPO"

echo "   Setting GCP_SERVICE_ACCOUNT..."
echo "$SERVICE_ACCOUNT_EMAIL" | gh secret set GCP_SERVICE_ACCOUNT --repo="$GITHUB_REPO"


echo ""
echo "   ✅ GitHub secrets configured successfully"


echo "========================================"
echo "Step 7: Update Deploy Module Configuration"
echo "========================================"
echo ""
echo "   Updating infra/deploy/providers.tf and data.tf..."

DEPLOY_DIR="$SCRIPT_DIR/../deploy"

# Update providers.tf with the bucket name
if [ -f "$DEPLOY_DIR/providers.tf" ]; then
  # Backup the file
  cp "$DEPLOY_DIR/providers.tf" "$DEPLOY_DIR/providers.tf.backup"
  
  # Update bucket name in backend configuration
  sed -i.bak "s|bucket = \".*\"|bucket = \"$BUCKET_NAME\"|" "$DEPLOY_DIR/providers.tf"
  rm -f "$DEPLOY_DIR/providers.tf.bak"
  
  echo "   ✅ Updated providers.tf with bucket: $BUCKET_NAME"
else
  echo "   ⚠️  Warning: $DEPLOY_DIR/providers.tf not found"
fi

# Update data.tf with the bucket name
if [ -f "$DEPLOY_DIR/data.tf" ]; then
  # Backup the file
  cp "$DEPLOY_DIR/data.tf" "$DEPLOY_DIR/data.tf.backup"
  
  # Update bucket name in remote state configuration
  sed -i.bak "s|bucket = \".*\"|bucket = \"$BUCKET_NAME\"|" "$DEPLOY_DIR/data.tf"
  rm -f "$DEPLOY_DIR/data.tf.bak"
  
  echo "   ✅ Updated data.tf with bucket: $BUCKET_NAME"
else
  echo "   ⚠️  Warning: $DEPLOY_DIR/data.tf not found"
fi

echo ""
echo "========================================"
echo "Step 8: Initialize and Validate Deploy Module"
echo "========================================"
echo ""

cd "$DEPLOY_DIR"
echo "   Initializing deploy module..."
terraform init

echo ""
echo "   Validating deploy module configuration..."
terraform validate

echo ""
echo "   ✅ Deploy module initialized and validated"

cd "$SCRIPT_DIR"

echo ""
echo "========================================"
echo "Step 9: Commit Changes to Git"
echo "========================================"
echo ""

read -p "Commit changes to git? (yes/no): " git_confirm
if [ "$git_confirm" == "yes" ]; then
  cd "$SCRIPT_DIR/../.."
  
  git add infra/bootstrap/providers.tf
  git add infra/bootstrap/main.tf
  git add infra/deploy/providers.tf
  git add infra/deploy/data.tf

  
  echo "   ✅ Changes committed to git"
  echo ""
  echo "   Next: Push to GitHub to enable deployment"
  echo "   Command: git push origin main"
else
  echo "   ⚠️  Changes not committed - remember to commit manually"
fi

echo ""
echo "========================================"
echo "✅ Bootstrap Complete!"
echo "========================================"
echo ""
echo ""

echo "========================================"
echo "📋 Summary & Next Steps"
echo "========================================"
echo ""
echo "✅ Completed:"
echo "   • Bootstrap infrastructure deployed"
echo "   • State migrated to GCS bucket"
echo "   • Deploy module configured and validated"
echo ""
echo "📋 Next Steps:"
echo ""


echo "1. Push Changes to GitHub"
echo "   -------------------------------------"
echo "   git push origin main"
echo ""

echo "2. Enable GitHub Actions Deployment"
echo "   -------------------------------------"
echo "   After GitHub secrets are configured, GitHub Actions will"
echo "   automatically deploy infrastructure on push to main branch"
echo ""

echo "========================================"
echo "⚠️  IMPORTANT REMINDERS"
echo "========================================"
echo ""
echo "• The providers.tf file has been modified to enable the GCS backend"
echo "• Future changes to bootstrap require manual approval and admin access"
echo "• DO NOT run bootstrap in CI/CD pipelines"
echo "• The deploy module can now be safely run by GitHub Actions"
echo ""