# LEVI-AI: v6.8 Sovereign Deployment Checklist ✅

This checklist ensures a successful, zero-downtime deployment for the **LEVI-AI v6.8 Sovereign Architecture**.

---

## 🌀 1. Cognitive Infrastructure (BCCI & LEE)
- [ ] **Redis Performance**: Verify `stats:avg_response_rating` and `stats:avg_confidence` keys are initializing correctly.
- [ ] **Token Budget**: Confirm `TokenBudget` limits in `context_utils.py` align with your specific LLM provider limits (e.g., 8k for Llama 3.1).
- [ ] **ICL Patterns**: Verify `profound_patterns` collection exists in Firestore with a high-performance index on `created_at`.
- [ ] **Context Compression**: Run a manual test on `/chat` to verify `Q: {in} -> A: {out}` formatting is active in the system prompt.

## 🧠 2. Hybrid Learning & Evolution
- [ ] **Escalation State**: Verify the system starts in `HEALTHY`. Use the God View dashboard to confirm.
- [ ] **Gatekeeper**: Confirm `TOGETHER_API_KEY` is set and the fine-tuning cooldown (7 days) is understood.
- [ ] **Critic Agent**: Verify the `diagnostic_agent` is registered in `tool_registry.py` and reachable.
- [ ] **Pattern Crystallization**: Confirm that 5-star ratings (explicit or auto) are triggering the `crystallize_profound_pattern` task.

## 🛡️ 3. Resilience & Security
- [ ] **Circuit Breakers**: Verify `together_breaker` and `groq_breaker` thresholds in `network.py`.
- [ ] **Sanitization**: Ensure `anonymize_failure` logic is successfully stripping PII before logging to the shared pattern pool.
- [ ] **Budget Breaker**: Confirm `max_finetune_cost_monthly` (if implemented) is set in your environment.

## 👁️ 4. Monitoring (God View)
- [ ] **Evolution Widget**: Verify the `monitor.html` dashboard shows the `Evolution State` badge.
- [ ] **Metric Polling**: Confirm the `/api/monitor/stats` endpoint is returning `performance` and `evolution_state` fields.
- [ ] **Audit Log**: Verify real-time streaming of `DecisionLog` data to the dashboard via Firebase SDK.

## 🚀 5. Final Launch
- [ ] **Environment**: Set `ENVIRONMENT=production`.
- [ ] **Model Overrides**: Ensure `system:finetuning:last_model_id` is empty for the first boot to use base weights.
- [ ] **Health Check**: Run `curl http://localhost/api/health/evolution` to confirm all evolutionary engines are online.

---

**LEVI v6.8 — Sovereign. Efficient. Self-Scaling.**
*Hardened for the Infinite Learning Loop.*
