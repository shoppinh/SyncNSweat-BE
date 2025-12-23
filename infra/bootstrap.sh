#!/bin/bash

# Bootstrap script to initialize Terraform remote state
# This must be run ONCE before enabling the GCS backend in providers.tf

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}╔════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║  Terraform State Backend Bootstrap Script     ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════╝${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if gh (GitHub CLI) is installed (used to set repo secrets)
if ! command -v gh &> /dev/null; then
    echo -e "${YELLOW}Note: gh (GitHub CLI) not found. Skipping GitHub secret bootstrap unless you install gh.${NC}"
    GH_CLI_AVAILABLE=false
else
    GH_CLI_AVAILABLE=true
fi

# Check if terraform is installed
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}Error: terraform is not installed${NC}"
    echo "Install it from: https://www.terraform.io/downloads"
    exit 1
fi

# Get project ID, region,github_repo, db_password and bucket name from terraform.tfvars or prompt
if [ -f "terraform.tfvars" ]; then
    PROJECT_ID=$(grep 'project_id' terraform.tfvars | cut -d'"' -f2)
    REGION=$(grep 'region' terraform.tfvars | cut -d'"' -f2)
    GITHUB_REPO=$(grep 'github_repo' terraform.tfvars | cut -d'"' -f2)
    DB_PASSWORD=$(grep 'db_password' terraform.tfvars | cut -d'"' -f2)
fi

if [ -z "$PROJECT_ID" ]; then
    read -p "Enter GCP Project ID: " PROJECT_ID
fi

if [ -z "$REGION" ]; then
    read -p "Enter GCP Region (e.g., us-central1): " REGION
fi

if [ -z "$GITHUB_REPO" ]; then
    read -p "Enter GitHub Repository (e.g., user/repo): " GITHUB_REPO
fi

if [ -z "$DB_PASSWORD" ]; then
    read -s -p "Enter Database Password: " DB_PASSWORD
    echo ""
fi


BUCKET_NAME="syncnsweat-terraform-state-$(echo $PROJECT_ID | tr ':' '-' | tr '.' '-')"

echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  GitHub Repo: $GITHUB_REPO"
echo "  Database Password: [HIDDEN]"
echo "  Bucket Name: $BUCKET_NAME"
echo ""

read -p "Continue with bootstrap? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Bootstrap cancelled"
    exit 0
fi

echo ""
echo -e "${YELLOW}Step 1: Checking if bucket already exists...${NC}"
if gsutil ls -b "gs://${BUCKET_NAME}" &> /dev/null; then
    echo -e "${GREEN}✓ Bucket already exists${NC}"
    BUCKET_EXISTS=true
else
    echo -e "${YELLOW}Creating bucket...${NC}"
    gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://${BUCKET_NAME}"
    echo -e "${GREEN}✓ Bucket created${NC}"
    BUCKET_EXISTS=true
fi

echo ""
echo -e "${YELLOW}Step 2: Enabling versioning on bucket...${NC}"
gsutil versioning set on "gs://${BUCKET_NAME}"
echo -e "${GREEN}✓ Versioning enabled${NC}"

echo ""
echo -e "${YELLOW}Step 3: Setting uniform bucket-level access...${NC}"
gsutil uniformbucketlevelaccess set on "gs://${BUCKET_NAME}"
echo -e "${GREEN}✓ Uniform bucket-level access enabled${NC}"

echo ""
echo -e "${YELLOW}Step 4: Running Terraform init (without backend)...${NC}"
terraform init
echo -e "${GREEN}✓ Terraform initialized${NC}"

echo ""
echo -e "${YELLOW}Step 5: Creating infrastructure (including bucket resource)...${NC}"
if [ "$BUCKET_EXISTS" = true ]; then
    echo -e "${YELLOW}Bucket already exists — importing into Terraform state...${NC}"
    # Ensure terraform is initialized (safe to run again)
    terraform init -var="project_id=$PROJECT_ID" \
      -var="region=$REGION" \
      -var="github_repo=$GITHUB_REPO" \
      -var="db_password=$DB_PASSWORD"
    if terraform import google_storage_bucket.terraform_state "${BUCKET_NAME}"; then
        echo -e "${GREEN}✓ Bucket imported into Terraform state${NC}"
    else
        echo -e "${RED}Error importing bucket into Terraform state${NC}"
        exit 1
    fi
else
    terraform apply \
      -var="project_id=$PROJECT_ID" \
      -var="region=$REGION" \
      -var="github_repo=$GITHUB_REPO" \
      -var="db_password=$DB_PASSWORD" \
      -target=google_storage_bucket.terraform_state \
      -target=google_storage_bucket_iam_member.terraform_state_admin
fi

echo ""
echo -e "${GREEN}✓ State bucket infrastructure created${NC}"

echo ""
echo -e "${YELLOW}Step 6: Migrating to remote backend...${NC}"
echo "Uncommenting backend configuration in providers.tf..."

# Uncomment the backend configuration
sed -i.backup 's/# terraform {/terraform {/' providers.tf
sed -i.backup 's/#   backend "gcs" {/  backend "gcs" {/' providers.tf
sed -i.backup 's/#     bucket = /    bucket = /' providers.tf
sed -i.backup 's/#     prefix = /    prefix = /' providers.tf
sed -i.backup 's/#   }/  }/' providers.tf
sed -i.backup 's/# }/}/' providers.tf

echo "Setting bucket name in backend configuration..."
# Replace bucket and prefix with the provided values (handles existing assignments)
sed -i.backup 's/bucket = "[^"]*"/bucket = "'"$BUCKET_NAME"'"/' providers.tf 

echo -e "${GREEN}✓ Backend configuration uncommented and bucket set to ${BUCKET_NAME}${NC}"

echo ""
echo -e "${YELLOW}Step 7: Reinitializing with remote backend...${NC}"
terraform init -migrate-state

echo ""
echo -e "${YELLOW}Step 8: Applying remaining infrastructure via Terraform...${NC}"
terraform apply -auto-approve \
    -var="project_id=$PROJECT_ID" \
    -var="region=$REGION" \
    -var="github_repo=$GITHUB_REPO" \
    -var="db_password=$DB_PASSWORD" \

echo -e "${GREEN}✓ Terraform apply complete${NC}"

if [ "$GH_CLI_AVAILABLE" = true ]; then
    echo ""
    echo -e "${YELLOW}Step 9: Exporting Terraform outputs and setting GitHub secrets...${NC}"

    WORKLOAD_IDENTITY_PROVIDER=$(terraform output -raw workload_identity_provider 2>/dev/null || true)
    SERVICE_ACCOUNT_EMAIL=$(terraform output -raw service_account_email 2>/dev/null || true)

    if [ -z "$WORKLOAD_IDENTITY_PROVIDER" ] || [ -z "$SERVICE_ACCOUNT_EMAIL" ]; then
        echo -e "${RED}Warning: Terraform did not return workload_identity_provider or service_account_email outputs.${NC}"
        echo "  You may need to run 'terraform output' manually to inspect outputs."
    else
        echo "Setting GitHub secret GCP_WORKLOAD_IDENTITY_PROVIDER for repo ${GITHUB_REPO}"
        printf '%s' "$WORKLOAD_IDENTITY_PROVIDER" | gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER --repo "$GITHUB_REPO"

        echo "Setting GitHub secret GCP_SERVICE_ACCOUNT for repo ${GITHUB_REPO}"
        printf '%s' "$SERVICE_ACCOUNT_EMAIL" | gh secret set GCP_SERVICE_ACCOUNT --repo "$GITHUB_REPO"

        echo -e "${GREEN}✓ GitHub secrets set (GCP_WORKLOAD_IDENTITY_PROVIDER, GCP_SERVICE_ACCOUNT)${NC}"
    fi
else
    echo -e "${YELLOW}Skipping GitHub secret creation because gh CLI is not available.${NC}"
    echo "You can set these manually with:
    gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER --body \"$(terraform output -raw workload_identity_provider)\" --repo ${GITHUB_REPO}
    gh secret set GCP_SERVICE_ACCOUNT --body \"$(terraform output -raw service_account_email)\" --repo ${GITHUB_REPO}"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Bootstrap Complete! 🎉               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Your Terraform state is now stored remotely in GCS${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Commit the updated providers.tf (with backend uncommented)"
echo "  2. Delete local state files: rm -f terraform.tfstate*"
echo "  3. Run 'terraform plan' to verify everything works"
echo ""
echo -e "${YELLOW}Note: Your backup files (*.backup) can be deleted after verification${NC}"
