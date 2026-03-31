# Security Policy: LEVI-AI v6.8 "Sovereign"

## 🛡️ Sovereign Defense Strategy

LEVI-AI v6.8 is built with a **"Your Data, Your Infrastructure"** philosophy. Our Sovereign architecture ensures that the most sensitive parts of the AI reasoning process occur within your secure perimeter.

### 1. Local-First Processing (Sovereignty)
- **Zero-Cloud Reasoning**: By default, LEVI utilizes local GGUF models via `Llama-CPP`. Sensitive user queries never leave your infrastructure.
- **Private Vector Space**: Semantic memory is stored in local FAISS indices. Unlike cloud vector DBs, your long-term knowledge matrix is never shared with 3rd party providers for training or analysis.

### 2. Request Sanitization & Logic Hardening
- **Multi-Stage Sanitization**: Every incoming request is scanned for prompt injection, SSRF, and path traversal via the `Standardizer` stage.
- **Logic Isolation**: Code execution is sandboxed using the **Piston API** with a restricted local fallback, preventing unauthorized system access.

### 3. Identity & Session Security
- **Firebase Auth**: Industry-standard JWT validation with mandatory **JTI Blacklisting** in Redis to prevent session hijacking.
- **Distributed Credit Locking**: Atomic Lua-based Redis locks prevent race conditions in financial/credit transactions (Transactional Integrity).
- **Secret Management**: All production secrets (API keys, DB credentials) are managed via encrypted environment variables or GCP Secret Manager.

## 🐛 Reporting a Vulnerability

If you discover a security vulnerability within LEVI-AI, please do **not** open a public issue.

1. **Email us**: Send a detailed report to `security@levi-ai.com`.
2. **Include Details**: Describe the vulnerability, the potential impact, and steps to reproduce.
3. **Response Time**: We aim to acknowledge all reports within 24 hours.

## 🚫 Out of Scope
- DDoS attacks (handled via Cloud Run / Nginx ingress).
- 3rd party fallbacks (Together AI, Firebase).

---
*Last Updated: 2026-04-01 — Sovereign Hardened.*
