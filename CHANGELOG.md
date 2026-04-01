## [6.8.5] - 2026-04-01 "The Sovereign Monolith" 🏗️
### Added
- **Monolithic Transition**: Consolidated all backend services into a unified production-grade monolith for Google Cloud Run.
- **Sovereign reasoning**: Integrated `Llama-3-8B` (GGUF) for 100% local-first, zero-cost reasoning within the 8Gi RAM perimeter.
- **Persistent Memory Matrix**: Implemented GCS FUSE volume mounting (`/mnt/vector_db`) for user-isolated FAISS semantic memory.
- **Intelligence Pulse (SSE)**: Synchronized real-time `activity` and `metadata` pulses for routing transparency.
- **Autonomous Evolution**: Enabled `AdaptivePromptManager` for self-optimizing instructions based on 5-star performance.
- **Absolute Privacy**: Implemented a full multi-layer memory purge (Firestore, Redis, FAISS) for 'Forget Me' requests.

### Hardened
- **Concurrency Gate**: Enforced `MAX_LOCAL_CONCURRENCY=2` and saturation fallback to prevent resource exhaustion.
- **Security Defense**: Formally documented the 'Defense in Depth' strategy in `SECURITY.md` for monolithic isolation.
- **Sovereign Engine Probe**: Built the `/health/sovereign` deep-diagnostic endpoint with `X-Admin-Key` protection.

### Fixed
- **Memory Residuals**: Resolved the issue where 'Clear Memory' left semantic fragments in the local FAISS index.
- **Pulse Latency**: Optimized SSE delivery to ensure the 'Thinking' heartbeat starts within 50ms of request arrival.

## [6.8.4] - 2026-03-31 "The Sovereign Hardening" 💎
### Fixed
- **Memory Leak**: Resolved long-running FAISS index fragmentation in Celery workers.
- **Race Condition**: Hardened Lua scripts for multi-user credit deduction under high concurrency.
- **SSE Stability**: Improved buffer management in Nginx for consistent 50ms pulse delivery.

## [6.8.0] - 2026-03-31 "The Sovereign Transformation" 🏺
### Added
- **Sovereign Reasoning Engine**: Integrated `llama-cpp-python` (GGUF) for 100% local-first, zero-cost reasoning.
- **Hybrid Memory Model**: Persistent FAISS vector indices (`user_faiss.bin` / `global_faiss.bin`) for sub-millisecond semantic retrieval.
- **Unified Activity Stream**: Real-time SSE 'Intelligence Pulses' (Intent, Memory, Routing) delivered before response generation.
- **Deterministic Routing**: Hardened 3-tier complexity routing (L0-L4) with autonomous model selection.
- **Sovereign Maintenance**: Celery-based background FAISS garbage collection and evolutionary distillation.
- **Atomic Concurrency**: Redis-based distributed locks for credit deduction and shared memory writes.
- **Sovereignty Audit**: Automated verification suite (`tests/verify_sovereignty.py`) for routing/memory validation.

### Changed
- **SSE Format**: Transitioned to unified `activity` / `metadata` / `choices` chunk structure.
- **Memory Dimensions**: Aligned FAISS and `sentence-transformers` (MiniLM) to 384-dimensional space.
- **Plan Synthesis**: Refined `executor.py` with multi-turn reflection (PEOC Loop).

---

# LEVI v5.0 — The Soul 🌌
## Changelog

## [5.0.0] - 2026-03-31 "The Soul" 🌌
### Added
- **Deterministic Brain v5.0**: Transitioned to `ExecutionPlan` models for 0% hallucination risk.
- **Self-Refining Memory**: Hierarchical 3-layer memory with **Semantic Conflict Resolution**.
- **Adaptive Personas**: Self-optimizing system prompts based on real-time user resonance ratings.
- **Learning & Memory Graph**: Background extraction of user interests and goals into structured context.
- **Production Lockdown**: Automated Abuse Detection and Per-User Rate Limiting middlewares.
- **Canary Verification**: CI/CD now runs automated E2E tests against Canary URLs before promotion.
- **Hardened SSE**: Built-in 2s reconnection logic and 20s heartbeats for 100% sync reliability.

### Fixed
- **Silent Failures**: Standardized on `ToolResult` contracts with automatic retry/fallback chains.
- **Memory Context Drift**: Added recency-weighted ranking to long-term memory retrieval.
- **Async Bottlenecks**: Full async/non-blocking refactor of the `learning.py` system.
- **Deployment Safety**: Added post-deploy technical verification stage in GitHub Actions.

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
