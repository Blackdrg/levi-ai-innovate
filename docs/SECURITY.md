# 🛡️ The Sovereign Security Framework (v8.11.1)

Architectural isolation relies fundamentally on Identity, Encryption, and Sanitization. LEVI-AI v8.11.1 implements a multi-layered security mesh to protect user-specific cognitive traits.

---

## 🔐 1. Identity & Encryption (SovereignVault)

LEVI-AI v8.11.1 graduates beyond simple plaintext storage for user identity.
- **SovereignVault (AES-256):** All Tier 4 Identity traits in Postgres are encrypted at rest via `SovereignVault.encrypt()`. Decryption only occurs during authorized context hydration.
- **Firebase Handshake:** Routes strictly validate the Firebase `idToken` against the `firebase-admin` internal SDK, returning `uid` values mapped to internal Sovereign IDs.

## ⚖️ 2. Transaction Integrity (Redis Atomic Locks)

Mission execution and high-compute tasks are protected by a distributed locking mechanism.
- **Distributed Locking:** Prevents race conditions during credit deductions and agent commissions.
- **Webhook Cryptography:** Razorpay/Stripe payloads are mathematically verified using `hashlib.sha256` HMAC validation against `RAZORPAY_KEY_SECRET`.

## 👁️ 3. Sovereign Shield & NER Sanitization

The v8.11.1 "Cognitive Monolith" implements a dual-layer sanitization model.

1.  **Input Sanitization (Sovereign Shield):**
    - **NER PII Masking:** Automatically detects and masks sensitive entities before hitting external inference (Groq, OpenAI). Protected entities: `PERSON`, `ORG`, `LOC`, `PERCENT`, `MONEY`, `EMAIL`, `PHONE`.
    - **Hijack Protection:** The **Perception Engine** filters for "ignore previous instructions" injection patterns.

2.  **Output Auditing (Sovereign Auditor):**
    - **Mission Fidelity (0.85):** Every mission is audited by the **CriticAgentV8**. If the **Fidelity Score** falls below 0.85, a **Correction Wave** is triggered.
    - **Logic Grounding:** The auditor explicitly checks for grounding against the Knowledge Graph (Neo4j) and Semantic Store (FAISS).

## 🧩 4. Execution Sandbox

The `CodeAgent` executes all generated Python artifacts in an isolated, zero-host-access sandbox.
- **Resource Limits:** CPU and Memory caps are enforced per execution block.
- **Network Isolation:** No external internet access from within the PythonREPL sandbox.

---

© 2026 LEVI-AI SOVEREIGN HUB.
