# LEVI-AI Sovereign OS (v14.0.0-Autonomous-SOVEREIGN)

LEVI-AI is a high-fidelity, predictable, and failure-isolated distributed AI operating system. It transforms complex autonomous reasoning into a controlled cognitive pipeline, enabling deterministic execution of mission-critical tasks through a Sovereign Task Graph (DAG).

---

## 1. Overview

The active v14 runtime now inserts a mandatory **Reasoning Core** between planning and execution. Every mission can go through critique, dry-run simulation, confidence scoring, and plan refinement before the Executor runs the DAG.

LEVI-AI is designed as a **Cognitive Operating System** that manages the lifecycle of AI missions—from intent classification and goal generation to parallelized agent execution and multi-tier memory synchronization. It addresses the inherent unpredictability of large language models by enforcing strict execution contracts, centralized state tracking, and a unified memory consistency layer.

### Core Philosophy

- **Local-First**: Prioritizes local inference (Ollama) for privacy and zero-cost logic.
- **Deterministic**: Every action is planned in a DAG before execution begins.
- **Sovereign**: Absolute control over data, memory, and model routing.
- **Distributed**: Built for high-availability across multiple cognitive nodes (DCN).

### Current Status (2026-04-09)

The designated workflow is connected end-to-end:

`Gateway -> Orchestrator -> Goal -> Planner -> Reasoning -> Executor -> Agents -> Memory -> Response`

What is implemented and verified:

- Workflow contracts are explicit and inspectable.
- DAG validation, retries, sandbox boundaries, and mission budgets are enforced in the executor path.
- DAG Depth limitations gracefully batch using sub_dag chunking instead of erroring out.
- True Fast-path Bypass is active for high-speed low-complexity intents.
- Dynamic Token-Optimization dynamically down-routes basic queries to `L1` models to preserve capital.
- Backpressure now uses VRAM, CPU, RAM, and queue depth rather than VRAM alone.
- Load Balancing uses a DCN Predictive load-distribution algorithm based on node CPU/Mem heartbeat polling via Redis Hashes.
- Audit-ready security layer is active, enforcing an SSRF allowlist, CSP headers, and sliding window tiered rate limiting globally.
- Security enforcement is continuously verified via integration tests covering SSRF blocks, header presence, and 429 quota exhaustion.
- `/health` now performs real dependency checks for Redis, Postgres, and `Ollama /api/tags`, while `/ready` reports dependency and production-readiness state. Kubernetes HPA metrics are directly exposed via `auto_scaler.py`.
- Prometheus metrics, OpenTelemetry tracing, Kubernetes rollout manifests, and CI validation are wired into the active runtime.
- Structured agent and executor logging now emits `trace_id`, `mission_id`, `node_id`, `duration_ms`, and `status`.
- RBAC hardening tests now cover missing tokens, expired tokens, and wrong-role tokens.
- Mission idempotency has a concurrent regression test that verifies only one identical in-flight mission executes.
- Executor compensation is now exercised in tests instead of being documentation-only. Agents possess internal reflexive multi-retry self-correction loops.
- Graceful Teardown universal tracking transitions all live missions to an `INTERRUPTED` state to flush logs safely upon `SIGTERM` signals.

Targeted production wiring suite currently passes:

```bash
.\.venv\Scripts\python.exe -m pytest backend/tests/test_gateway_workflow_manifest.py backend/tests/test_pipeline_workflow.py backend/tests/test_production_wiring.py backend/tests/test_stability_hardening.py backend/tests/test_reasoning_core_upgrade.py backend/tests/test_state_and_replay_upgrade.py -q
```

Verified result on 2026-04-09:

- `19 passed`
- Additional hardening regression suite: `9 passed`
- Chaos Mesh and Circuit Breakers: `8 passed`

Known remaining gaps:

- Route-by-route smoke coverage for every feature surface is not complete yet.

Recently Closed (Production Hardening Final Phase):
- Full chaos drills against Neo4j disconnections, GPU saturation, and split-brain Redis caching are actively modeled in `test_chaos_mesh.py`.
- Graceful shutdown now properly drains the Orchestrator's internal tracked states, ensuring zero partially tracked memory loss.
- Passive Learning Loop Strategy Culling. Weak graph templates decay and are pruned below 0.65 fidelity automatically.
- Front-end integration of `ReplayDebugger.jsx` interactive visualizer built upon Nextjs Cybernetic framework.
- Developer Python API SDK (`levi_client.py`) published.

---

## 2. System Capabilities

### 2.1 Orchestration & Planning

- **Goal Engine**: Translates raw user input into structured, multi-step mission objectives.
- **DAG Planner**: Generates an optimized Task Graph with explicit dependencies and contracts.
- **Central Execution State Machine**: Authoritative tracking from `CREATED` to `COMPLETE`.
- **Reasoning Core**: Validates DAG logic, simulates outcomes before execution, scores plan confidence, and can force a second planning pass.
- **Mission Idempotency**: Duplicate mission protection prevents equivalent in-flight requests from executing twice.

### 2.2 Memory System

- **Episodic**: 7-day rolling window in Redis for rapid context retrieval.
- **Factual**: Immutable Interaction Log in PostgreSQL for long-term persistence.
- **Relational**: Neo4j knowledge graph for mapping entities and semantic relationships.
- **Semantic**: Vector DB (FAISS/HNSW) for RAG and similarity-based discovery.
- **Decision-Aware Recall**: A lightweight strategy ledger captures which graph shapes worked best for each intent.

### 2.3 Inference Layer

- **Local (Ollama)**: Primary execution path for sensitive or low-complexity tasks.
- **Cloud Fallback**: Adaptive routing to Together/Groq/OpenAI when local resources are under pressure.
- **Multi-Signal Backpressure**: Automatically throttles concurrency based on VRAM, CPU, RAM, and executor queue depth.

### 2.4 Security & Governance

- **Worker Isolation**: Scoped memory and tool sandboxing for every task.
- **RBAC**: Fine-grained role-based access control for tenants and resources.
- **Audit Ledger**: Immutable, monthly-partitioned log with HMAC-SHA256 integrity chains.
- **Default Secret Guardrails**: Startup checks and pre-commit hooks flag insecure placeholder secrets.

---

## 3. Architecture Overview

### 3.1 Request Lifecycle Flow

```mermaid
graph TD
    User[User Request] --> Gateway[FastAPI Gateway]
    Gateway --> Auth[RBAC & Security Shield]
    Auth --> Orchestrator[Orchestrator]
    Orchestrator --> Goal[Goal Engine]
    Goal --> Planner[DAG Planner]
    Planner --> Reasoning[Reasoning Core]
    Reasoning --> Executor[Graph Executor]
    Executor --> Wave[Wave Scheduler]
    Wave --> Agents[Specialized Agents]
    Agents --> Tools[Isolated Tools]
    Tools --> Memory[Memory Sync]
    Memory --> Response[Final Response]
```

### 3.2 Memory Flow (Single Write Authority)

```mermaid
graph LR;
    Runtime["Runtime State"] --> Redis["Redis - Source of Truth"];
    Redis --> MCM["Memory Consistency Manager"];
    MCM --> Postgres["PostgreSQL - Immutable History"];
    MCM --> Neo4j["Neo4j - Relational Knowledge"];
    MCM --> Vector["Vector DB - Semantic Memory"];
```

### 3.3 Agent System Hierarchy

```mermaid
graph TD
    Brain[LeviBrain v14.0] --> Intent[Intent Classifier]
    Brain --> Policy[Brain Policy Engine]
    Policy --> Swarm[Agent Swarm]
    Swarm --> Logic[Logic: Code, Task, Consensus]
    Swarm --> Data[Data: Search, Research, Document]
    Swarm --> Creative[Creative: Image, Video]
```

### 3.4 Complete System Architecture

```mermaid
graph TD;

  %% === Ingress & Infrastructure ===
  subgraph Kubernetes Infrastructure
    LB[K8s predictive Load Balancer]
    HPA[Prometheus HPA Metrics via auto_scaler.py]
    LB --> GW
    HPA --> LB
  end

  subgraph Gateway Tier
    GW["FastAPI App Gateway"]
    RATE["Tiered Sliding Window Rate Limiter"]
    SH["RBAC / SSRF Shield & CSP"]
    PII["Prompt Injection / Secret Guard"]
    
    GW <--> RATE
    GW --> PII
    PII --> SH
  end

  %% === Central Orchestration ===
  subgraph Central Orchestration
    ORC["Orchestrator (Mission Controller)"]
    SM["Central Execution State Machine"]
    TEAR["Graceful Teardown Hook"]
    IDEMP["Idempotency Verifier"]
    
    SH --> IDEMP
    IDEMP --> ORC
    ORC <--> SM
    TEAR -.-> ORC
  end

  %% === Planning & Brain Governance ===
  subgraph Brain Governance
    GE["Goal Engine (Objective Translation)"]
    ROUTER["ModelRouter (Dynamic Token Optimization & Shadow Routing)"]
    PL["DAG Planner (Task Execution Contracts)"]
    RC["Reasoning Core (Critique & Safe-Mode Gen)"]
    FP["Fast-Path Bypass"]
    LL["Learning Loop (Strategy Culling / LoRA)"]
    
    ORC --> GE
    GE --> ROUTER
    ROUTER --> PL
    PL --> FP
    FP --"Low Complexity"--> EX
    FP --"High Complexity"--> RC
    RC <--> LL
    RC --> EX
  end

  %% === Execution & Distributed Network ===
  subgraph DCN_NET ["Distributed Execution Network (DCN)"]
    EX["Graph Executor (Wave Parallelism)"]
    SCHED["Wave Scheduler & Priority Queues"]
    VRAM["GPU Backpressure (VRAMGuard)"]
    DCN["DCN Peer Gossip & Heartbeats"]
    
    RC -.-> EX
    EX --> SCHED
    EX <--> VRAM
    EX <--> DCN
  end

  %% === Agent Ecosystem ===
  subgraph Sovereign Agent Swarm
    AG_BASE["SovereignAgent Base (Reflexive Correction)"]
    AG_CODE["Artisan (Code & Safe Sandbox)"]
    AG_TASK["HardRule (Logic)"]
    AG_SEARCH["Scout (Search & Retrieval)"]
    AG_DOC["Analyst (OCR/Parsing)"]
    COMPENSE["Compensation Engine (Rollbacks)"]
    
    SCHED --> AG_BASE
    AG_BASE --> AG_CODE
    AG_BASE --> AG_TASK
    AG_BASE --> AG_SEARCH
    AG_BASE --> AG_DOC
    AG_BASE -.-> COMPENSE
  end

  %% === Memory Integrity ===
  subgraph Memory Architecture
    MCM["Memory Consistency Manager (MCM)"]
    RED["Redis (Tier 1: Episodic & Queue)"]
    PG["PostgreSQL (Tier 2: Factual Logs / Audit)"]
    NEO["Neo4j (Tier 3: Relational Knolwedge)"]
    VEC["FAISS/Vector DB (Tier 4: Semantic RAG)"]
    HEAL["MCM Asynchronous Reconciliation Jobs"]
    
    AG_BASE --> MCM
    MCM --> RED
    MCM --> PG
    MCM --> NEO
    MCM --> VEC
    HEAL <--> RED
    HEAL --> NEO
  end

  %% === Telemetry & Replay ===
  subgraph Observability
    TR["Cognitive Tracer"]
    PRO["Prometheus Metrics (/metrics)"]
    REP["Replay Debugger UX"]
    
    ORC --> TR
    GW --> PRO
    TR --> REP
  end

  MCM -.->|Context Feedback| ORC
```

---

## 4. Core Components (System Blueprint)

| Module | Purpose | Input | Output | Dependencies |
| :--- | :--- | :--- | :--- | :--- |
| **Gateway** | API Entry & Security | HTTP Request | Sanitized Payload | RBAC, Shield |
| **Orchestrator** | Mission Lifecycle | User Intent | Final Response | Goal Engine, Planner |
| **Goal Engine** | Objective Generation | Perception | Mission Goals | Memory Manager |
| **Planner** | DAG Generation | Goal | Task Graph (DAG) | Brain Policy, LLM |
| **Reasoning Core** | Plan Critique & Simulation | Task Graph | Confidence, Strategy, Refined Graph | Planner, Replay Metadata |
| **Executor** | Parallel Wave Execution | DAG | Node Results | Agents, Redis |
| **Memory Manager** | Tiered Sync & Retrieval | Events | Merged Context | MCM, Neo4j, FAISS |
| **MCM** | Memory Consistency | Memory Events | Versioned State | Redis, Pipeline |
| **Learning Loop** | Outcome Capture & Strategy Reuse | Mission Audit | Best DAG Templates | Evaluator, Corpus, Strategy Ledger |

---

## 5. Execution Model

### 5.1 Task Execution Contract (TEC)

Every mission is decomposed into a directed acyclic graph (DAG) of task nodes. Each node defines a **TEC**:

- **`timeout_ms`**: Explicit execution deadline.
- **`max_retries`**: Capped retry attempts (default: 2).
- **`allowed_tools`**: Restricted tool access per agent.
- **`memory_scope`**: Scoped memory access (`session`, `mission`, `global`).
- **`fallback_output`**: Safe result returned if a node exhausts retries.
- **`compensation_action`**: Recovery action recorded for failure handling and replay.

### 5.2 Mandatory Reasoning Pass

Before the DAG reaches the Executor, the Reasoning Core performs:

- **Plan Critique**: Detects missing dependencies, shallow plans, and weak resilience structure.
- **Simulation Pass**: Dry-runs the DAG with mock outputs to expose blocked branches.
- **Confidence Scoring**: Produces a per-plan confidence score used to trigger refinement.
- **Execution Strategy Selection**: Chooses normal DAG execution or `safe_mode` linear fallback.

The planner now supports a minimum two-pass flow when the first graph is weak: generation, critique, then refinement.

### 5.3 Wave Scheduling & Backpressure

The Executor processes the DAG in parallel "waves." A wave consists of all nodes whose dependencies are satisfied.

- **Adaptive Concurrency**: Parallelism is dynamically throttled based on VRAM, CPU, RAM, and queue pressure.
- **Budgeting**: Enforces mission-wide `token_limit` and `tool_call_limit` to prevent resource exhaustion.
- **Safe Mode**: Forces linear execution when the plan is risky or partially blocked.

### 5.4 Workflow Introspection

The runtime exposes the designated workflow manifest at `GET /api/v1/telemetry/workflow`.

That endpoint reports:

- The expected stage order through the core pipeline.
- Contract-level integration details such as trace headers.
- Core production metrics used by dashboards and alerts.

---

## 6. Memory System (4-Tier Architecture)

| Tier | Implementation | Purpose | Sync Rule |
| :--- | :--- | :--- | :--- |
| **Tier 1 (Episodic)** | Redis | Recent session history | Runtime only (7d TTL) |
| **Tier 2 (Factual)** | PostgreSQL | Immutable interaction log | Immediate persist |
| **Tier 3 (Relational)** | Neo4j | Knowledge graph triplets | Derived via Pipeline |
| **Tier 4 (Semantic)** | Vector DB | Semantic fact retrieval | Derived via Embedding |

**Memory Consistency Manager (MCM)**:

- Acts as the runtime arbiter for all writes.
- Implements versioned events to prevent conflict resolution issues in distributed nodes.
- Provides deduplication markers to prevent redundant vector storage.
- Adds per-event checksums for source-of-truth verification.
- Supports retry queue handoff for delayed derived-store synchronization.

### 6.1 Mission Learning Loop

Each completed mission is treated as a training signal:

- **Outcome Evaluator**: Scores fidelity, grounding, and latency.
- **Pattern Capture**: High-quality missions are stored in the training corpus.
- **Strategy Ledger**: Best-performing graph signatures are retained per intent and reused during planning.

---

## 7. Agent Swarm (Registry)

LEVI-AI utilizes a specialized swarm of agents, each acting as a "dumb executor" governed by the central Orchestrator.

### Logic & Planning

- **Artisan (CodeAgent)**: Generates high-fidelity code and architectural patterns.
- **HardRule (TaskAgent)**: Enforces recursive goal decomposition and strict intent logic.
- **SwarmCtrl (ConsensusAgent)**: Adjudicates across parallel outputs for collective resonance.

### Data & Retrieval

- **Scout (SearchAgent)**: Real-time discovery via web-search tools.
- **Researcher (ResearchAgent)**: Multi-source synthesis and citation bundle generation.
- **Analyst (DocumentAgent)**: Document parsing and matrix analysis.

### Specialized Functions

- **Imaging (ImageAgent)**: Generative visual content creation.
- **Video (VideoAgent)**: Frame-consistent video generation.
- **Memory (MemoryAgent)**: Populates Neo4j with relational knowledge triplets.
- **Diagnostic (DiagnosticAgent)**: Real-time system health and troubleshooting.

---

## 8. Database Schema & Multi-Tenancy

The system uses PostgreSQL as the authoritative store for user profiles, missions, and audits.

### Key Tables

- **`user_profiles`**: Central identity store with `tenant_id` partitioning.
- **`user_traits`**: Distilled behavioral archetypes (e.g., 'Stoic', 'Technical').
- **`missions`**: Distributed mission ledger recording objective, status, and fidelity scores.
- **`audit_log`**: Month-partitioned, cryptographically-chained ledger for compliance.
- **`cognitive_usage`**: Token and resource consumption tracking per user/mission.

### Multi-Tenancy

Every persistent record includes a `tenant_id`. The application enforces Row-Level Security (RLS) and cryptographic partitioning via the KMS layer to ensure data isolation.

---

## 9. Setup & Installation

### Prerequisites

- **Hardware**: NVIDIA GPU (8GB+ VRAM recommended).
- **Environment**: Linux/WSL2 (Windows native requires `cmd.exe`).
- **Tools**: Docker, Python 3.10+, Node.js 18+.

### Configuration (`.env`)

```env
# Infrastructure
REDIS_URL=redis://localhost:6379/0
POSTGRES_URL=postgresql+asyncpg://user:pass@localhost:5432/levi
NEO4J_URI=bolt://localhost:7687

# Cognitive Layer
OLLAMA_HOST=http://localhost:11434
TOGETHER_API_KEY=your_key
TAVILY_API_KEY=your_key

# Security
AUDIT_CHAIN_SECRET=replace-with-real-secret
ENCRYPTION_KEY=replace-with-real-key
JWT_SECRET=replace-with-real-jwt-secret
INTERNAL_SERVICE_KEY=replace-with-real-service-key
```

### Installation Steps

1. **Infrastructure**: Start services via Docker Compose.

   ```bash
   docker compose up -d
   ```

2. **Backend**: Install dependencies and initialize DB.

   ```bash
   pip install -r requirements.txt
   alembic -c backend/alembic.ini upgrade head
   ```

3. **Frontend**: Install dependencies and build.

   ```bash
   cd frontend && npm install && npm run build
   ```

4. **Launch**: Start the Sovereign Gateway.

   ```bash
   npm run dev
   ```

5. **Production Verification (Windows)**: Run the integrated 10-step deploy checker.
   
   ```powershell
   .\scripts\deploy\verify_production.ps1
   ```

---

## 10. API Specification (v1.0)

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/orchestrator/mission` | POST | Initiates a new cognitive mission. |
| `/api/v1/brain/pulse` | GET | Returns live system health and model routing status. |
| `/api/v1/memory/context` | GET | Retrieves merged context from all 4 memory tiers. |
| `/api/v1/auth/session` | POST | Generates a new secure session token. |
| `/api/v1/missions/replay/{id}` | GET | Triggers deterministic replay of a previous mission. |
| `/metrics` | GET | Exposes Prometheus telemetry for system monitoring. |

---

## 11. Failure Handling & Recovery

| Failure Category | Detection Mechanism | Recovery Logic | Escalation |
| :--- | :--- | :--- | :--- |
| **DAG Conflict** | Planner Validation | Regenerate linear plan | Abort mission |
| **Tool Failure** | Executor Exception | Node retry (max 2) | Fallback to Chat |
| **Agent Timeout** | TEC Enforcement | Exponential backoff | Compensate node |
| **Memory Desync** | MCM Version or checksum mismatch | Force source-of-truth verification | Log Audit |
| **VRAM Overload** | VRAM Monitor Pulse | Disable Critic loops | Linear execution |
| **Cloud Fallback** | Model Router Pulse | Switch to local Ollama | Service Degraded |
| **Duplicate Mission** | Idempotency claim collision | Return existing mission handle | Suppress duplicate execution |

### Compensation Engine

If a critical task node fails after all retries, the **Compensation Engine** executes rollback actions defined in the TEC (e.g., reverting database changes or emitting a failure pulse to the user). The executor now records executed compensation metadata on terminal node failure; broader live rollback workflows still need more chaos coverage.

---

## 12. Observability & Telemetry

### 12.1 Global Tracing

Every request carries a `TRACE_ID` injected at the Gateway. Spans are recorded for:

- **Planning**: Intent, Goal, DAG Generation, critique, simulation, and refinement.
- **Execution**: Node start/stop, Latency, Tool output.
- **Persistence**: MCM sync status, DB commit latency.
- **Replay**: Mission input, reasoning strategy, and simulated graph shape.

Structured logs also include:

- `trace_id`
- `mission_id`
- `node_id`
- `duration_ms`
- `status`

### 12.2 Health Graph

The `/api/v1/orchestrator/health/graph` endpoint aggregates real-time stability metrics:

- **Throughput**: Queue depth, DAG failure rates.
- **Resources**: VRAM usage, Redis/Neo4j query latencies.
- **Quality**: Fidelity scores across the last 100 missions.

---

## 13. Testing Strategy

LEVI-AI employs a multi-layered testing strategy to ensure reliability across its distributed components.

### 13.1 Unit Testing

- **Agents**: Every agent in the registry is tested for input/output schema adherence.
- **Engines**: The Goal Engine, Planner, and Reasoning Core are tested for DAG validity, simulation behavior, and confidence scoring.
- **Utils**: Security filters and sanitizers are tested against known injection patterns.

### 13.2 Integration Testing

- **End-to-End Missions**: Simulated user requests are routed through the entire pipeline to verify completion.
- **Memory Consistency**: Tests verify that writes to Redis are correctly synchronized to Postgres, Neo4j, and FAISS.
- **DCN Gossip**: Pulses are simulated to ensure nodes correctly process swarm telemetry.
- **Replay & Idempotency**: Tests verify duplicate mission suppression and deterministic replay payload capture.
- **RBAC Negatives**: Protected routes are tested for no token, expired token, and wrong-role token handling.
- **Live Ollama Smoke**: Optional non-mocked tests validate real local inference when `RUN_LIVE_OLLAMA_TESTS=1`.

### 13.3 Chaos & Reliability

- **Chaos Monkey**: Intentional injection of Redis outages, Neo4j slowdowns, and agent timeouts to test recovery logic.
- **VRAM Stress**: Simulation of high GPU load to verify adaptive concurrency throttling.

```bash
# Run all tests
python -m pytest tests/

# Run chaos tests
ENABLE_CHAOS=true python -m pytest tests/chaos/

# Run live Ollama smoke tests
RUN_LIVE_OLLAMA_TESTS=1 python -m pytest tests/integration/test_live_ollama_smoke.py

# Run shutdown-drain regression
python -m pytest backend/tests/test_runtime_shutdown.py
```

## 14. Contribution & Development

We welcome contributions to the Sovereign OS. Please follow these guidelines:

### Development Workflow

1. **Branching**: Create a feature branch from `main`.
2. **Coding Standards**: Adhere to PEP 8 for Python and Clean Architecture patterns.
3. **Documentation**: Update the `SYSTEM_MANIFEST.md` if adding new modules or agents.
4. **Testing**: Ensure all tests pass before submitting a PR.

### Adding a New Agent

To add a new agent to the swarm:

1. Create a new class in `backend/agents/` inheriting from `SovereignAgent`.
2. Define the input/output schemas using Pydantic.
3. Register the agent in `backend/agents/registry.py`.
4. Add a default TEC heuristic in `backend/core/planner.py`.

## 15. Limitations & Roadmap

### Current Limitations

- **Scaling**: Vertical scaling is optimized; horizontal DCN peering is currently in beta and limited to 5 concurrent nodes.
- **Hardware**: Strongly dependent on `nvidia-smi` for backpressure logic; non-NVIDIA environments will default to linear execution.
- **Connectivity**: Cloud fallback requires active internet; local mode disables high-cost reasoning but ensures 100% data sovereignty.
- **Latency**: High-complexity DAGs (depth > 6) may incur significant reasoning overhead due to recursive validation steps.
- **Runtime Coupling**: Some legacy runtime paths still assume Redis-first startup, which can complicate isolated local module boot.

### Roadmap (v14.x - v15.0)

- **Phase 2: Swarm Intelligence**: Hardening of multi-agent consensus protocols and shadow-critic calibration.
- **Phase 3: DCN Peering**: Official release of the peer-to-peer cognitive network for global mission distribution.
- **Phase 4: Deterministic Replay**: Full UI integration for step-by-step mission debugging and forensic analysis.
- **Phase 5: Evolutionary Learning**: Promote strategy-led mission templates into deeper adaptive planner behavior.
- **Phase 6: Multi-Modal Context**: Native support for video and spatial audio context in the long-term memory graph.

---

## 16. System Manifest

For a complete, auto-generated list of all internal modules, services, and agent registries, see the [SYSTEM_MANIFEST.md](./SYSTEM_MANIFEST.md).

---

*© 2026 Sovereign Engineering. Built for predictability, observability, and absolute autonomy.*

---

## 17. Configuration Reference

The following environment variables configure the Sovereign OS. Defaults are safe for local development but should be overridden in production.

| Variable                 | Default                           | Description                                                                 |
| :---                     | :---                              | :---                                                                        |
| REDIS_URL                | redis://localhost:6379/0          | Runtime state and rate limiter store                                        |
| POSTGRES_URL             | postgresql+asyncpg://…            | SQL fabric for immutable history and profiles                               |
| NEO4J_URI                | bolt://localhost:7687             | Relational knowledge graph                                                  |
| VECTOR_BACKEND           | faiss                             | Semantic store implementation (faiss, pinecone, chroma)                     |
| OLLAMA_HOST              | http://localhost:11434            | Local inference endpoint                                                    |
| ENABLE_CHAOS             | false                             | Enables chaos injection during tests                                        |
| TRACE_SAMPLING_RATE      | 1.0                               | Portion of requests to instrument (0.0 – 1.0)                               |
| MAX_PARALLEL_WAVES       | 2                                 | Default parallel wave budget                                                |
| VRAM_PRESSURE_KEY        | vram:pressure                     | Redis key used to signal backpressure                                      |
| AUDIT_CHAIN_SECRET       | none                              | HMAC seed for immutable audit chain. Must not use placeholder values.       |
| ENCRYPTION_KEY           | none                              | KMS envelope key alias. Must not use placeholder values.                    |
| JWT_SECRET               | none                              | JWT signing key. Startup checks fail production readiness on insecure value. |
| INTERNAL_SERVICE_KEY     | none                              | Service-to-service auth secret. Must be unique outside local development.   |
| LOG_LEVEL                | INFO                              | Logging level (DEBUG, INFO, WARN, ERROR)                                    |
| MODEL_ROUTER_PROVIDER    | local                             | Model router primary provider                                               |
| CLOUD_FALLBACK_PROVIDER  | none                              | Backup provider (together, openai, groq)                                    |
| SSE_BURST_SIZE           | 32                                | SSE message batching factor                                                 |
| SSE_MAX_LATENCY_MS       | 250                               | SSE latency bound for interactive sessions                                  |

---

## 18. Deployment Guides

### 18.1 Docker Compose (Local)

```yaml
version: "3.9"
services:
  redis:
    image: redis:7
    ports: ["6379:6379"]
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: levi
      POSTGRES_USER: levi
      POSTGRES_PASSWORD: levi
    ports: ["5432:5432"]
  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/levi
    ports: ["7474:7474", "7687:7687"]
  backend:
    build: .
    env_file: .env
    depends_on: [redis, postgres, neo4j]
    ports: ["8000:8000"]
```

### 18.2 Kubernetes (Preview)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: levi-backend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: levi-backend
  template:
    metadata:
      labels:
        app: levi-backend
    spec:
      containers:
        - name: backend
          image: ghcr.io/sovereign-ai/levi:14
          envFrom:
            - secretRef:
                name: levi-secrets
          ports:
            - containerPort: 8000
          readinessProbe:
            httpGet:
              path: /healthz
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
```

---

## 19. End‑to‑End Walkthroughs

### 19.1 Chat Mission (Fast Path)

```bash
curl -X POST http://localhost:8000/api/v1/orchestrator/mission \
  -H "Content-Type: application/json" \
  -d '{"message":"Explain self-attention in 2 bullet points","session_id":"demo"}'
```

Expected:
- Orchestrator routes to FAST mode.
- Brain produces a single-node DAG with chat_agent.
- Result cached in Redis; state machine transitions to COMPLETE.

### 19.2 Code Mission (Sandboxed)

```bash
curl -X POST http://localhost:8000/api/v1/orchestrator/mission \
  -H "Content-Type: application/json" \
  -d '{"message":"Write a Python function to deduplicate a list","mode":"SECURE"}'
```

Expected:
- Planner emits nodes: code_agent → python_repl_agent (verify).
- Executor enforces sandbox and memory_scope.
- Critic disabled under backpressure; capped retries.

### 19.3 Research Mission (Retrieval)

```bash
curl -X POST http://localhost:8000/api/v1/orchestrator/mission \
  -H "Content-Type: application/json" \
  -d '{"message":"Summarize recent LLM evals on math reasoning","mode":"RESEARCH"}'
```

Expected:
- DAG: search_agent → browser_agent (optional) → chat_agent synth.
- Memory extractions populate vector store and Neo4j.
- Trace and per-node latencies visible via health endpoints.

---

## 20. Extension Points

### 20.1 Adding Tools
- Implement tool call in `backend/core/tool_registry.py`.
- Define a `ToolResult` contract (success, message, error, data).
- Reference tool name in the node’s `TaskExecutionContract.allowed_tools`.

### 20.2 New Agents
- Subclass SovereignAgent and register in `backend/agents/registry.py`.
- Provide pydantic input/output schemas.
- Add default TEC heuristics via planner hooks.

### 20.3 Memory Pipelines
- Implement derived sinks behind the `MemoryConsistencyManager` fan‑out.
- Honor versioning fields and dedup markers.

---

## 21. Trace & Telemetry Taxonomy

### 21.1 Trace IDs
- `TRACE_ID`: mission root identifier.
- Scope: Gateway → Orchestrator → Planner → Executor → Agent → Tool → Memory.

### 21.2 Timeline Steps (Common)
- routing_decision
- scheduled
- executed
- node_start
- node_complete
- validating
- persisted
- failed

### 21.3 Metrics Keys (Redis)
- `metrics:latency_ms`: rolling list of mission latencies.
- `metrics:neo4j_latency_ms`, `metrics:redis_latency_ms`: service latencies.
- `stats:failure_rate`: recent error ratio.
- `vram:pressure`: backpressure boolean.

---

## 22. Memory Consistency Rules

### 22.1 Event Schema

```json
{
  "id": "mem_1712345678",
  "version": 3,
  "origin_task": "t_synth",
  "derived_from": ["t_search"],
  "timestamp": 1712345678.123
}
```

### 22.2 Write Authority
- Redis is the only runtime write authority.
- Postgres, Neo4j, and Vector stores are derived projections.

### 22.3 Deduplication
- Content‑hash keys prevent repeated embeddings.
- TTL markers schedule pruning of outdated items.

---

## 23. Security Hardening Checklist

- Enable RBAC and JWTs on all API routes.
- Enforce sandbox for code execution nodes.
- Use KMS‑managed envelope keys for secrets.
- Activate prompt shield on the gateway.
- Block outbound egress except for whitelisted domains.
- Enforce strict CSP, HSTS, and X-Frame-Options outbound headers globally.
- Activate Redis sliding-window tiered rate limiting to prevent API abuse.
- Rotate `AUDIT_CHAIN_SECRET` with proper key management.

---

## 24. Performance Tuning

### 24.1 Live Chaos & Load

```bash
python scripts/chaos/run_live_chaos.py --service redis --outage-seconds 10
k6 run tests/load/missions_k6.js
```

- Increase `MAX_PARALLEL_WAVES` only with sufficient VRAM headroom.
- Raise `TRACE_SAMPLING_RATE` selectively for problematic routes.
- Use local embeddings for high‑traffic topics to reduce latency.
- Cache stable mission outcomes via exact/semantic layers.

---

## 25. Troubleshooting & FAQ

- Symptoms: “Could not establish a connection to backend (MySQL Shell)”
  - Cause: legacy monitors expecting MySQL; LEVI uses Postgres.
  - Resolution: remove outdated MySQL checks; validate `POSTGRES_URL`.

- Symptoms: High latencies during research missions
  - Cause: excessive DAG depth or slow external sites.
  - Resolution: reduce `max_dag_depth`, enable browser_agent only when needed.

- Symptoms: Critic loops cause delays
  - Cause: critic enabled under resource pressure.
  - Resolution: backpressure disables critic; confirm `vram:pressure` key.

---

## 26. Glossary

- **Sovereign OS**: An AI operating system emphasizing control and predictability.
- **TEC**: Task Execution Contract; per‑node guardrails defining retries, timeout, and allowed tools.
- **Wave Scheduling**: Parallel groups of DAG nodes executed once dependencies are satisfied.
- **MCM**: Memory Consistency Manager; orchestrates versioned runtime writes and fan‑out.
- **DCN**: Distributed Cognitive Network; multi‑node scale‑out architecture (beta).

---

## 27. Change Log (v14 Highlights)

- Added Central Execution State Machine with explicit transitions.
- Introduced TECs and global execution budgets.
- Implemented Memory Consistency Manager with versioning and dedup.
- Added deterministic Replay Engine harness for post‑mortem analysis.
- Introduced adaptive scheduler with VRAM backpressure signals.
- Hardened agents to be dumb executors under a centralized orchestrator.

---

## 28. SLOs & Error Budgets

- Availability SLO: 99.5% for Gateway and Orchestrator.
- Latency SLO: P95 end‑to‑end mission < 3.0s for FAST mode.
- Error Budget Policy: auto‑throttle concurrency and disable critic when burn rate exceeds thresholds.

---

## 29. Operational Runbooks

### 29.1 Cache Warmup
- Preload embeddings for top intents.
- Seed Redis with common exact-match responses.

### 29.2 Backpressure Toggle
- Set `vram:pressure` → `true` in Redis to force linear execution.
- Verify via `/api/v1/orchestrator/health/graph`.

### 29.3 Deterministic Replay
- Fetch `TRACE_ID` from orchestrator response.
- Run the replay harness to reconstruct node timelines.

---

## 30. Extension Examples

### 30.1 Example: Custom Tool Contract

```json
{
  "name": "web_fetch",
  "version": "1.0",
  "input": { "url": "string" },
  "output": { "content": "string", "status": "number" },
  "errors": [ "timeout", "dns_error" ]
}
```

### 30.2 Example: TEC for Browser Agent

```json
{
  "task_id": "t_browse",
  "timeout_ms": 60000,
  "max_retries": 1,
  "allowed_tools": ["web_fetch", "sanitize_html"],
  "memory_scope": "session"
}
```

---

## 31. License & Governance

- Source usage is bound by the Sovereign Engineering governance policy.
- Contributions require CLA acceptance and pass the security review.

---

## 32. v14.0 Production Release & Graduation State

The v14.0 release represents the final transition from a monolithic architecture to a modular multi-agent orchestration system (Sovereign OS).

| Category | Status | Detail |
| :--- | :--- | :--- |
| Orchestration | ✅ Active | Strategy Selection, Tool Discovery, and Task Arbitration |
| Stability | ✅ Hardened | Continuous Evaluation (CE), Experience Replay, Shadow Deployment |
| Security/GDPR | ✅ Compliant | PII Masking, RTBF (Manual Wipe), SSRF bounds, strict CSP/HSTS |
| Scalability | ✅ Resilient | Local + Cloud Burst (Groq/OAI), Semaphore Gating, Tiered Rate Limits |
| Observability | ✅ Deep Trace | OpenTelemetry/Jaeger + Automated Root Cause Analysis |

### System Performance (RC1)
- **Concurrent Sessions**: 4 (Gated) / 1000+ (Burst)
- **p95 Latency**: ~12s (Cloud Accelerated)
- **Overhead**: Adaptive (5-50ms)
- **Recovery RTO**: < 300s (Automated)

### Operational Commands
- **Check Burst Status**: `docker logs levi-backend | grep -i "burst"`
- **Security Stress Test**: `python -m backend.scripts.red_team`
- **Data Governance**: `POST /api/v1/privacy/rtbf?user_id={uid}`
- **System Audit**: `GET /api/v1/trainer/ce-report`

---

## 33. Complete System Manifest (Current Runtime Surfaces)

**Designated Workflow:** `Gateway -> Orchestrator -> Goal -> Planner -> Reasoning -> Executor -> Agents -> Memory -> Response`

### Core Runtime Services
- `backend/api/main.py`: Primary HTTP entrypoint, middleware, metrics, router registration.
- `backend/main.py`: Backward-compatible import surface.
- `backend/utils/runtime_tasks.py`: Tracks background tasks and drains in-flight work on shutdown.
- `backend/core/orchestrator.py`: Mission lifecycle coordination.
- `backend/core/goal_engine.py`: Converts user input into structured objectives.
- `backend/core/planner.py`: Builds DAG plans and supports compatibility helpers.
- `backend/core/brain.py`: Reasoning pass, critique, refinement, policy bridging.
- `backend/core/executor/__init__.py`: Runs DAG waves, retries, backpressure.
- `backend/core/execution_guardrails.py`: Sandbox and threshold enforcements.
- `backend/core/workflow_contract.py`: Validates and reports designated workflow integrity.

### Persistence and State
- **Redis** (`backend/db/redis.py`): Runtime state, queues, rate limiting.
- **Postgres** (`backend/db/postgres_db.py`): Resonance verification and persistent data.
- **Alembic** (`backend/alembic/`): Versioned schema migrations.
- **Neo4j** (`backend/db/neo4j_client.py`): Relational memory and graph surfaces.
- **Vector Store** (`backend/db/vector_store.py`): Semantic retrieval.
- **Task Graph** (`backend/core/task_graph.py`): DAG structure, validation, and depth reporting.

### Runtime Guarantees
- Stricter DAG validation & bounded retries (with backoff behavior).
- Sandbox and tool-boundary enforcement.
- Mission token-budget & tool-call-budget enforcement.
- Multi-signal backpressure using VRAM, CPU, RAM, and queue depth.
- Startup readiness contract reporting.
- Active Alembic migration path on backend startup.
- Tracked shutdown draining for background mission tasks.
