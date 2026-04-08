# LEVI-AI Sovereign OS (v14.0.0-Autonomous-SOVEREIGN)

LEVI-AI is a high-fidelity, predictable, and failure-isolated distributed AI operating system. It transforms complex autonomous reasoning into a controlled cognitive pipeline, enabling deterministic execution of mission-critical tasks through a Sovereign Task Graph (DAG).

---

## 1. Overview

LEVI-AI is designed as a **Cognitive Operating System** that manages the lifecycle of AI missions—from intent classification and goal generation to parallelized agent execution and multi-tier memory synchronization. It addresses the inherent unpredictability of large language models by enforcing strict execution contracts, centralized state tracking, and a unified memory consistency layer.

### Core Philosophy

- **Local-First**: Prioritizes local inference (Ollama) for privacy and zero-cost logic.
- **Deterministic**: Every action is planned in a DAG before execution begins.
- **Sovereign**: Absolute control over data, memory, and model routing.
- **Distributed**: Built for high-availability across multiple cognitive nodes (DCN).

---

## 2. System Capabilities

### 2.1 Orchestration & Planning

- **Goal Engine**: Translates raw user input into structured, multi-step mission objectives.
- **DAG Planner**: Generates an optimized Task Graph with explicit dependencies and contracts.
- **Central Execution State Machine**: Authoritative tracking from `CREATED` to `COMPLETE`.

### 2.2 Memory System

- **Episodic**: 7-day rolling window in Redis for rapid context retrieval.
- **Factual**: Immutable Interaction Log in PostgreSQL for long-term persistence.
- **Relational**: Neo4j knowledge graph for mapping entities and semantic relationships.
- **Semantic**: Vector DB (FAISS/HNSW) for RAG and similarity-based discovery.

### 2.3 Inference Layer

- **Local (Ollama)**: Primary execution path for sensitive or low-complexity tasks.
- **Cloud Fallback**: Adaptive routing to Together/Groq/OpenAI when local resources are under pressure.
- **VRAM Backpressure**: Automatically throttles concurrency based on live GPU telemetry.

### 2.4 Security & Governance

- **Worker Isolation**: Scoped memory and tool sandboxing for every task.
- **RBAC**: Fine-grained role-based access control for tenants and resources.
- **Audit Ledger**: Immutable, monthly-partitioned log with HMAC-SHA256 integrity chains.

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
    Planner --> Executor[Graph Executor]
    Executor --> Wave[Wave Scheduler]
    Wave --> Agents[Specialized Agents]
    Agents --> Tools[Isolated Tools]
    Tools --> Memory[Memory Sync]
    Memory --> Response[Final Response]
```

### 3.2 Memory Flow (Single Write Authority)

```mermaid
graph LR
    Runtime[Runtime State] --> Redis[Redis (Source of Truth)]
    Redis --> MCM[Memory Consistency Manager]
    MCM --> Postgres[PostgreSQL (Immutable History)]
    MCM --> Neo4j[Neo4j (Relational Knowledge)]
    MCM --> Vector[Vector DB (Semantic Memory)]
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

---

## 4. Core Components (System Blueprint)

| Module | Purpose | Input | Output | Dependencies |
| :--- | :--- | :--- | :--- | :--- |
| **Gateway** | API Entry & Security | HTTP Request | Sanitized Payload | RBAC, Shield |
| **Orchestrator** | Mission Lifecycle | User Intent | Final Response | Goal Engine, Planner |
| **Goal Engine** | Objective Generation | Perception | Mission Goals | Memory Manager |
| **Planner** | DAG Generation | Goal | Task Graph (DAG) | Brain Policy, LLM |
| **Executor** | Parallel Wave Execution | DAG | Node Results | Agents, Redis |
| **Memory Manager** | Tiered Sync & Retrieval | Events | Merged Context | MCM, Neo4j, FAISS |
| **MCM** | Memory Consistency | Memory Events | Versioned State | Redis, Pipeline |

---

## 5. Execution Model

### 5.1 Task Execution Contract (TEC)

Every mission is decomposed into a directed acyclic graph (DAG) of task nodes. Each node defines a **TEC**:

- **`timeout_ms`**: Explicit execution deadline.
- **`max_retries`**: Capped retry attempts (default: 2).
- **`allowed_tools`**: Restricted tool access per agent.
- **`memory_scope`**: Scoped memory access (`session`, `mission`, `global`).

### 5.2 Wave Scheduling & Backpressure

The Executor processes the DAG in parallel "waves." A wave consists of all nodes whose dependencies are satisfied.

- **Adaptive Concurrency**: Parallelism is dynamically throttled (e.g., down to 1 wave) based on system resources like VRAM pressure.
- **Budgeting**: Enforces mission-wide `token_limit` and `tool_call_limit` to prevent resource exhaustion.

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
AUDIT_CHAIN_SECRET=genesis_key
ENCRYPTION_KEY=kms_master_key
```

### Installation Steps

1. **Infrastructure**: Start services via Docker Compose.

   ```bash
   docker-compose up -d redis postgres neo4j faiss
   ```

2. **Backend**: Install dependencies and initialize DB.

   ```bash
   pip install -r requirements.txt
   python backend/db/main.py init
   ```

3. **Frontend**: Install dependencies and build.

   ```bash
   cd frontend && npm install && npm run build
   ```

4. **Launch**: Start the Sovereign Gateway.

   ```bash
   npm run dev
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
| **Memory Desync** | MCM Version Mismatch | Force Redis re-sync | Log Audit |
| **VRAM Overload** | VRAM Monitor Pulse | Disable Critic loops | Linear execution |
| **Cloud Fallback** | Model Router Pulse | Switch to local Ollama | Service Degraded |

### Compensation Engine

If a critical task node fails after all retries, the **Compensation Engine** executes rollback actions defined in the TEC (e.g., reverting database changes or emitting a failure pulse to the user).

---

## 12. Observability & Telemetry

### 12.1 Global Tracing

Every request carries a `TRACE_ID` injected at the Gateway. Spans are recorded for:

- **Planning**: Intent, Goal, DAG Generation.
- **Execution**: Node start/stop, Latency, Tool output.
- **Persistence**: MCM sync status, DB commit latency.

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
- **Engines**: The Goal Engine and Planner are tested for DAG validity and cycle detection.
- **Utils**: Security filters and sanitizers are tested against known injection patterns.

### 13.2 Integration Testing

- **End-to-End Missions**: Simulated user requests are routed through the entire pipeline to verify completion.
- **Memory Consistency**: Tests verify that writes to Redis are correctly synchronized to Postgres, Neo4j, and FAISS.
- **DCN Gossip**: Pulses are simulated to ensure nodes correctly process swarm telemetry.

### 13.3 Chaos & Reliability

- **Chaos Monkey**: Intentional injection of Redis outages, Neo4j slowdowns, and agent timeouts to test recovery logic.
- **VRAM Stress**: Simulation of high GPU load to verify adaptive concurrency throttling.

```bash
# Run all tests
python -m pytest tests/

# Run chaos tests
ENABLE_CHAOS=true python -m pytest tests/chaos/
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

### Roadmap (v14.x - v15.0)

- **Phase 2: Swarm Intelligence**: Hardening of multi-agent consensus protocols and shadow-critic calibration.
- **Phase 3: DCN Peering**: Official release of the peer-to-peer cognitive network for global mission distribution.
- **Phase 4: Deterministic Replay**: Full UI integration for step-by-step mission debugging and forensic analysis.
- **Phase 5: Evolutionary Learning**: Autonomous LoRA fine-tuning based on high-fidelity interaction patterns.
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
| AUDIT_CHAIN_SECRET       | change-me                         | HMAC seed for immutable audit chain                                         |
| ENCRYPTION_KEY           | kms_master_key                    | KMS envelope key alias                                                      |
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
- Rotate `AUDIT_CHAIN_SECRET` with proper key management.

---

## 24. Performance Tuning

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
