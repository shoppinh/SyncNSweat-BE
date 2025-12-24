#!/bin/bash
set -euo pipefail

# ========================================
# Deploy Module Validation Script
# ========================================
# This script validates that bootstrap has been completed
# before allowing the deploy module to run.
#
# This script is called by GitHub Actions before Terraform operations.
# ========================================

PROJECT_ID="${1:-}"

echo "========================================"
echo "Deploy Module Pre-Flight Validation"
echo "========================================"
echo ""

# Validate inputs
if [ -z "$PROJECT_ID" ]; then
  echo "❌ Error: PROJECT_ID is required"
  echo "Usage: ./validate.sh <PROJECT_ID>"
  exit 1
fi

echo "📋 Validating bootstrap completion for project: $PROJECT_ID"
echo ""

# ========================================
# Check 1: Bootstrap completion marker (with diagnostics)
# ========================================
echo "🔍 Check 1: Bootstrap completion marker..."

if gcloud secrets describe BOOTSTRAP_COMPLETE --project="$PROJECT_ID" > /dev/null 2>&1; then
  echo "   ✅ Secret exists (describe succeeded)."
else
  echo ""
  echo "❌ VALIDATION FAILED: Bootstrap not complete or inaccessible"
  echo "The BOOTSTRAP_COMPLETE secret either does not exist or the current identity lacks permission to view it."
  echo ""
  exit 1
fi

echo "   ✅ Secret describe succeeded"

# ========================================
# Check 2: Terraform state bucket exists
# ========================================
echo "🔍 Check 2: Terraform state bucket..."

STATE_BUCKET="syncnsweat-terraform-state-${PROJECT_ID}"

if ! gsutil ls -b "gs://${STATE_BUCKET}" &>/dev/null; then
  echo ""
  echo "❌ VALIDATION FAILED: State bucket not found"
  echo ""
  echo "The Terraform state bucket does not exist: gs://${STATE_BUCKET}"
  echo "This indicates incomplete bootstrap setup."
  echo ""
  echo "Required action:"
  echo "  An administrator must complete the bootstrap module setup."
  echo ""
  exit 1
fi

echo "   ✅ Terraform state bucket exists: gs://${STATE_BUCKET}"
echo ""

# ========================================
# Check 3: Bootstrap state exists
# ========================================
echo "🔍 Check 3: Bootstrap Terraform state..."

if ! gsutil ls "gs://${STATE_BUCKET}/terraform/bootstrap/state/default.tfstate" &>/dev/null; then
  echo ""
  echo "⚠️  WARNING: Bootstrap state not found in expected location"
  echo "   Expected: gs://${STATE_BUCKET}/terraform/bootstrap/state/default.tfstate"
  echo ""
  echo "   This may indicate:"
  echo "   - Bootstrap state migration was not completed"
  echo "   - Bootstrap was run but not migrated to GCS"
  echo ""
  echo "   The deploy module may fail if it cannot read bootstrap outputs."
  echo ""
  # Don't fail here, let Terraform try and provide a better error
else
  echo "   ✅ Bootstrap state file found"
  echo ""
fi


# ========================================
# Check 4: Service accounts exist
# ========================================
echo "🔍 Check 5: Required service accounts..."

# Expected service account IDs (based on bootstrap configuration)
GITHUB_SA="github-actions-sa-runner@${PROJECT_ID}.iam.gserviceaccount.com"
CLOUDRUN_SA="cloudrun-sa@${PROJECT_ID}.iam.gserviceaccount.com"

MISSING_SAS=()

if ! gcloud iam service-accounts describe "$GITHUB_SA" --project="$PROJECT_ID" &>/dev/null; then
  MISSING_SAS+=("$GITHUB_SA")
fi

if ! gcloud iam service-accounts describe "$CLOUDRUN_SA" --project="$PROJECT_ID" &>/dev/null; then
  MISSING_SAS+=("$CLOUDRUN_SA")
fi

if [ ${#MISSING_SAS[@]} -gt 0 ]; then
  echo ""
  echo "❌ VALIDATION FAILED: Required service accounts not found"
  echo ""
  echo "The following service accounts are missing:"
  for sa in "${MISSING_SAS[@]}"; do
    echo "  - $sa"
  done
  echo ""
  echo "Required action:"
  echo "  These service accounts should have been created by bootstrap."
  echo "  An administrator must run or re-run the bootstrap module."
  echo ""
  exit 1
fi

echo "   ✅ Required service accounts exist"
echo ""

# ========================================
# Validation Summary
# ========================================
echo "========================================"
echo "✅ All Validations Passed"
echo "========================================"
echo ""
echo "The deploy module is ready to run."
echo "Bootstrap configuration is valid and complete."
echo ""
echo "You can now proceed with:"
echo "  terraform init"
echo "  terraform plan"
echo "  terraform apply"
echo ""

exit 0
