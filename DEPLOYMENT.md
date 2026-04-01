# Deployment Guide — LEVI-AI v6.8.5 "The Sovereign Monolith"

Production-grade deployment for the **Sovereign AI Ecosystem** using a unified, hardened Monolith architecture on Google Cloud Platform.

---

## 🏗️ Sovereign Monolith Architecture

LEVI v6.8.5 is architecturally hardened for maximum efficiency, privacy, and sovereignty. It uses a **Monolith design** for simplified scaling and reduced latency, with on-demand user-specific memory loading.

- **Frontend**: [React (Vite)](https://vitejs.dev/) hosted on **Vercel**
- **Backend (Monolith)**: [FastAPI](https://fastapi.tiangolo.com/) hosted on [Cloud Run](https://cloud.google.com/run) (`levi-monolith`)
- **API Gateway**: Integrated via Cloud Run (Auto-SSL + Global LB)
- **Reasoning**: **Local Llama-3-8B (GGUF)** (Primary) / Groq & Together AI (High-fidelity fallbacks)
- **Memory (Matrix)**: **User-Specific FAISS Indices** (Stored in GCS, loaded on-demand via FUSE)
- **Database**: [Firestore](https://cloud.google.com/firestore) + [MongoDB Atlas](https://www.mongodb.com/atlas) (Persistence)
- **Cache/SSE/RL**: [Cloud Memorystore for Redis](https://cloud.google.com/memorystore)
- **Storage**: [Google Cloud Storage](https://cloud.google.com/storage) (Mounted via GCS FUSE at `/mnt/vector_db`)

---

## 🚀 Deployment (CI/CD)

The repository uses a **Unified GitHub Action** for production-grade hardened deployments:

### 1. **`deploy_production.yml`**
- **Backend Pipeline**:
    - Build: `Dockerfile` with optimized Python 3.11-slim.
    - Push: Artifact Registry (`us-central1-docker.pkg.dev`).
    - Deploy: Cloud Run with **GCS Volume Mounting** for persistent user vector stores.
- **Frontend Pipeline**:
    - Automatic deployment via **Vercel** on push to `main`.
    - Workflow performs a sanity check build and **Sovereign System Audit** before promotion.

---

## ⚡ Cloud Run Sizing (Sovereign Optimized)

### `levi-monolith` (Production Service)
- **Memory**: **8Gi** (Required for Llama-3-8B GGUF (~5GB) + FAISS memory matrix + Concurrency)
- **CPU**: 4 vCPU (Recommended for stable token-per-second throughput)
- **Scaling**: 1-10 instances (Min-instances recommended for zero-cold-start sovereignty)
- **Concurrency**: 80 (High throughput with non-blocking SSE)
- **Volume**: GCS Bucket `levi-ai-vector-store` mounted at `/mnt/vector_db`

---

## 📊 Security & Observability

- **Rate Limiting**: Global Redis-backed rate limiting (20 req/min for free users).
- **Concurrency Gate**: Enforced `MAX_LOCAL_CONCURRENCY=2` with automatic saturation fallback.
- **Identity**: Firebase Auth with JTI blacklisting in Redis.
- **Internal Auth**: Service-to-service calls protected via `INTERNAL_SERVICE_KEY` HMAC.
- **Deep Health**: Sovereign Engine Probe at `/health/sovereign` with `X-Admin-Key`.

---

## 🧪 Post-Deployment Verification

- ✅ **Sovereign Engine**: `GET /api/status/sovereign` returns `status: "Green"`.
- ✅ **Memory Matrix**: `/mnt/vector_db` contains binary FAISS indices for active users.
- ✅ **Intelligence Pulse**: `POST /api/chat` returns `text/event-stream` with activity metadata.
- ✅ **Local Reasoning**: `scripts/verify_production.py --prod` returns 100% pass on all circuits.

---

**LEVI v6.8.5 — Sovereign. Secure. Self-Learning.**
