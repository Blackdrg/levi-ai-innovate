# Deployment Guide — LEVI-AI v5.0+ "The Sovereign Brain"

Production-grade deployment to **Google Cloud Platform (GCP)** using managed serverless services.

---

## 🏗️ GCP-Native Architecture

LEVI v5.0+ has been architecturaly hardened for GCP to support 10,000+ users with zero-maintenance and high-cost efficiency.

- **API Layer**: [Cloud Run Service](https://cloud.google.com/run) (`levi-api`)
- **Worker Layer**: [Cloud Run Jobs](https://cloud.google.com/run/docs/create-jobs) (`levi-video-job`)
- **Queueing/Async**: [Cloud Tasks](https://cloud.google.com/tasks)
- **Database**: [Firestore](https://cloud.google.com/firestore) (Native Mode)
- **Cache/RL**: [Memorystore for Redis](https://cloud.google.com/memorystore)
- **Storage**: [Google Cloud Storage](https://cloud.google.com/storage) (`gs://levi-media-*`)
- **Secrets**: [Secret Manager](https://cloud.google.com/secret-manager)

---

## 🚀 Initial Setup (Provisioning)

Before deploying code, provision the project resources using the provided setup scripts:

```powershell
# Windows (PowerShell)
.\scripts\setup_gcp.ps1

# Linux/macOS (Bash)
chmod +x ./scripts/setup_gcp.sh
./scripts/setup_gcp.sh
```

> [!IMPORTANT]
> After running the setup scripts, navigate to the [GCP Secret Manager Console](https://console.cloud.google.com/security/secret-manager) and populate the values for `GROQ_API_KEY`, `TOGETHER_API_KEY`, and `SECRET_KEY`.

---

## 🔧 Environment Configuration

| Variable | Description | Recommendation |
|----------|-------------|----------------|
| `ENVIRONMENT` | Deployment stage | `production` |
| `GCP_STORAGE_BUCKET` | Media storage | `levi-media-[PROJECT_ID]` |
| `USE_GCP_JOBS` | Enable Cloud Run Jobs | `true` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

---

## ⚡ Cloud Run Sizing (Recommended)

### `levi-api` (Cloud Run Service)
- **Memory**: 4Gi (Required for Sentence-Transformers `all-MiniLM-L6-v2`)
- **CPU**: 2 vCPU
- **Min Instances**: 1 (Essential for Zero Cold Start)
- **Concurrency**: 80

### `levi-video-job` (Cloud Run Job)
- **Memory**: 8Gi to 32Gi (High-intensity rendering)
- **CPU**: 4 vCPU
- **Timeout**: 3600s (1 hour)

---

## 📊 CI/CD Pipeline

The repository includes GitHub Actions workflows for seamless deployment:

1. **`deploy-backend.yml`**:
   - Builds `Dockerfile` for the API.
   - Deploys to Cloud Run Service with a `production` tag.
   - Triggers `gcloud run services update-traffic` for zero-downtime rolls.

2. **`deploy-jobs.yml`**:
   - Builds `Dockerfile.job`.
   - Updates `levi-video-job` definition in Cloud Run.

---

## 🧪 Post-Deployment Verification

After deployment, verify each component:

```bash
BASE=https://levi-api.a.run.app

# 1. Health check (Verify Firestore + Redis)
curl $BASE/health

# 2. Evolution Monitoring (Verify Learning Layer)
curl $BASE/health/evolution -H "X-Admin-Key: $ADMIN_KEY"

# 3. SSE Streaming Test
# Use a tool like 'curl -N' to verify token-by-token delivery
curl -N -X GET $BASE/stream
```

---

## 🔄 Scaling & Costs

- **Scale-to-Zero**: Video workers (Jobs) cost $0/month when not in use.
- **Memorystore**: Standard Tier is recommended for HA.
- **Firestore**: Use the **Redis-First** read pattern implemented in `MemoryManager` to minimize Firestore read costs.

---

## 🔄 Rollback

```bash
# List recent Cloud Run revisions
gcloud run revisions list --service levi-api --region us-central1

# Pin to a specific revision
gcloud run services update-traffic levi-api \
  --to-revisions REVISION_NAME=100 \
  --region us-central1
```
