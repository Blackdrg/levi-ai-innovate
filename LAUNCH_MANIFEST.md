# 🚀 Launch Manifest: LEVI-AI v6.8.5 "Sovereign Monolith"

This document serves as the final authoritative source for the production environment and operational state of the LEVI-AI v6.8.5 Sovereign Monolith.

## 📦 1. Infrastructure (Google Cloud Run)
- **Service Name**: `levi-monolith`
- **Region**: `us-central1`
- **Memory**: `8Gi` (Mandatory for local Llama-3-8B GGUF + FAISS load)
- **CPU**: `4 vCPU` (Recommended for stable reasoning throughput)
- **Concurrency**: `80` (Optimized for asynchronous SSE streaming)
- **Volume Mounts**: 
  - `GCS FUSE` Bucket: `levi-ai-vector-store` mounted at `/mnt/vector_db`

## 🔑 2. Mandatory Secrets (GCP Secret Manager)
| Secret Name | Description |
| :--- | :--- |
| `SECRET_KEY` | JWT/Session encryption seed |
| `ADMIN_KEY` | Access to `/health/sovereign` deep diagnostics |
| `INTERNAL_SERVICE_KEY` | HMAC key for protected maintenance triggers |
| `FIREBASE_PROJECT_ID` | Identity & Auth synchronization |
| `REDIS_URL` | Session history, rate limiting, and pulse coordination |
| `GROQ_API_KEY` | High-complexity API fallback |
| `TOGETHER_API_KEY` | Collective Wisdom pattern distillation |

## 🧠 3. Sovereign Mind State
- **Primary Engine**: `Llama-3-8B-Instruct.gguf` (100% In-Process)
- **Memory Matrix**: User-Scoped FAISS (Persistent via FUSE)
- **Evolution Mode**: Autonomous (Mutation threshold: 5 star performance)
- **Privacy Mode**: Absolute (FAISS/Redis/Firestore atomic wipe enabled)

## 🧪 4. Post-Launch Sovereignty Audit
1. **Sovereign Engine Probe**:
   - URL: `GET /health/sovereign`
   - Headers: `X-Admin-Key: <ADMIN_KEY>`
   - *Expect*: Comprehensive report on LLM readiness and FUSE mount integrity.
2. **Persistence Circuit**:
   - Test: Insert fact, restart service, verify fact recall.
   - *Expect*: 100% semantic recall via GCS FUSE persistence.
3. **Privacy Absolute**:
   - Test: Trigger `clear-all`, verify `/mnt/vector_db/<user_id>` is empty.

---
*Generated: 2026-04-01 — LEVI-AI v6.8.5 Sovereign Monolith Ready.*
