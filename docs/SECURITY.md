# 🛡️ LEVI-AI: Security Architecture (v14.0.0-Autonomous-SOVEREIGN)

Architectural isolation relies on Identity, Encryption, Sanitization, and Boundary Enforcement. LEVI-AI v14.0.0-Autonomous-SOVEREIGN implements a multi-layered security mesh to protect all user data and system orchestration components.

---

## 1. Defense-In-Depth Pipeline

Every task request passes through 5 sequential security layers before reaching the orchestration engine, and 3 more on output.

```
INPUT PIPELINE
[Raw Input] → Prompt Injection Shield
            → PII Masking (AES-256-GCM)
            → Rate Limit Gate (Redis Sliding Window)
            → RBAC Tier Check (User/Provider/Core)
            → Egress Proxy Allowlist (Deny-by-Default)
            → [Orchestration Engine]

OUTPUT PIPELINE
[Result] → ResultSanitizer (XSS / Markdown)
         → PII Re-masking Check
         → Security Headers (CSP / HSTS / X-Frame)
         → [Authenticated Response]
```

---

## 2. SystemKMS — Encryption Specification

- **Algorithm**: AES-256-GCM (Authenticated Encryption with Associated Data)
- **Key Derivation**: PBKDF2-HMAC-SHA256 (100,000 iterations, random salt per encrypt)
- **PII Scope**: Email addresses, phone numbers, API keys, credential strings
- **System Secret**: `SYSTEM_KMS_SECRET` env var (production must use 64-char hex)
- **Decryption**: Plaintext only reconstructed within authorized task scope — never persisted

> [!CAUTION]
> The default `SYSTEM_KMS_SECRET` in `.env.example` is **NOT** production-safe. Generate a 64-character hex key before any production deployment.

---

## 3. EgressProxy — SSRF Prevention

All outbound HTTP calls from agents are **exclusively** routed via the `EgressProxy`.

### Active Allowlist (Deny-by-Default)
```python
ALLOWED_EGRESS_DOMAINS = {
    "api.tavily.com",    # Web search (approved)
    "serpapi.com",       # Alternative search (approved)
}
# ALL other domains → SSRFBlockedError raised immediately
```

### Blocked Categories
| Category | Examples |
| :--- | :--- |
| **Private IP ranges** | `10.x.x.x`, `172.16-31.x.x`, `192.168.x.x` |
| **Localhost** | `127.0.0.1`, `::1`, `localhost` |
| **Cloud Metadata** | `169.254.169.254` (AWS/GCP/Azure IMDS) |
| **Unapproved APIs** | All domains not in the allowlist |

---

## 4. Security Headers Middleware

Enforced on every response via `SecurityHeadersMiddleware`:

| Header | Value | Purpose |
| :--- | :--- | :--- |
| `Content-Security-Policy` | `default-src 'self'` | XSS prevention |
| `Strict-Transport-Security`| `max-age=31536000; includeSubDomains` | HTTPS enforcement |
| `X-Frame-Options` | `DENY` | Clickjacking prevention |
| `X-Content-Type-Options` | `nosniff` | MIME-type sniffing prevention |
| `X-System-Version` | `v14.0.0` | Audit traceability header |
| `Referrer-Policy` | `no-referrer` | Data leakage prevention |

---

## 5. RBAC Permission Matrix

| Role | Tasks/Day | Vault Access | System Override | Rate Limit |
| :--- | :--- | :--- | :--- | :--- |
| **Guest (G)** | 0 | None | No | 10 req/hr |
| **Pro (P)** | 100 | Read-only | No | 60 req/min |
| **Admin (A)** | Unlimited | Full | Yes | 300 req/min |

---

## 6. Docker Sandbox

The `CodeAgent` executes all model-generated code in an isolated container.

- **Interface**: **Rootless Unix Socket** — Legacy TCP:2375 is **disabled and removed**.
- **CPU Cap**: 0.5 cores per execution block
- **Memory Cap**: 512MB per execution block
- **Network**: Zero internet access from within the container (Egress Proxy controls outbound)

> [!WARNING]
> Never re-enable the TCP Docker socket (`-H tcp://0.0.0.0:2375`) on production hosts. This creates a container-escape vector.

---

## 7. JWT Identity Cycle

```
Login
  → JWT access token (15min expiry) + refresh token (7 days)

Access Token Expired
  → POST /api/v1/auth/refresh
  → JTI blacklist checked in Redis
  → New access JWT issued

Logout / Wipe
  → JTI added to Redis blacklist (TTL = refresh token expiry)
  → All task sessions invalidated
```

---

## 8. GDPR Data Governance (Erasure)

On explicit data deletion request, the system executes an atomic ordered wipe across all 5 persistence tiers:

| Tier | Store | Operation |
| :--- | :--- | :--- |
| T1 | Redis | `DEL system:user:{id}:*` — all keys and blackboard |
| T2 | Postgres | `DELETE FROM sessions WHERE user_id=?` |
| T3 | Neo4j | `MATCH (n {user_id:$u}) DETACH DELETE n` |
| T4 | HNSW Vault | Remove all vectors with matching `user_id` metadata |
| T5 | training_corpus | `DELETE FROM training_corpus WHERE user_id=?` |

---

## 9. Rate Limiting Specification

Redis-backed **sliding window** algorithm using sorted sets (ZSETs):

- **Window**: 60 seconds rolling
- **Keys**: `rate_limit:{user_id}:{endpoint}`
- **On Breach**: `429 Too Many Requests` with `Retry-After` header

---

© 2026 LEVI-AI Sovereign OS — Security Specification v14.0.0 Production Stable
