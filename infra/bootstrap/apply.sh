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

# Confirm before proceeding
read -p "Do you want to proceed with bootstrap? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
  echo "❌ Bootstrap cancelled"
  exit 0
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
echo "✅ Bootstrap Complete!"
echo "========================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Configure GitHub Secrets"
echo "   -------------------------------------"
terraform output github_secrets_checklist
echo ""

echo "2. Update Deploy Module Configuration"
echo "   -------------------------------------"
echo "   Edit infra/deploy/providers.tf and infra/deploy/data.tf"
echo "   Update the bucket name to: $BUCKET_NAME"
echo ""

echo "3. Test Deploy Module Locally (Optional)"
echo "   -------------------------------------"
echo "   cd ../deploy"
echo "   terraform init"
echo "   terraform plan"
echo ""

echo "4. Commit Changes to Git"
echo "   -------------------------------------"
echo "   git add infra/bootstrap/"
echo "   git commit -m \"Add bootstrap infrastructure\""
echo ""

echo "5. Enable GitHub Actions Deployment"
echo "   -------------------------------------"
echo "   After GitHub secrets are configured, push to trigger deployment"
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
