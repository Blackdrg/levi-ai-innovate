# LEVI v2.0 — Changelog

All notable changes to this project will be documented in this file.

## [5.0.0] - 2026-03-31
### Added
- **True SSE Streaming**: Full token-by-token streaming from Groq API via Server-Sent Events.
- **Response Caching**: 30-minute Redis cache for identical search and chat queries.
- **Webhook Alerts**: Circuit breaker now POSTs to `ALERT_WEBHOOK_URL` on service failure.
- **Ops Runbook**: Centralized `RUNBOOK.md` for production operations.
- **Nginx Ingress**: Production-ready Nginx configuration with SSE optimizations.

### Fixed
- **JTI Blacklist**: Corrected inverted logic in Firestore auth fallback.
- **Memory Pruning**: Fixed `created_at` type mismatch; old facts are now correctly pruned.
- **Docker Context**: Fixed build context issues in `docker-compose.yml`.

### Changed
- **Circuit Breaker**: Consolidated multiple implementations into `backend/utils/network.py`.
- **System Version**: Bumped to v5.0 "Hardened Architecture".

---

## [2.0.0] — 2026-03-31 "The Brain" 🧠

### Added
- **`LeviOrchestrator` class** — single authoritative interface for all AI interactions
- **8-stage pipeline**: Sanitize → Memory → Intent → Decide → Execute → Validate → Store → Output
- **`local_engine.py`** — zero-API engine for greetings, identity queries, and simple FAQ (~60% of traffic served at $0)
- **3-route Decision Engine** (LOCAL / TOOL / API) — deterministic routing based on intent + complexity
- **`validate_response()`** — 3-tier fallback chain guaranteeing non-empty responses even under total LLM failure
- **`EngineRoute` enum** — typed routing values (`LOCAL`, `TOOL`, `API`)
- **`DecisionLog` dataclass** — structured log emitted at every routing decision
- **Expanded intent taxonomy**: `greeting`, `simple_query`, `tool_request`, `image`, `code`, `search`, `complex_query`, `chat`, `unknown`
- **`tests/test_orchestrator.py`** — 42-test comprehensive suite covering all 5 required execution paths
- **Engine route badge** in `chat.js` — 🟢/🟡/🔴 badge shows which engine handled each response
- **`_buildRouteBadge()`** in `chat.js` — color-coded engine indicator with hover tooltip

### Fixed
- **`store_memory` sync bug** — was `def` (sync) called via `asyncio.create_task()` → silent crash, memory never saved. Now `async def` with `asyncio.to_thread()`
- **Router double-wrap bug** — `router.py` was double-wrapping result dict, losing `intent`, `route`, `job_ids`, `request_id`  
- **`check_allowance` patch target** — test was patching source module instead of engine namespace (top-level import binding)
- **`asyncio.create_task(prune_old_facts)` guard** — wrapped in `try/except RuntimeError` for test environment safety
- **`detect_intent` now never raises** — LLM stage wrapped in `try/except`, returns `IntentResult(intent="chat")` on failure
- **`Dict, Any` import missing** in `chat/router.py` — would cause `NameError` on server startup

### Changed
- `planner.py` — extended `INTENT_RULES` with greedy regex patterns for `greeting`, `simple_query`, `tool_request`
- `memory_manager.py` — `_MIDTERM_TIMEOUT` guard on Firestore queries; all sync helpers wrapped in `asyncio.to_thread`
- `router.py` — returns full orchestrator result dict; `BackgroundTasks` passthrough; structured lifecycle logging
- `orchestrator_types.py` — added `EngineRoute`, `DecisionLog`; `OrchestratorResponse` now includes `route` + `request_id`
- `chat.js` — controls block now shows intent label + engine route badge; `loadChatHistory` + `displayWelcomeMessage` stubs added

---

## [1.5.0] — 2026-03-30 "Production Hardening"

### Added
- Redis-based memory write debouncing (Celery Beat flush every 5 min)
- Structured JSON logging with `request_id` + `user_id` correlation
- `log_request_id` / `log_user_id` context vars in `logging_context.py`
- `test_memory_buffering.py` — memory debounce tests

### Fixed  
- Blocking Firestore writes in async context → moved to `asyncio.to_thread`
- Celery Beat scheduler not writing to correct DB

---

## [1.0.0] — 2026-03-29 "Initial Brain"

### Added
- FastAPI gateway with CORS, GZip, rate limiting, JWT auth
- Orchestrator pipeline: Planner → Executor → Synthesizer
- 3-layer memory system (Redis / Firestore / Embeddings)
- Celery background task processing
- Razorpay payment integration
- Firebase Auth integration
- Studio (image generation) + Gallery services
- CI/CD pipelines (Cloud Run + Firebase Hosting)
- Sentry error monitoring
- SSE real-time activity stream
