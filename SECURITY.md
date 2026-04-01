# Security Policy: LEVI-AI v6.8.5 "Sovereign Monolith"

## 🛡️ Sovereign Defense Strategy

LEVI-AI v6.8.5 is built with a **"Your Data, Your Infrastructure"** philosophy. Our Sovereign architecture ensures that the most sensitive parts of the AI reasoning process occur within your secure perimeter, isolated from the public cloud.

### 1. Local-First Processing (Sovereignty)
- **Model Isolation**: By default, LEVI utilizes local GGUF models via `Llama-CPP`. These models run in-process on the monolith, ensuring that reasoning never leaks to 3rd party APIs for sensitive tasks.
- **Private Vector Space**: Semantic memory is stored in local FAISS indices on a **GCS FUSE** mount (`/mnt/vector_db`). Access is strictly limited to the application process, and data is encrypted at rest via GCP infrastructure.
- **Zero-Cloud Vectors**: Unlike legacy cloud vector DBs, your long-term knowledge matrix is never shared with 3rd party providers for training or analysis.

### 2. Request Sanitization & Logic Hardening
- **Multi-Stage Sanitizer**: Every incoming request is scanned for prompt injection and path traversal. The `Standardizer` stage enforces strict character limits to prevent buffer saturation.
- **Resource Gating (DoS Prevention)**: The monolith operates with a strict **8Gi RAM limit** and a **MAX_LOCAL_CONCURRENCY=2** semaphore. This prevents resource exhaustion attacks from stalling the primary reasoning engine.
- **Sovereign Engine Probe**: Production health is monitored via the `/health/sovereign` deep-diagnostic endpoint, which verifies Vector DB integrity and Local LLM reachability using a hardened `X-Admin-Key`.

### 3. Identity & Session Security
- **Firebase Auth**: Industry-standard JWT validation.
- **Internal HMAC Authentication**: Internal triggers (distillation, memory GC) are protected via hardened `INTERNAL_SERVICE_KEY` HMAC verification, ensuring service-to-service calls originate from within the monolith.
- **Secret Management**: All production secrets (ADMIN_KEY, RAZORPAY_KEY, etc.) are managed via GCP Secret Manager or encrypted environment variables.

## 🐛 Reporting a Vulnerability

If you discover a security vulnerability within LEVI-AI, please do **not** open a public issue.

1. **Email us**: Send a detailed report to `security@levi-ai.com`.
2. **Include Details**: Describe the vulnerability, potential impact, and steps to reproduce.
3. **Response Time**: We aim to acknowledge all reports within 24 hours and patch critical Sovereignty failures within 48 hours.

---
*Last Updated: 2026-04-01 — LEVI-AI v6.8.5 Sovereign Hardened.*
