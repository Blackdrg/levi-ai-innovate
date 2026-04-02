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

## 👁️ 4. Sovereign Shield (PII & Hijack Protection)
Users attempting to inject malicious instructions or share sensitive PII (Emails, Credit Cards, SSNs) are caught natively by the `Sovereign Shield`. 
1. **Input Sanitization**: `backend/core/planner.py` detects sensitive patterns and forces a Local-Only GGUF route.
2. **Real-time Masking**: `backend/engines/utils/security.py` (`SovereignSecurity`) masks tokens in the outgoing SSE stream.
3. **Boundary Enforcement**: Filters outputs recursively checking against global rules in `backend/core/planner.py`.
