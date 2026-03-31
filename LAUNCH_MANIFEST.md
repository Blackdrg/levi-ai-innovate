# LAUNCH MANIFEST — LEVI-AI v6.8 "Sovereign"

## 📑 Project Overview
- **Codename**: Sovereign
- **Version**: v6.8.4-Hardened
- **Architecture**: Hybrid-Sovereign Distributed Agentic Synthesis
- **License**: Sovereign / Proprietary
- **Launch Date**: 2026-04-01

---

## 🛠️ Core Engine Specifications

| Module | Engine | Role |
| :--- | :--- | :--- |
| **Brain** | LeviBrain v6.8 | Multi-tier routing & tool-calling |
| **Logic (Sovereign)** | Llama-3-8B (GGUF/llama.cpp) | 100% Local-first zero-cost reasoning |
| **Logic (Cloud)** | Llama-3.1-70B/405B (Together) | High-complexity Level 3/4 orchestration |
| **Visuals** | FLUX.1 [schnell] / SD-V6 | High-fidelity cinematic synthesis |
| **Motion** | Stable Video Diffusion / MoviePy | Multi-scene Reel generation |
| **Memory** | FAISS + Redis + Firestore | 3-layer semantic context matrix |

---

## 🏗️ Deployment Infrastructure

### 🚢 Backend (FastAPI / Celery)
- **Runtime**: Python 3.10+ (Dockerized)
- **Queues**: 
    - `default`: Chat, Image, Memory management.
    - `heavy`: Pattern distillation, Global maintenance.
- **Circuit Breakers**: Multi-tier thresholds (Local/Cloud).

### 🎨 Frontend (Vite / Vercel)
- **Rendering**: Static with Dynamic Hydration.
- **SSE**: Unified Activity Stream (Intelligence Pulses).
- **Assets**: Optimized with sub-resource integrity (SRI).

---

## 🔑 Critical Production Variables

- `ENVIRONMENT`: Must be set to `production`.
- `USE_SOVEREIGN_ROUTING`: Set to `true` for local-first execution.
- `LOCAL_MODEL_PATH`: Point to valid `.gguf` file.
- `REDIS_URL`: Primary state & concurrency lock.
- `FIREBASE_SERVICE_ACCOUNT_JSON`: Database and Auth gateway.
- `AWS_S3_BUCKET` / `GCP_STORAGE_BUCKET`: Media persistence.

---

## 🛡️ Resilience Matrix
- **PEOC Loop**: Observe -> Critique -> Improve loop for agentic self-correction.
- **Hybrid Evolution**: RAG-driven in-context learning (ICL) via local FAISS.
- **Soul Optimizer**: 20-interaction distillation cycle for personality growth.

---

**LEVI v6.8 — The Sovereign Evolution.**
*Sovereign Intelligence. Absolute Privacy.*
