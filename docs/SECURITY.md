# 🛡️ The Sovereign Security Framework

Architectural isolation relies fundamentally on Identity and Economics. You cannot scale an LLM orchestrator without immediately hemorrhaging developer tokens if your network bounds fail.

---

## 🔐 1. Authentication (Firebase Handshake)
LEVI-AI routes completely block unregistered users from accessing High-Compute Tiers (Creator/Pro video parsing). 
- **`backend/services/auth/logic.py`**: Executes strict validation of the Firebase `idToken` attached as `Authorization: Bearer` against the `firebase-admin` internal SDK.
- It returns user Identity Maps tied to `uid` values mapped in Firestore, bypassing standard session-cookie hijacking vulnerabilities.

## 💰 2. Transaction Integrity (Redis Atomic Locks)
Generating an AI video can cost >$0.02 and take 4 minutes. A malicious user submitting 50 rapid requests could cripple the host.
- **`backend/db/redis_client.py` (`distributed_lock`)**: Protects the exact second an AI Studio deduction initiates via `backend.services.payments.logic.use_credits()`.
- Wait blocks ensure credit reads and updates fire simultaneously via Lua scripts to prevent **Race Conditions**. 

## ⚖️ 3. Webhook Cryptography (Razorpay)
When Stripe/Razorpay issues an intent success status to top up an account:
1. `backend/api/payments.py` receives the payload.
2. It mathematically checks `X-Razorpay-Signature` against `RAZORPAY_KEY_SECRET` utilizing `hashlib.sha256` HMAC validation.
3. This completely prevents bad actors from fabricating `payment.captured` webhooks via Postman requests.

## 👁️ 4. Sovereign Shield & Mission Auditing (v8)
The v8 "Cognitive Monolith" introduces a dual-layer security model: **Input Sanitization** (Sovereign Shield) and **Output Auditing** (Sovereign Auditor).

1. **Input Sanitization (Sovereign Shield):**
   - **PII Masking:** `backend/api/v1/orchestrator.py` automatically detects and masks sensitive data (Emails, SSNs) before it reaches the LLM.
   - **Hijack Protection:** The **Perception Engine** filters malicious system prompt injections.

2. **Output Auditing (Sovereign Auditor):**
   - **Mission Fidelity (0.85):** Every mission is audited by the **CriticAgentV8**. If the **Fidelity Score** falls below 0.85, a **Correction Wave** is triggered.
   - **Hallucination Detection:** The auditor explicitly checks for grounding against the **Semantic Vault** (Mongo) and search results to prevent logic drift.

3. **Boundary Enforcement:**
   - **Real-time Masking:** The v8 SSE parser in `backend.api.v1.orchestrator` masks tokens in the outgoing stream if a security breach is detected during generation.
   - **Network Isolation:** High-compute tasks are executed in a topological wave, ensuring logical isolation from the primary API request loop.
