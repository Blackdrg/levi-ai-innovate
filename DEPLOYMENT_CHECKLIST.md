# LEVI-AI: v6.8 Sovereign Deployment Checklist ✅

This checklist ensures a successful, zero-downtime deployment for the **LEVI-AI v6.8 Sovereign Architecture**.

---

## 🌀 1. Cognitive Infrastructure (BCCI & LEE)
- [x] **Redis Performance**: Verify `stats:avg_response_rating` and `stats:avg_confidence` keys are active.
- [x] **Token Budget**: Confirm `TokenBudget` (8k) in `context_utils.py` aligns with Llama 3.1.
- [x] **Memory Flush**: Verify the 30s Celery Beat task for Redis-to-Firestore syncing is active.

## 🎬 2. Universal Studio & Gallery 
- [ ] **Heavy Queue**: Ensure a separate Celery worker is running for the `heavy` queue (Video tasks).
- [ ] **Storage Buckets**: Confirm `AWS_S3_BUCKET` or `GCS_STORAGE_BUCKET` permissions are configured.
- [ ] **Gallery Index**: Verify direct-to-feed logic for successful generations is operational.
- [ ] **Video Autoplay**: Check `feed.js` for muted autoplay deployment on current production domain.

## 🧠 3. Hybrid Learning & Evolution
- [x] **Escalation State**: Verify the system starts in `HEALTHY`.
- [x] **Gatekeeper**: Confirm `TOGETHER_API_KEY` is set and the 7-day cooldown is active.
- [ ] **Critic Agent**: Verify the `diagnostic_agent` is registered and calibrated (min score: 0.85).

## 🛡️ 4. Resilience & Security
- [x] **Circuit Breakers**: Verify `together_breaker` and `groq_breaker` thresholds in `network.py`.
- [ ] **Atomic Credits**: Confirm Razorpay webhooks correctly trigger credit increments in Firestore.
- [ ] **Rate Limiting**: Verify the 10 RPM (Images) / 2 RPM (Video) limits are enforced in `logic.py`.

## 🚀 5. Final Launch
- [ ] **Environment**: Set `ENVIRONMENT=production`.
- [ ] **Health Probe**: Run `curl https://api.levi-ai.com/health` and verify all engines are `online`.
- [ ] **Manifest Proof**: Verify the `LAUNCH_MANIFEST.md` is shared with the DevOps team.

---

**LEVI v6.8 — Sovereign. Efficient. Self-Scaling.**
*Hardened for the Infinite Learning Loop.*
