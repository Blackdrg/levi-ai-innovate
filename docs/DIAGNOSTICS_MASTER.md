# 🩺 System Diagnostics Master (v14.0 Production)

Standard health-monitoring and performance metrics for the LEVI-AI v14.0 Distributed Stack.

---

## 🔍 1. Standard Testing Hierarchy

LEVI-AI uses a unified testing framework to ensure system stability:
1.  **Unit Tests:** `pytest tests/unit/` (Component isolation).
2.  **Integration Tests:** `pytest tests/integration/` (Service fabric connectivity).
3.  **Readiness Audit:** `pytest tests/production_readiness_suite.py` (Full technical compliance).

---

## ⚡ 2. Latency & Resource Thresholds

- **Postgres (Episodic):** `SELECT 1` (Latency < 20ms).
- **Redis (Working Memory):** `PING` (Latency < 5ms).
- **Neo4j (Knowledge Graph):** `MATCH (n) RETURN n LIMIT 1` (Latency < 50ms).
- **FAISS (Semantic Memory):** Local vector search (Retrieval < 100ms).
- **Ollama (Inference):** `phi3:mini` TTFT (Time To First Token) < 500ms.

---

## 🛡️ 3. Security Diagnostics

- **PII Masking:** `SecurityMiddleware.mask_pii(text)` ➔ De-identification.
- **Vault Health:** `VaultService.test_encryption()` ➔ `Success`.
- **Sandbox Health:** `DockerSandbox.is_available()` ➔ `Active`.

---

© 2026 LEVI-AI HUB. Engineered for Technical Excellence.
