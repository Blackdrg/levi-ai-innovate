# LEVI-AI: Security Architecture Deep Dive
### Specification v1.0.0-RC1

---

## 1. Defense-In-Depth Pipeline

Every mission request passes through 5 security layers before reaching the cognitive core.

```
[Input] → Prompt Injection Shield
        → PII Masking (AES-256-GCM)
        → Rate Limit (Redis Sliding Window)
        → RBAC Tier Gate (G/P/C)
        → Egress Allowlist (Deny-by-Default)
        → [Sovereign Core]
        → Output Scrubbing (XSS/Markdown)
        → PII Re-masking
        → Security Headers (CSP/HSTS)
        → [Authenticated Response]
```

---

## 2. SovereignKMS — Encryption Specification

- **Algorithm**: AES-256-GCM (Authenticated Encryption)
- **Key Derivation**: PBKDF2-HMAC-SHA256 (100,000 iterations)
- **PII Scope**: Email addresses, phone numbers, API keys, SSNs.
- **Storage**: Encrypted ciphertext stored; plaintext never persisted.

### 2.1 Encrypt Flow
```python
# SovereignKMS.encrypt(plaintext: str) → str (base64 ciphertext)
key = PBKDF2HMAC(SHA256, AUDIT_CHAIN_SECRET, salt, 100_000)
ciphertext = AES_GCM_encrypt(key, plaintext)
return base64.encode(salt + iv + ciphertext + tag)
```

---

## 3. EgressProxy — SSRF Prevention

All outbound HTTP calls from agents are routed through the `EgressProxy`.

### 3.1 Allowlist (Deny-by-Default)
```python
ALLOWED_EGRESS_DOMAINS = {
    "api.tavily.com",    # Web search
    "serpapi.com",       # Alternative search
}
# All other domains → SSRFBlockedError raised immediately
```

### 3.2 Blocked Targets
- Private IP ranges: `10.x.x.x`, `172.16-31.x.x`, `192.168.x.x`
- Localhost: `127.0.0.1`, `::1`, `localhost`
- Cloud metadata: `169.254.169.254` (AWS/GCP/Azure)

---

## 4. SecurityHeadersMiddleware — Audit Headers

Injected on every response for OWASP LLM Top 10 compliance:

| Header | Value | Purpose |
| :--- | :--- | :--- |
| `Content-Security-Policy` | `default-src 'self'` | XSS prevention |
| `Strict-Transport-Security` | `max-age=31536000` | HTTPS enforcement |
| `X-Frame-Options` | `DENY` | Clickjacking prevention |
| `X-Content-Type-Options` | `nosniff` | MIME sniffing prevention |
| `X-Sovereign-Version` | `v1.0.0-RC1` | Audit traceability |
| `Referrer-Policy` | `no-referrer` | Data leakage prevention |

---

## 5. RBAC Matrix

| Role | Missions/Day | Vault Access | System Override | Rate Limit |
| :--- | :--- | :--- | :--- | :--- |
| **Guest (G)** | 0 | None | No | 10 req/hr |
| **Pro (P)** | 100 | Read | No | 60 req/min |
| **Creator (C)** | Unlimited | Full | Yes | 300 req/min |

---

## 6. JWT Identity Cycle

```
Login → JWT(access, 15min) + JWT(refresh, 7days)
      ↓
Access Expired → POST /api/v1/auth/refresh (refresh token)
              → New access JWT (JTI blacklist checked)
              ↓
Logout → JTI added to Redis blacklist (TTL = refresh expiry)
```

---

## 7. 5-Tier GDPR Memory Wipe

On user deletion or explicit wipe request:

| Tier | Store | Operation |
| :--- | :--- | :--- |
| T1 | Redis | `DEL user:{id}:*` — all keys |
| T2 | Postgres | `DELETE FROM missions WHERE user_id=?` |
| T3 | Neo4j | `MATCH (n {user_id:?}) DETACH DELETE n` |
| T4 | FAISS | Remove all vectors with `user_id` metadata |
| T5 | training_corpus | `DELETE FROM training_corpus WHERE user_id=?` |

---

*© 2026 LEVI-AI Sovereign Hub — Security Architecture Specification v1.0.0-RC1*
