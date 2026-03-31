# Deployment Guide — LEVI-AI v6.8 "The Sovereign Mind"

Production-grade deployment for the **Sovereign AI Ecosystem** using a hybrid Cloud/Local architecture.

---

## 🏗️ Sovereign Architecture

LEVI v6.8 is architecturally hardened for maximum privacy and zero-cost reasoning. It prioritizes local infrastructure while utilizing managed services for scale.

- **API Layer**: [Cloud Run Service](https://cloud.google.com/run) (`levi-api`)
- **Reasoning**: **Local Llama-CPP** (Primary) / Together AI (High-fidelity fallback)
- **Memory**: **FAISS** (Local State) / Firestore (Cold Persistence)
- **Queueing/Async**: [Cloud Tasks](https://cloud.google.com/tasks) / Celery
- **Database**: [Firestore](https://cloud.google.com/firestore) (Native Mode)
- **Cache/RL**: [Memorystore for Redis](https://cloud.google.com/memorystore)
- **Storage**: [Google Cloud Storage](https://cloud.google.com/storage) (`gs://levi-media-*`)

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
> **Sovereign Dependency Check**: Ensure the `.gguf` model files are present in the `backend/models/` directory before building the Docker image. The deployment will fail if local reasoning weights are missing.

---

## 🔧 Environment Configuration

| Variable | Description | Recommendation |
|----------|-------------|----------------|
| `ENVIRONMENT` | Deployment stage | `production` |
| `LOCAL_MODEL_PATH` | Path to GGUF model | `models/llama-3-8b.gguf` |
| `USE_SOVEREIGN_ROUTING`| Prioritize Local Engine | `true` |
| `MEMORY_DIMENSION` | FAISS vector size | `384` |

---

## ⚡ Cloud Run Sizing (Recommended v6.8)

### `levi-api` (Cloud Run Service)
- **Memory**: **8Gi** (Required for FAISS Indexing + Llama-CPP reasoning)
- **CPU**: 4 vCPU
- **Min Instances**: 1 (Essential for Zero Cold Start)
- **Concurrency**: 40 (Lowered for local inference stability)

### `levi-heavy-worker` (Cloud Run Job/Service)
- **Memory**: 16Gi to 32Gi (High-intensity pattern distillation)
- **CPU**: 4-8 vCPU
- **Timeout**: 3600s (1 hour)

---

## 📊 CI/CD Pipeline

The repository includes GitHub Actions workflows for seamless deployment:

1. **`deploy-backend.yml`**:
    - Builds `Dockerfile` with optimized `llama-cpp-python` wheels.
    - Deploys to Cloud Run Service with a `sovereign` tag.
    - Mounts necessary GCS buckets for model persistence.

2. **`deploy-jobs.yml`**:
    - Builds `Dockerfile.worker`.
    - Updates Celery workers for Pattern Distillation tasks.

---

## 🧪 Post-Deployment Verification

After deployment, verify the Sovereign state:

```bash
BASE=https://api.levi-ai.com

# 1. Sovereignty Check (Verify Local Llama + FAISS)
curl $BASE/health/sovereign

# 2. Intelligence Pulse Verification
# Check for real-time activity stream delivery
curl -N -X GET $BASE/stream

# 3. Memory Integrity
# Verify FAISS index hydration from Firestore
curl $BASE/api/v1/memory/status -H "X-Admin-Key: $ADMIN_KEY"
```

---

## 🔄 Scaling & Costs

- **Zero-Cost Reasoning**: Local Llama-CPP handles ~80% of traffic, reducing API costs by 90%.
- **FAISS Efficiency**: Vector retrieval happens within the API process, eliminating expensive remote vector DB calls.
- **Scaling**: Use Cloud Run's horizontal scaling. Note that memory usage per instance is higher in v6.8.

---

**LEVI v6.8 — Sovereign. Secure. Self-Learning.**
