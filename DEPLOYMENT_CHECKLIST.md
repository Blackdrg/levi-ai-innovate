# LEVI-AI: v6.8 Sovereign Deployment Checklist ✅

This checklist ensures a successful, zero-downtime deployment for the **LEVI-AI v6.8 Sovereign Architecture**.

---

## 🌀 1. Cognitive Infrastructure (Sovereign Mind)
- [x] **Local Model**: Verify `llama-3-8b.gguf` is loaded and `LocalEngine` reports `READY`.
- [x] **FAISS Index**: Confirm `user_faiss.bin` and `global_faiss.bin` are initialized (384-dim).
- [x] **Redis Buffer**: Verify the 30s Celery Beat task for Redis-to-Firestore syncing is active.
- [x] **Memory Hydration**: Confirm vector recovery from Firestore on cold boot is functional.

## 🎬 2. Universal Studio & Gallery 
- [x] **Heavy Queue**: Ensure a separate Celery worker is running for the `heavy` queue (Pattern Distillation).
- [ ] **Storage Buckets**: Confirm `AWS_S3_BUCKET` or `GCS_STORAGE_BUCKET` permissions are configured for model weights.
- [ ] **Gallery Index**: Verify direct-to-feed logic for successful generations is operational.
- [ ] **SSE Pulses**: Check `chat.js` for real-time "Intelligence Pulse" rendering.

## 🧠 3. Hybrid Learning & Evolution
- [x] **Escalation State**: Verify the system starts in `SOVEREIGN` state.
- [x] **Evolution Task**: Confirm `run_autonomous_evolution` is scheduled and has write access to prompts.
- [ ] **Soul Optimizer**: Verify the `SoulOptimizer` is registered and calibrated (min resonance: 0.85).

## 🛡️ 4. Resilience & Security
- [x] **Circuit Breakers**: Verify `together_breaker` and `local_breaker` thresholds in `network.py`.
- [ ] **Atomic Credits**: Confirm Lua scripts correctly trigger credit increments in Redis.
- [ ] **Rate Limiting**: Verify the Sovereign-specific rate limits (40 RPM) are enforced in `gateway.py`.

## 🚀 5. Final Launch
- [ ] **Environment**: Set `ENVIRONMENT=production` and `USE_SOVEREIGN_ROUTING=true`.
- [ ] **Health Probe**: Run `curl https://api.levi-ai.com/health/sovereign` and verify all engines are `online`.
- [ ] **Manifest Proof**: Verify the `LAUNCH_MANIFEST.md` is shared with the DevOps team.

---

**LEVI v6.8 — Sovereign. Efficient. Self-Scaling.**
*Hardened for the Sovereign Intelligence Loop.*
