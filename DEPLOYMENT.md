# Deployment Guide — LEVI-AI v2.0 "The Brain"

Production deployment to **Google Cloud Run** (backend) + **Firebase Hosting** (frontend).

---

## ⚙️ GitHub Secrets — Required

Add all of these in **GitHub → Settings → Secrets and variables → Actions**:

### 🌐 Cloud & Infrastructure
| Secret | Description |
|--------|-------------|
| `GCP_SA_KEY` | GCP Service Account JSON (Cloud Run Admin + Storage Admin) |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | Firebase service account JSON string |
| `FIREBASE_PROJECT_ID` | e.g. `levi-ai-c23c6` |
| `REDIS_URL` | Upstash Redis URL — **required** for Celery + rate limiting |

### 🧠 AI & Intelligence
| Secret | Description |
|--------|-------------|
| `GROQ_API_KEY` | Groq Cloud API key (intent detection + synthesis) |
| `TOGETHER_API_KEY` | Together AI key (image generation via FLUX.1) |

### 💳 Payments
| Secret | Description |
|--------|-------------|
| `RAZORPAY_KEY_ID` | Razorpay API key ID |
| `RAZORPAY_KEY_SECRET` | Razorpay API key secret |
| `RAZORPAY_WEBHOOK_SECRET` | Webhook signature verification |

### 🔒 Security
| Secret | Description |
|--------|-------------|
| `SECRET_KEY` | Long random string for JWT signing |
| `ADMIN_KEY` | X-Admin-Key header for maintenance endpoints |

### 📦 Optional
| Secret | Description |
|--------|-------------|
| `AWS_S3_BUCKET` | S3 bucket for image/video storage |
| `AWS_ACCESS_KEY_ID` | AWS IAM key |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret |
| `SENTRY_DSN` | Error monitoring (recommended for orchestrator retries) |

---

## LEVI-AI: v5.0 Deployment Guide 🚀

This guide outlines the production deployment process for the hardened LEVI-AI platform.

## 🏗️ Core Infrastructure
LEVI follows a containerized architecture managed via **Docker Compose** or **Kubernetes/Cloud Run**.

- **API Gateway**: FastAPI (Python 3.11+)
- **Broker/Cache**: Redis
- **Ingress**: Nginx (Custom SSE-optimized config)
- **Database**: Firestore (GCP)
- **Jobs**: Celery (Worker + Beat)

---

## 🛠️ Production Setup (Docker Compose)

The fastest way to deploy the full hardened stack is via the updated `docker-compose.yml`.

```bash
# 1. Fill in production .env
cp .env.example .env
# Set ENVIRONMENT=production
# Set ALERT_WEBHOOK_URL for circuit breaker alerts

# 2. Build and start services
docker compose up --build -d

# 3. Verify nginx upstream
curl http://localhost/api/health
```

---

## ⚡ Critical Configuration for SSE

For real-time token streaming to work, the reverse proxy (Nginx/Cloudflare) **must not buffer the response**.

The v5.0 `nginx.conf` included in the repo handles this via:
- `proxy_buffering off;`
- `chunked_transfer_encoding on;`
- MIME type: `text/event-stream`

---

## 📖 Operational Procedures
For detailed maintenance, logs management, and troubleshooting, refer to the **[RUNBOOK.md](RUNBOOK.md)**.

## 🧪 Post-Deployment Checklist
- [ ] `/health` returns all OK.
- [ ] Test chat streaming (tokens should arrive piece-by-piece).
- [ ] Verify Celery `beat` logs for successful memory flushes.
- [ ] Confirm `ENVIRONMENT=production` is set in all workers.
- Rewrites `/api/**` → Cloud Run backend URL
- SSE endpoint `/stream` proxied with streaming headers

---

## 🧪 Production Smoke Tests

After deployment, verify each endpoint:

```bash
BASE=https://levi-api.a.run.app

# Health check
curl $BASE/health

# Brain status
curl $BASE/system/orchestrator/status

# Chat (local route — tests zero-API path)
curl -X POST $BASE/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "hello", "session_id": "smoke_test"}'
# Expected: route="local", instant response, no API cost

# Full load test
python scripts/load_test.py --users 50 --target $BASE
```

---

## 🖥️ Cloud Run Configuration (Recommended)

```yaml
# service.yaml
memory: 4Gi
cpu: 2
min-instances: 1         # Keep warm for < 5ms local responses
max-instances: 10
concurrency: 80
timeout: 60s
```

> [!WARNING]
> Do **not** set memory below 2GB. The Sentence-Transformers embedding model (`all-MiniLM-L6-v2`) requires ~400MB at load time. Memory-constrained containers will `OOMKilled` during semantic extraction.

---

## 📊 CI/CD Pipeline

```
git push master
    │
    ├─ deploy-backend.yml
    │     1. Build Docker image
    │     2. Push to Artifact Registry
    │     3. Deploy to Cloud Run
    │     4. Run smoke test /health
    │
    └─ deploy-frontend.yml
          1. firebase deploy --only hosting
```

---

## 🔄 Rollback

```bash
# List recent Cloud Run revisions
gcloud run revisions list --service levi-backend --region us-central1

# Pin to a specific revision
gcloud run services update-traffic levi-backend \
  --to-revisions REVISION_NAME=100 \
  --region us-central1
```
