# 🩺 System Diagnostics Master (v13.1.0-Hardened-PROD)

Standard health-monitoring and cognitive-fidelity metrics for the LEVI-AI v13.1.0-Hardened-PROD Distributed Stack.

---

## 🔍 1. Standard Testing Hierarchy

LEVI-AI uses a unified testing framework to ensure graduate-level stability:
1.  **Unit Tests:** `pytest tests/unit/` (Component isolation).
2.  **Integration Tests:** `pytest tests/integration/` (Service fabric connectivity).
3.  **Graduation Audit:** `pytest tests/v1_graduation_suite.py` (Full 28-point technical compliance).

---

## ⚡ 2. Latency & Resource Thresholds

- **Postgres (Episodic):** `SELECT 1` (Latency < 20ms).
- **Redis (Working Memory):** `PING` (Latency < 5ms).
- **Neo4j (Knowledge Graph):** `MATCH (n) RETURN n LIMIT 1` (Latency < 50ms).
- **FAISS (Semantic Memory):** Local vector search (Retrieval < 100ms).
- **Ollama (Inference):** `phi3:mini` TTFT (Time To First Token) < 500ms.

---

## 🛡️ 3. Security Diagnostics

- **SHA-256 PII Masking:** `SecurityMiddleware.mask_pii(text)` ➔ `SHA256[:8]` de-identification.
- **Vault Health:** `VaultService.test_encryption()` ➔ `Success`.
- **Sandbox Health:** `DockerSandbox.is_available()` ➔ `Active`.

---

© 2026 LEVI-AI SOVEREIGN HUB.
