# GCP Setup Guide for SyncNSweat Backend

This guide provides a step-by-step walkthrough to set up all necessary Google Cloud Platform (GCP) services, permissions, and secrets required for the `backend-deployment.yml` GitHub Actions workflow.

## Prerequisites

1.  **Google Cloud Project**: You need a GCP project. If you don't have one, create it [here](https://console.cloud.google.com/projectcreate).
2.  **Billing Enabled**: Ensure billing is enabled for your project.
3.  **Google Cloud CLI (gcloud)**: Installed and authenticated on your local machine.
    *   [Install Guide](https://cloud.google.com/sdk/docs/install)
    *   Login: `gcloud auth login`
    *   Set Project: `gcloud config set project YOUR_PROJECT_ID`

---

## Step 1: Environment Setup

Open your terminal and set the following variables. This will make the subsequent commands easier to run. **Replace the values with your specific details.**

```bash
# Configuration Variables
export PROJECT_ID="your-project-id"          # Your GCP Project ID
export REGION="us-central1"                  # Choose your region (e.g., us-central1, asia-southeast1)
export SERVICE_NAME="syncnsweat-backend"     # Name for your Cloud Run service
export REPO_NAME="syncnsweat-repo"           # Name for Artifact Registry repository
export SERVICE_ACCOUNT_NAME="github-actions-sa" # Name for the Service Account

# GitHub Repo Details (for Workload Identity)
export GITHUB_REPO="your-username/SyncNSweat-BE" # Format: username/repo

# Set the project in gcloud
gcloud config set project $PROJECT_ID
```

---

## Step 2: Enable Required APIs

Enable the necessary Google Cloud APIs for Cloud Run, Artifact Registry, Cloud SQL, and Secret Manager.

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  iamcredentials.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  compute.googleapis.com
```

---

## Step 3: Create Resources

### 3.1 Artifact Registry
Create a Docker repository to store your container images.

```bash
gcloud artifacts repositories create $REPO_NAME \
  --repository-format=docker \
  --location=$REGION \
  --description="Docker repository for SyncNSweat Backend"
```

### 3.2 Cloud SQL (PostgreSQL)
*If you haven't created a Cloud SQL instance yet:*

```bash
# Create the instance (this may take a few minutes)
gcloud sql instances create syncnsweat-db \
  --database-version=POSTGRES_15 \
  --cpu=1 \
  --memory=3840MiB \
  --region=$REGION

# Create a database
gcloud sql databases create syncnsweat_db --instance=syncnsweat-db

# Create a user
gcloud sql users create syncnsweat_user \
  --instance=syncnsweat-db \
  --password="YOUR_DB_PASSWORD"
```

*Note the Instance Connection Name (e.g., `project-id:region:instance-id`) for later.*

### 3.3 Secret Manager
Create the secrets required by the application. The workflow pulls these secrets and injects them as environment variables.

Run the following commands for **EACH** secret. You will be prompted to enter the secret value.

```bash
# Application Secrets
printf "YOUR_DATABASE_URI" | gcloud secrets create DATABASE_URI --data-file=-
printf "YOUR_SECRET_KEY" | gcloud secrets create SECRET_KEY --data-file=-
printf "YOUR_SPOTIFY_CLIENT_ID" | gcloud secrets create SPOTIFY_CLIENT_ID --data-file=-
printf "YOUR_SPOTIFY_CLIENT_SECRET" | gcloud secrets create SPOTIFY_CLIENT_SECRET --data-file=-
printf "YOUR_SPOTIFY_REDIRECT_URL" | gcloud secrets create SPOTIFY_REDIRECT_URL --data-file=-
printf "YOUR_EXERCISE_API_KEY" | gcloud secrets create EXERCISE_API_KEY --data-file=-
printf "YOUR_EXERCISE_API_HOST" | gcloud secrets create EXERCISE_API_HOST --data-file=-
printf "YOUR_API_URL" | gcloud secrets create API_URL --data-file=-
printf "YOUR_GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=-
printf "YOUR_DEFAULT_SPOTIFY_USER_PASSWORD" | gcloud secrets create DEFAULT_SPOTIFY_USER_PASSWORD --data-file=-
```

---

## Step 4: Create Service Account

Create a Service Account that GitHub Actions will use to deploy.

```bash
# Create Service Account
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
  --display-name="GitHub Actions Service Account"
```

---

## Step 5: Assign Roles

Grant the necessary permissions to the Service Account.

```bash
# 1. Artifact Registry Writer (to push images)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# 2. Cloud Run Developer (to deploy)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.developer"

# 3. Cloud SQL Client (to connect to DB)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

# 4. Secret Manager Secret Accessor (to access secrets)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 5. Service Account User (to act as the service account)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

---

## Step 6: Workload Identity Federation

This allows GitHub Actions to authenticate without storing long-lived JSON keys.

```bash
# 1. Create a Workload Identity Pool
gcloud iam workload-identity-pools create "github-pool" \
  --project="$PROJECT_ID" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# 2. Get the Pool ID (needed for the next step)
# It usually looks like: projects/123456789/locations/global/workloadIdentityPools/github-pool
export WORKLOAD_IDENTITY_POOL_ID=$(gcloud iam workload-identity-pools describe "github-pool" \
  --project="$PROJECT_ID" \
  --location="global" \
  --format="value(name)")

# 3. Create a Provider
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="$PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Repo Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository == 'YOUR_GITHUB_USER/YOUR_REPO_NAME'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# 4. Allow the GitHub repo to impersonate the Service Account
gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/${GITHUB_REPO}"
```

---

## Step 7: GitHub Repository Secrets

Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**.

Add the following secrets:

| Secret Name | Value Description | Example Value |
| :--- | :--- | :--- |
| `GCP_PROJECT_ID` | Your Google Cloud Project ID | `my-project-123` |
| `GCP_REGION` | The region you chose | `us-central1` |
| `GCP_SERVICE_NAME` | The Cloud Run service name | `syncnsweat-backend` |
| `GCP_SERVICE_REGISTRY` | Artifact Registry repo name | `syncnsweat-repo` |
| `GCP_CLOUD_SQL_INSTANCE_ID` | Cloud SQL Instance ID | `instance-id` |
| `GCP_SERVICE_ACCOUNT` | The full email of the Service Account | `github-actions-sa@project-id.iam.gserviceaccount.com` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | The full Provider resource name | `projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |

### How to get the Workload Identity Provider string:
```bash
gcloud iam workload-identity-pools providers describe "github-provider" \
  --project="$PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --format="value(name)"
```

---

## Summary

Once you have completed these steps:
1.  **Infrastructure** is ready (Artifact Registry, Cloud SQL, Secrets).
2.  **Security** is configured (Service Account, Roles, Workload Identity).
3.  **GitHub** is connected (Secrets added).

You can now push to the `main` branch, and the `backend-deployment.yml` workflow should succeed!
