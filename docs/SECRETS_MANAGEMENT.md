# Secrets Management Guide

## Security Architecture

This project uses a **secure two-layer approach** for secrets management:

```
GitHub Secrets → gcloud CLI → GCP Secret Manager → Cloud Run
     (CI/CD)     (deployment)      (runtime)        (app)
```

## ✅ Why This Approach is Secure

### 1. **Secrets Never Touch Terraform State**
- Terraform only creates **empty secret containers** in Secret Manager
- Secret **values** are injected via `gcloud` CLI during CI/CD
- Terraform state files remain clean and safe

### 2. **GCP Secret Manager Benefits**
- ✅ Encryption at rest and in transit
- ✅ Automatic key rotation support
- ✅ Fine-grained IAM access control
- ✅ Complete audit logging (who accessed what and when)
- ✅ Secret versioning with rollback capability

### 3. **Defense in Depth**
- GitHub Secrets: Encrypted at rest, only accessible during workflow runs
- GCP Secret Manager: Additional encryption layer with IAM controls
- Cloud Run: Service account with least-privilege access
- No secrets in code, containers, or logs

## 🔄 How It Works

### CI/CD Flow (.github/workflows/backend-deployment.yml)

1. **GitHub Actions authenticates to GCP** via Workload Identity Federation (no keys!)
2. **Update secrets in GCP Secret Manager** using `gcloud secrets create/update`
3. **Terraform manages infrastructure** (Cloud Run, Cloud SQL, IAM, etc.)
4. **Cloud Run deployment** references secrets by name from Secret Manager

### Runtime Flow

Cloud Run containers:
- Don't contain secrets in environment variables directly
- Reference secrets via Secret Manager paths
- Service account automatically injects secret values at runtime

## 🔐 Required GitHub Secrets

Add these in **Settings → Secrets and variables → Actions**:

### Infrastructure Secrets
- `GCP_PROJECT_ID` - Your GCP project ID
- `GCP_REGION` - Deployment region (e.g., `us-central1`)
- `GCP_SERVICE_NAME` - Cloud Run service name
- `GCP_SERVICE_REGISTRY` - Artifact Registry name
- `GCP_CLOUD_SQL_INSTANCE_ID` - Cloud SQL instance ID
- `GCP_CLOUD_SQL_DB_PASSWORD` - Database password
- `GCP_SERVICE_ACCOUNT` - Service account email
- `GCP_WORKLOAD_IDENTITY_PROVIDER` - Workload Identity Provider resource name

### Application Secrets
- `DATABASE_URI` - Full database connection string
- `SECRET_KEY` - JWT signing key
- `SPOTIFY_CLIENT_ID` - Spotify API client ID
- `SPOTIFY_CLIENT_SECRET` - Spotify API client secret
- `SPOTIFY_REDIRECT_URL` - OAuth redirect URL
- `EXERCISE_API_KEY` - Exercise API key
- `EXERCISE_API_HOST` - Exercise API host
- `API_URL` - Backend API URL
- `GEMINI_API_KEY` - Google Gemini API key
- `DEFAULT_SPOTIFY_USER_PASSWORD` - Default user password

## 🛠️ Local Development

For local development, you have two options:

### Option 1: Use GCP Secret Manager (Recommended)
```bash
# Authenticate to GCP
gcloud auth application-default login

# Your app will automatically fetch secrets from Secret Manager
python -m uvicorn app.main:app --reload
```

### Option 2: Use .env file
```bash
# Create .env file (DO NOT COMMIT!)
cp .env.example .env
# Edit .env with your local values

# Run the app
python -m uvicorn app.main:app --reload
```

## 🔄 Updating Secrets

### In Production (via CI/CD)
1. Update the secret value in GitHub Repository Secrets
2. Push to main branch or re-run the workflow
3. The CI/CD pipeline will automatically update GCP Secret Manager
4. Cloud Run will pick up the new value on next deployment

### Manually (via gcloud CLI)
```bash
# Update a secret
echo -n "new-secret-value" | gcloud secrets versions add SECRET_NAME \
  --project="your-project-id" \
  --data-file=-

# List secret versions
gcloud secrets versions list SECRET_NAME --project="your-project-id"

# Access a secret (requires proper IAM permissions)
gcloud secrets versions access latest --secret="SECRET_NAME"
```

## 🔍 Audit & Monitoring

### View Secret Access Logs
```bash
gcloud logging read "resource.type=secret_version AND protoPayload.methodName=AccessSecretVersion" \
  --project="your-project-id" \
  --limit=50
```

### View Secret Modifications
```bash
gcloud logging read "resource.type=secret_version AND (protoPayload.methodName=AddSecretVersion OR protoPayload.methodName=CreateSecret)" \
  --project="your-project-id" \
  --limit=50
```

## 🚨 Security Best Practices

### DO ✅
- ✅ Keep GitHub Secrets up-to-date
- ✅ Use least-privilege IAM roles
- ✅ Rotate secrets regularly (especially API keys)
- ✅ Monitor secret access logs
- ✅ Use different secrets for dev/staging/prod
- ✅ Enable secret versioning for rollback

### DON'T ❌
- ❌ Never commit secrets to git (even in .env files)
- ❌ Never log secret values
- ❌ Never pass secrets in URLs or query parameters
- ❌ Never store secrets in Terraform state
- ❌ Never share secrets via Slack/email
- ❌ Never hardcode secrets in application code

## 📚 Additional Resources

- [GCP Secret Manager Best Practices](https://cloud.google.com/secret-manager/docs/best-practices)
- [GitHub Actions Security Hardening](https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions)
- [Cloud Run Secret Management](https://cloud.google.com/run/docs/configuring/secrets)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
