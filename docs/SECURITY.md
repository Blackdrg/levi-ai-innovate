# 🛡️ System Security Framework (v1.0.0-RC1)

Architectural isolation relies fundamentally on Identity, Encryption, and Sanitization. LEVI-AI v1.0.0-RC1 implements a multi-layered security mesh to protect user-specific data and cognitive agents.

---

## 🔐 1. Identity & Encryption (Vault Service)

LEVI-AI v1.0.0-RC1 uses production-grade encryption for all sensitive data.
- **Vault Service (AES-256):** All sensitive user identity traits in Postgres are encrypted at rest. Decryption only occurs during authorized session hydration.
- **Identity Middleware:** All API routes strictly validate JWT sessions and RBAC roles (GUEST, PRO, CREATOR) against the local user store.

## ⚖️ 2. Transaction Integrity & Sync

Mission execution and high-compute tasks are protected by a distributed integrity layer.
- **Distributed Locking:** Uses Redis to prevent race conditions during mission state transitions and credit deductions.
- **DCN Integrity:** Inter-node pulses are HMAC-SHA256 signed using a 32-byte `DCN_SECRET`. Unsigned or tampered pulses are rejected.

## 👁️ 3. Security Middleware & PII Masking

The v1.0.0-RC1 stack implements a production-ready sanitization model.

1.  **PII Masking (SHA-256):**
    - **Deterministic De-identification:** Automatically detects and masks sensitive entities (EMAIL, PHONE, PERSON) via `SHA256(val)[:8]` before model handoff.
    - **Instruction Boundary Guard:** Enforces strict `<USER_MISSION>` and `<SYSTEM_OVERRIDE>` tags to prevent prompt injection.

2.  **Fidelity Adjudication (Deterministic):**
    - **Graduation Fidelity (S):** Missions are audited using a 60/40 weighted formula: 60% from neural appraisal and 40% from rule-based **Deterministic Validation** (syntax, logic, JSON integrity).
    - **Grounding Hub:** Validates all factual claims against the Relational Graph (Neo4j) and Semantic Memory (FAISS).

## 🧩 4. Execution Sandbox (Docker)

The `CodeAgent` executes all generated Python artifacts in an isolated Docker container.
- **Resource Limits:** CPU (0.5) and Memory (512MB) caps are enforced per execution block.
- **Network Isolation:** Zero internet access is permitted from within the code sandbox by default (Egress Proxy allowlist restricted).

---

© 2026 LEVI-AI SOVEREIGN HUB.
