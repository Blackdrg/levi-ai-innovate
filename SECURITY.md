# Security Policy: LEVI-AI v5.0

## 🛡️ Production Defense Strategy

LEVI-AI is built with a "Privacy First, Defense Always" philosophy. Our v5.0 architecture implements several layers of security to protect both the infrastructure and our users.

### 1. Request Sanitization & Abuse Detection
- **Pattern Matching**: Every incoming request is scanned for common attack patterns (SQLi, XSS, Path Traversal). 
- **Automated Blocking**: Requests containing malicious patterns are instantly rejected with a `403 Banned` response.
- **Log Enrichment**: Security events are logged with full Trace-IDs for forensic analysis.

### 2. Rate Limiting & Quotas
- **Per-User Tracking**: We use `X-User-ID` mapped to Redis-backed leakage buckets to enforce fair-use quotas.
- **Flood Protection**: Extreme frequency bursts (>10 requests/10s) from a single IP trigger a temporary ban.
- **Tier Enforcement**: API routes (e.g., Image Generation) check user subscription tiers before execution.

### 3. Identity & Session Security
- **Firebase Auth**: Industry-standard JWT validation for all authenticated routes.
- **JTI Blacklist**: Stolen or revoked tokens are instantly blacklisted in Redis, preventing session hijacks.
- **Secret Management**: All production secrets are managed via Google Cloud Secret Manager; no secrets are stored in the codebase.

## 🐛 Reporting a Vulnerability

If you discover a security vulnerability within LEVI-AI, please do **not** open a public issue. Instead, follow our coordinated disclosure process:

1. **Email us**: Send a detailed report to `security@levi-ai.com`.
2. **Include Details**: Describe the vulnerability, the potential impact, and steps to reproduce.
3. **Response Time**: We aim to acknowledge all reports within 24 hours and provide a fix within 72 hours for critical issues.

## 🚫 Out of Scope
- DDoS attacks (handled by Cloud Run / Cloud Armor).
- Social engineering against LEVI-AI employees.
- Vulnerabilities in 3rd party providers (Groq, Together AI, Razorpay).

---
*Last Updated: 2026-03-31*
