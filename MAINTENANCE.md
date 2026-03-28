# LEVI-AI v3.0 — Operational Maintenance Guide 🛠️

**Release Signature: v3.0.0 Bulletproof**

This guide provides administrators with the procedures required to maintain, scale, and secure the **v3.0 Bulletproof** modular architecture.

## 1. Key Rotation Protocols 🔑

To maintain a vault-level security posture, rotate the following credentials every 90 days or upon staff turnover.

- **AWS S3 IAM Keys**: Update `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`. Ensure the new user has `s3:PutObject`, `s3:GetObject`, and `s3:ListBucket` permissions.
- **Razorpay Secret**: Update `RAZORPAY_KEY_SECRET` and `RAZORPAY_WEBHOOK_SECRET`. Re-verify the HMAC signature logic in `backend/payments.py` after rotation.
- **Groq/Together AI**: Update `GROQ_API_KEY` and `TOGETHER_API_KEY`. These are handled by the [CircuitBreaker](file:///c:/Users/mehta/Desktop/New%20folder/LEVI-AI/backend/circuit_breaker.py) logic automatically.
- **Firebase Service Account**: If rotating, update the `FIREBASE_SERVICE_ACCOUNT_JSON` environment variable in Google Cloud Run. **No local file update is required.**

## 2. Monitoring & Incident Response 🚨

The platform uses **Proactive Alerting** via Discord/Slack webhooks.

- **Circuit Breaker Alerts**: If an AI provider fails, you will receive an `🚨 ALERT: Circuit TestBreaker is OPEN` notification.
- **Studio Job Failures**: Any video or image rendering failure with a `CRITICAL` log level will be prefixed with `🚨 ALERT:`.
- **Log Investigation**: Use Google Cloud Logging with the query `jsonPayload.level="CRITICAL" OR jsonPayload.message:"ALERT:"` to identify top-tier production issues.

## 3. Scaling Strategy 📈

The modular architecture is designed to scale independently.

- **Gateway / API Sub-services**: Scale horizontally on Google Cloud Run based on CPU/Request count. (Suggested: 512MB RAM, 1 vCPU per instance).
- **Celery Workers**: Scale these specifically for Studio demand. Workers are compute-intensive (MoviePy/PIL). (Suggested: 2GB RAM, 2 vCPU per instance).
- **Redis Queue**: If `jobs` latency increases, upgrade the Redis instance (e.g., Google Memorystore) to a higher TIER.

## 4. Security Enforcement 🛡️

- **CSP Updates**: If adding a new frontend library or CDN (e.g., Sentry), you MUST update the `csp_parts` in [gateway.py](file:///c:/Users/mehta/Desktop/New%20folder/LEVI-AI/backend/gateway.py) to avoid "Refused to load" errors in the browser.
- **Global Rate Limiting**: Adjust `Chat` (10/min) and `Studio` (5/min) limits in the respective routers if your operational budget allows for higher throughput.

## 5. Absolute Baseline Compliance 🏛️

The platform is initialized under a **Universal 37-Phase Hardening** framework. Any architectural update must satisfy the following:
1. **Security**: Zero-trust media delivery, strict CSP/HSTS, and HMAC signature verification.
2. **Resiliency**: Circuit breakers for all AI providers and proactive Discord/Slack alerting.
3. **Observability**: Request-ID mapping across all frontend/backend boundaries.
4. **Performance**: Selective Tailwind tree-shaking and runtime Gzip compression.

---
**LEVI-AI v3.0 Bulletproof — Architected for Excellence.**
