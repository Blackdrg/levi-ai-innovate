LEVI-AI is a high-fidelity, predictable, and failure-isolated distributed AI operating system. It transforms complex autonomous reasoning into a controlled cognitive pipeline, enabling deterministic execution of mission-critical tasks through a Sovereign Task Graph (DAG).

## 🚧 Reality Check

LEVI-AI v14.2 is currently:
- **Architecture**: 90% complete ✅
- **Implementation**: ~35% ⚠️
- **Production Ready**: ❌ No

This repository represents a high-fidelity system design that is under active development toward full production deployment.

## 🟢 Current System Status (Truth Layer)

| Component        | Status        |
|-----------------|--------------|
| API Gateway      | ❌ Architecture Only |
| Orchestrator     | ⚠️ Partial (Core logic only) |
| Memory System    | ❌ Development-Lite |
| Agents           | ❌ Stubs / Minimal implementation |
| Voice Stack      | ❌ Research Phase |
| Infrastructure   | ⚠️ Partial (Terraform scripts) |

---

## 1. Quick Start (Development Node)

### 1.1 Prerequisites
- **Hardware**: NVIDIA GPU (8GB+ VRAM recommended).
- **Environment**: Linux/WSL2 or Docker.
- **Tools**: Docker, Python 3.10+, Node.js 18+.

### 1.2 Command Sequence
```bash
# 1. Clone & Init
git clone https://github.com/Blackdrg/levi-ai-innovate && cd levi-ai-innovate

# 2. Start Dependent Services
docker-compose up -d redis postgres neo4j

# 3. Setup Backend
pip install -r requirements.txt
python -m backend.main

# 4. Setup Frontend
cd frontend && npm install && npm run dev
```

## 2. Environment Configuration
Create a `.env` file in the root with the following variables:
```env
GCP_PROJECT_ID=your-project
REDIS_HOST=localhost
POSTGRES_USER=levi
NEO4J_URI=bolt://localhost:7687
OLLAMA_BASE_URL=http://localhost:11434
TAVILY_API_KEY=your-key
```

---


---

## 2. System Capabilities

### 2.1 Orchestration & Planning (v14.1 Unified Core)

- **DAG Planner**: Translates user intent into structured mission goals and an optimized Task Graph with explicit dependencies and contracts.
- **Sovereign Orchestrator**: The central "State Authority" (SM) tracking mission lifecycle from `CREATED` to `COMPLETE`.
- **Reasoning Core**: Validates DAG logic, simulates outcomes before execution, scores plan confidence, and can force a second planning pass.
- **Mission Idempotency**: Duplicate mission protection prevents equivalent in-flight requests from executing twice.

### 2.2 Memory System

- **Episodic**: 7-day rolling window in Redis for rapid context retrieval.
- **Factual**: Immutable Interaction Log in PostgreSQL for long-term persistence.
- **Relational**: Neo4j knowledge graph for mapping entities and semantic relationships.
- **Semantic**: Vector DB (FAISS/HNSW) for RAG and similarity-based discovery.
- **Decision-Aware Recall**: A lightweight strategy ledger captures which graph shapes worked best for each intent.

- **Multi-Signal Backpressure**: Automatically throttles concurrency based on VRAM, CPU, RAM, and executor queue depth.

### 2.4 Frontend Architecture (Cybernetic UI)

The LEVI-AI OS interface is a hyper-modern, high-performance Frontend layer built for absolute mission visibility.

- **Tech Stack**: React 18, Vite 6, Tailwind CSS, Framer Motion (animations), ReactFlow (mission execution graphs), Zustand (state).
- **Mission Dashboard**: A high-fidelity, real-time interface consuming SSE streams for mission tracking, Perception->Goal->Execution trace visibility.
- **Mission Auditor**: A specialized DCN Fidelity registry that scores mission quality and flags autonomous deviations in real-time.
- **Sovereign Console**: The primary command center featuring multi-tier (L1-L4) mission launching and neural input orchestration.
- **Observability Interface**: Real-time hardware utilization (VRAM/CPU) and cognitive telemetry monitors.

### 2.5 Security & Governance

- **Worker Isolation**: Scoped memory and tool sandboxing for every task.
- **RBAC**: Fine-grained role-based access control for tenants and resources.
- **Audit Ledger**: Immutable, monthly-partitioned log with HMAC-SHA256 integrity chains.
- **Default Secret Guardrails**: Startup checks and pre-commit hooks flag insecure placeholder secrets.
- **Sovereign Voice Stack**: Local, low-latency Speech-to-Text (STT) and Text-to-Speech (TTS) integration for voice-first cognitive missions.

---

---

## 3. Backend Technical Architecture

The LEVI-AI backend is a high-performance cognitive gateway built on FastAPI. It orchestrates the mission lifecycle from intent classification to distributed host-agent execution.

### ⚙️ Core Engines
- **FastAPI Gateway**: Entry point for all mobile, voice, and web clients.
- **Orchestrator Service**: The "State Authority" tracking mission progress.
- **Planner Service**: Decomposes user intent into a Sovereign Task Graph (DAG).
- **Executor Service**: Parallelizes agent waves across the DCN.
- **Memory Service**: Synchronizes the 4-tier cognitive memory layers.

### 🛡️ Middleware Stack
1. **PrometheusMiddleware**: Tracks latency and CU costs at the edge.
2. **RateLimitMiddleware**: Tiered sliding window enforcement (Redis-backed).
3. **SSRFMiddleware**: Egress protection via precision CIDR blocking and pre-request DNS resolution.
4. **SovereignShieldMiddleware**: RBAC and asymmetric JWT verification.

---

## 4. Frontend: Cybernetic Dashboard

The LEVI-AI frontend is a hyper-modern React 18 application designed for real-time mission observability. It utilizes a centralized Zustand store for managing cognitive telemetry and mission states.

### 🎨 Data Flow
`User Input → UI Component → API Client → Backend → SSE Updates → UI Refresh`

### 📂 Component Hierarchy
- **`App`**: Root Entry & Auth Router.
- **`Layout`**: Navigation & DCN Health Sidebar.
- **`Dashboard`**: High-level mission grid and hardware monitors.
- **`MissionStudio`**: DAG generation and configuration center.
- **`GraphInterface`**: ReactFlow-based execution visualizer.
- **`TelemetryMonitor`**: Real-time Prometheus/SSE data feeds.

### 🛡️ Auth Flow & State
- **Auth**: `login.html` → POST `/api/v1/auth/session` → Token stored in `localStorage` → Axios Interceptor injects `Authorization` header.
- **State**: `useChatStore` manages the mission history, active DAG, and real-time pulse.

---

LEVI-AI is deployed on a highly available, managed Google Cloud platform. This infrastructure ensures the system's "Sovereign" state across distributed nodes with enterprise-grade reliability.

### 2.1 Managed Services Stack
- **Compute**: [Cloud Run](https://cloud.google.com/run) serves the Sovereign Gateway and background executors, enabling rapid scaling and zero-infrastructure management.
- **Database**: [Cloud SQL for PostgreSQL 15](https://cloud.google.com/sql) acts as the source of truth for all factual memory and mission audits.
- **Cache & State**: [Memorystore for Redis 6.x](https://cloud.google.com/memorystore) handles the Tier-1 Episodic memory and mission state machine.
- **Queue**: [Cloud Tasks](https://cloud.google.com/tasks) manages high-volume mission wave scheduling and priority queuing.
- **Storage**: [Google Cloud Storage](https://cloud.google.com/storage) hosts mission artifacts, media, and long-term backups.
- **Secrets**: [Secret Manager](https://cloud.google.com/secret-manager) ensures all cryptographic keys and API tokens are never exposed in the runtime environment.

### 2.2 Security & Networking
- **VPC Connector**: Enables secure, internal-only communication between Cloud Run and managed databases.
- **IAM Hardening**: Every service runs under a specialized Service Account with **Least Privilege** access to project resources.
- **Audit Logging**: All infrastructure changes and mission-critical API calls are recorded in Cloud Logging with immutable integrity.

---

## 3. Frontend Technical Architecture

The LEVI-AI Frontend is a highly optimized, reactive interface designed for real-time mission observability and control.

### 3.1 Tech Stack & Core Libraries
- **Framework**: [React 18](https://reactjs.org/) + [Vite 6](https://vitejs.dev/) for ultra-fast HMR and build performance.
- **State Management**: [Zustand](https://github.com/pmndrs/zustand) for lightweight, predictable global state across missions and telemetry.
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) + [PostCSS](https://postcss.org/) for utility-first, performant UI components.
- **Animations**: [Framer Motion](https://www.framer.com/motion/) for smooth transitions and cognitive state visualization.
- **Visualization**: [ReactFlow](https://reactflow.dev/) for interactive Sovereign Task Graph (DAG) rendering.
- **Networking**: [Axios](https://axios-http.com/) for API communication and **Server-Sent Events (SSE)** for real-time mission telemetry.

### 3.2 Directory Structure (`frontend/src/`)
```text
├── components/     # Atomic UI components (Buttons, Modals, Cards)
├── features/       # Feature-specific logic (Chat, Studio, Monitor)
├── hooks/          # Custom React hooks (useAuth, useMission, useSSE)
├── lib/            # Third-party library configurations
├── pages/          # Top-level page components (Admin, Marketplace, Gallery)
├── services/       # API service wrappers (InternalServiceClient)
├── store/          # Zustand store definitions (authStore, missionStore)
├── styles/         # Global CSS and Tailwind directives
└── utils/          # Pure helper functions and formatters
```

### 3.3 ReactFlow Integration
The execution graph is rendered dynamically from the `frozen_dag` stored in the mission payload. Nodes are colored based on their lifecycle status (`CREATED`, `RUNNING`, `COMPLETE`, `FAILED`), providing immediate visual feedback of the "cognitive wave" execution.

---

## 5. Database & Cognitive Persistence

LEVI-AI utilizes a multi-engine persistence strategy to balance relational integrity with semantic discovery and episodic speed.

### 🗄️ Relational Schema (PostgreSQL 15)
The PostgreSQL instance acts as the absolute source of truth for missions, identity, and compliance.

### 🧠 Cognitive Persistence Layers
- **Tier 1 (Episodic)**: [Redis] 7-day rolling interaction buffer.
- **Tier 2 (Factual)**: [PostgreSQL] Immutable mission history.
- **Tier 3 (Relational)**: [Neo4j] Knowledge graph of semantic triples (User->Knows->Entity).
- **Tier 4 (Identity)**: [FAISS/Vector Store] Distributed vector memory for similarity RAG.

### 🔄 Lifecycle & Migrations
- **Alembic**: Relational migrations are managed via Alembic (`alembic upgrade head`).
- **Data Lifecycle**: Audit logs are partitioned monthly. GDPR deletions trigger a "Multi-Tier Sovereign Wipe" that physically erases data across all 4 tiers.

---

## 6. Infrastructure: Global Sovereign Network

LEVI-AI utilizes a globally diversified, serverless-first infrastructure on GCP. The design prioritizes 100% data sovereignty and high availability.

### 🏗️ Managed Services Stack
- **[Cloud Run]**: Primary backend gateway and background mission executors.
- **[Cloud SQL (PG 15)]**: Factual truth layer and user identity store.
- **[Memorystore (Redis 6.x)]**: Episodic memory and real-time mission state.
- **[Cloud Tasks]**: Wave scheduling and background task orchestration.
- **[Cloud Armor]**: WAF protection against SQLi, DDoS, and SSRF.

---

## 7. Test Suite & Verification

LEVI-AI utilizes a multi-tier testing strategy to ensure 100% system integrity and production stability.

### 🧪 Test Categories
- **Unit Tests**: Standard logic verification for core engines and utilities.
- **Integration Tests**: End-to-end mission flows from API Gateway to Agent Swarm.
- **Chaos Tests**: Verifies DCN resilience during node failure and network partitions.
- **Load Tests**: Validates system performance under extreme mission volume.
- **graduation_audit**: High-fidelity graduation suite for production-readiness sign-off.

### 🚀 Execution Commands
```bash
pytest tests/                    # Full Test Suite
python tests/v14_production_audit.py # Production Readiness Audit
```

---

## 5. Architecture Overview

### 3.1 Request Lifecycle Flow

```mermaid
graph TD
    User[User Request] --> Frontend[React UI / Zustand]
    VoiceInput[Voice Input] --> STT[Sovereign STT - Whisper]
    STT --> Gateway[FastAPI Gateway]
    Frontend --> Gateway
    Gateway --> FastPath{Fast-Path / Cache?}
    FastPath -- Hit --> Response[Response]
    FastPath -- Miss --> SecurityGate{Security Anomaly Gate}
    SecurityGate -- Threat --> Block[Block & Alert]
    SecurityGate -- Clean --> Guardrails[PII / NER Guardrails]
    Guardrails --> Auth[RS256 JWT Identity]
    Auth --> Orchestrator[Orchestrator]
    Orchestrator --> Evolution{Evolutionary Rule?}
    Evolution -- Match --> FastPath
    Evolution -- Drift --> Planner[DAG Planner]
    Planner --> Reasoning[Reasoning Core]
    Reasoning --> Executor[Graph Executor]
    Executor --> Wave[Wave Scheduler]
    Wave --> Agents[Specialized Agents]
    Agents --> Tools[Isolated Tools]
    Tools --> Memory[Memory Sync]
    Memory --> Response[Final Response]
    Response --> TTS[Sovereign TTS - Coqui]
    TTS --> VoiceOutput[Audio Output]
    Response -.-> Learning[Learning Pipeline]
    Learning -.-> Evolution
```

### 3.2 Memory Flow (Single Write Authority)

```mermaid
graph LR;
    Runtime["Runtime State"] --> Stream["Redis Stream - Event Log (Source of Truth)"];
    Stream --> MCM["Memory Consistency Manager"];
    MCM --> Redis["Redis KV - Episodic Context"];
    MCM --> Postgres["PostgreSQL - Immutable History"];
    MCM --> Neo4j["Neo4j - Relational Knowledge"];
    MCM --> Vector["Vector DB - Semantic Memory"];
```

### 3.3 Agent System Hierarchy

```mermaid
graph TD
    Orchestrator[Sovereign Orchestrator] --> Intent[Intent Classifier]
    Orchestrator --> Planner[DAG Planner]
    Planner --> Policy[Static Policy Rules]
    Planner --> Swarm[Agent Swarm]
    Swarm --> Logic[Logic: Code, Task, Consensus]
    Swarm --> Data[Data: Search, Research, Document]
    Swarm --> Creative[Creative: Image, Video]
```


### 3.4 Complete System Architecture

```mermaid
graph TD;

  %% === Ingress & Infrastructure ===
  subgraph Frontend UI
    UI["React 18 + Vite"]
    STOR["Zustand State Store"]
    FLOW["ReactFlow Graph Rendering"]
    UI <--> STOR
    UI --> FLOW
  end

  subgraph Sovereign Voice Stack
    STT["Whisper STT (Local)"]
    TTS["Coqui TTS (Local)"]
    VP["Voice Processor"]
    STT --> VP
    VP --> TTS
  end

  subgraph CI/CD & Deployment
    GHA["GitHub Actions (Audit/Tests)"]
    GCB["Google Cloud Build"]
    REG["Artifact Registry"]
    GHA --> GCB
    GCB --> REG
    REG -.-> RUN
  end

  subgraph GCP Production Infrastructure
    RUN["Cloud Run (Backend)"]
    LB["Cloud Load Balancing"]
    HPA["Auto-scaling"]
    CLT["Cloud Tasks (Mission Queue)"]
    LB --> UI
    UI --"[rs256]"--> RUN
    HPA --> LB
    RUN --> CLT
  end

  subgraph Gateway Tier
    GW["FastAPI App Gateway"]
    RATE["Rate Limiter (Redis)"]
    SH["RBAC / SSRF Shield"]
    PII["PII Guardrails"]
    
    RUN --> GW
    GW <--> RATE
    GW --> PII
    PII --> SH
    VP <--> GW
  end

  %% === Central Orchestration ===
  subgraph Central Orchestration
    ORC["Orchestrator (Mission Controller)"]
    SM["Execution State Machine"]
    TEAR["Graceful Teardown"]
    IDEMP["Idempotency Verifier"]
    
    SH --> IDEMP
    IDEMP --> ORC
    ORC <--> SM
    TEAR -.-> ORC
    VP <--> ORC
  end

  %% === Brain Governance ===
  subgraph Brain Governance
    PL["DAG Planner"]
    RC["Reasoning Core"]
    EVO["Evolution Engine"]
    
    ORC --> EVO
    EVO --"Rule Graduation"--> Response
    EVO --"Mission Drift"--> PL
    PL --> RC
    RC <--> EVO
    RC --> EX
  end

  %% === Execution & DCN ===
  subgraph DCN_NET ["Distributed Network (DCN)"]
    EX["Graph Executor"]
    SCHED["Wave Scheduler"]
    VRAM["GPU Backpressure"]
    DCN["Leader Election & P2P"]
    
    RC -.-> EX
    EX --> SCHED
    EX <--> VRAM
    EX <--> DCN
  end

  %% === Agent Ecosystem ===
  subgraph Sovereign Agent Swarm
    AG_BASE["SovereignAgent Base"]
    AG_CODE["Artisan (Code)"]
    AG_TASK["HardRule (Logic)"]
    AG_SEARCH["Scout (Search)"]
    AG_DOC["Analyst (Doc)"]
    COMPENSE["Compensation Engine"]
    
    SCHED --> AG_BASE
    AG_BASE --"[mtls 1.3]"--> AG_CODE
    AG_BASE --"[mtls 1.3]"--> AG_TASK
    AG_BASE --"[mtls 1.3]"--> AG_SEARCH
    AG_BASE --"[mtls 1.3]"--> AG_DOC
    AG_BASE -.-> COMPENSE
  end

  %% === GCP Memory & Consistency ===
  subgraph GCP Managed Memory
    MCM["Memory Consistency Manager"]
    RED["Memorystore (Episodic)"]
    PG["Cloud SQL (Factual)"]
    NEO["Neo4j (Relational)"]
    VEC["Vector DB (Semantic)"]
    VPC["VPC Connector"]
    
    AG_BASE --> MCM
    MCM --"[tcp/resp]"--> RED
    MCM --"[tcp/sql]"--> PG
    MCM --"[bolt]"--> NEO
    MCM --> VEC
    VPC -.-> PG
    VPC -.-> RED
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

## 6. Server Wiring & Security Middleware

The LEVI-AI Gateway is a mission-critical FastAPI application that coordinates model routing, identity verification, and DCN swarm synchronization.

### 6.1 Service Routers (v14.2)
The application is decomposed into specialized domains for isolation and performance:
- `/api/v1/orchestrator`: Central Mission Control and mission lifecycle state machine.
- `/api/v1/auth`: **RS256 Asymmetric Identity** provider.
- `/api/v1/memory`: Gateway to the 4-tier cognitive memory layers.
- `/api/v1/learning`: Evolved intelligence engine and fragility tracking.
- `/api/v1/telemetry`: SSE pulse broadcaster for real-time dashboard updates.
- `/api/v1/compliance`: GDPR Hard-Delete and immutable audit log exports.
- `/api/v1/voice`: **Sovereign Voice Stack** gateway (STT/TTS/Streaming).

### 6.2 Security Middleware Stack
1. **`RS256 Identity Middleware`**: Mandates asymmetric cryptographic verification of JWTs using the project's Public Key.
2. **`SSRF Shield Middleware`**: Inspects all egress payloads to prevent DNS-rebinding attacks and internal CIDR leakage.
3. **`RateLimitMiddleware`**: USes a Redis-backed sliding window for precision throttling of mission execution waves.
4. **`SecurityHeadersMiddleware`**: Enforces strict CSP, HSTS, and Frame-Options for production hardening.

### 6.3 Lifecycle & DCN Gossip Hub
During the `lifespan` event, the server initializes the **DCN Gossip Manager**. This background worker facilitates node discovery and shared cognitive insights across the swarm, ensuring that once a pattern is "Graduated" on one node, it is synchronized globally.

---

## 7. Pipelines & Cognitive Data Flow

| Module | Purpose | Input | Output | Dependencies |
| :--- | :--- | :--- | :--- | :--- |
| **Gateway** | API Entry & Security | HTTP Request | Sanitized Payload | RBAC, Shield |
| **Orchestrator** | Mission Lifecycle | User Intent | Final Response | DAG Planner, DCN |
| **DAG Planner** | Unified Planning | Raw Perception | Goal-Aligned Task Graph | Evolution Engine, LLM |
| **Reasoning Core** | Plan Critique & Simulation | Task Graph | Confidence, Strategy, Refined Graph | Planner, Replay Metadata |
| **Executor** | Parallel Wave Execution | DAG | Node Results | Agents, Redis |
| **Memory Manager** | Tiered Sync & Retrieval | Events | Merged Context | MCM, Neo4j, FAISS |
| **MCM** | Memory Consistency | Memory Events | Versioned State | Redis, Pipeline |
| **Learning Loop** | Outcome Capture & Strategy Reuse | Mission Audit | Best DAG Templates | Evaluator, Corpus, Strategy Ledger |

#### 4.1.1 DAG Generation Strategy
- **Hybrid-LLM**: Uses **Template-Retrieval** for stable patterns (from Evolution Engine) and **Dynamic LLM Generation** for high-fragility or novel intents ($F > 0.4$).
- **Granularity Rules**: 
    - **Split**: When tool-sets differ or node output volume is predicted to exceed 1MB.
    - **Merge**: When dependencies are linear and context overlap between nodes is $> 80\%$.
- **Cost Model ($C_{dag}$)**: 
    $$C_{dag} = \sum (\text{Model Cost} + \text{Tool Latency}) \times \text{Risk Factor}$$
    *Risk Factor is increased by 2.0x for sensitive domains or high-fragility routes.*

---

## 5. Execution Model

### 5.1 Task Execution Contract (TEC)

Every mission is decomposed into a directed acyclic graph (DAG) of task nodes. Each node defines a **TEC**:

- **`compensation_action`**: Recovery action recorded for failure handling and replay.

#### 5.1.1 Node Lifecycle States
- **CREATED**: Manifest initialized in memory.
- **QUEUED**: Dependencies satisfied; awaiting available wave slot.
- **RUNNING**: Active execution by a Sovereign Agent.
- **COMPLETE**: Result validated and stored in MCM.
- **FAILED**: Retries exhausted; compensation triggered.

#### 5.1.2 Retry & Backoff
- **Backoff Strategy**: Exponential backoff ($t = 2^n \times 500ms$) up to 2 retries.
- **Dependency Timeout**: Cross-node dependency wait-time is capped at $5000ms$.
- **Partial Completion Policy**: **Wait-All (Default)**. If a non-critical node fails, the DAG continues. If a **Critical Node** fails, the Orchestrator triggers an immediate abort of downstream dependents and executes compensation.

### 5.2 Mandatory Reasoning Pass

Before the DAG reaches the Executor, the Reasoning Core performs:

- **Plan Critique**: Detects missing dependencies, shallow plans, and weak resilience structure.
- **Simulation Pass**: A rule-based dry-run of the DAG with mock outputs to expose blocked branches.
- **Confidence Scoring ($S$ )**: 
  $$S = 0.92 - (0.2 \cdot \text{Issues}) - (0.05 \cdot \text{Warnings}) - (0.2 \text{ if simulation blocked}) - \text{complexity penalty}$$
- **Execution Strategy Selection**: Chooses normal DAG execution or `safe_mode` linear fallback.

The planner supports a minimum two-pass flow when $S < 0.55$ or when $\ge 1$ issues are detected: Generation -> Critique -> Refinement.

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
| **Tier 0 (Event Log)** | Redis Stream | Primary Source of Truth | Immediate Append |
| **Tier 1 (Episodic)** | Redis KV | Recent session history | Derived via Log |
| **Tier 2 (Factual)** | PostgreSQL | Immutable interaction log | Derived via Log |
| **Tier 3 (Relational)** | Neo4j | Knowledge graph triplets | Derived via Pipeline |
| **Tier 4 (Semantic)** | Vector DB | Semantic fact retrieval | Derived via Embedding |

**Fidelity Scoring System ($F$ )**:
Missions are evaluated across four dimensions to determine graduation and learning:
$$F = (0.4 \cdot C) + (0.3 \cdot G) + (0.2 \cdot L) + (0.1 \cdot U)$$
- **$C$ (Correctness)**: Percentage of successful node completions.
- **$G$ (Grounding)**: Factual resonance score from internal fact-checkers.
- **$L$ (Latency)**: Time-efficiency score ($1.0 - \min(1.0, \frac{\text{Latency}}{\text{SLA}})$).
- **$U$ (User Feedback)**: Explicit or implicit satisfaction signal.

**Memory Consistency Manager (MCM)**:

- Implements **Event Sourcing**: The Single Event Log (Redis Stream) is the absolute truth.
- **Conflict Resolution**: MCM uses a "Last-Event-Wins" (LEW) strategy based on the Global Sequence ID ($SID$).
- **5-Tier Absolute Wipe (GDPR)**: Graduation verified physical erasure of:
    1. **Vector** (FAISS/HNSW HPO-Indices)
    2. **Graph** (Neo4j Relational Context)
    3. **NoSQL** (Firestore Episodic & Jobs)
    4. **Cache** (Redis Short-term Keys)
    5. **SQL** (PostgreSQL Identity & Traits)
- **Synchrony Model**: Asynchronous reconciliation with a maximum lag target of $500ms$ via background MCM workers.

### 6.1 Mission Learning Loop

Each completed mission is treated as a training signal:

- **Outcome Evaluator**: Scores fidelity, grounding, and latency.
- **Pattern Capture**: High-quality missions are stored in the training corpus.
- **Strategy Ledger**: Best-performing graph signatures are retained per intent and reused during planning.

---

## 8. Pipelines & Cognitive Data Flow

LEVI-AI orchestrates data through three primary specialized pipelines.

### 8.1 Ingestion Pipeline (RAG Flow)
`Source (Web/File) -> Clean -> Chunk -> Semantic Embedding (Local LLM) -> Vector Pulse -> Vector DB Store`
- Optimized for batch processing of large datasets without blocking the primary mission waves.
- Uses asynchronous workers to populate the FAISS/HNSW indices.

### 8.2 Self-Evolution Pipeline (Learning Loop)
`Failure Detection -> Insight Capture (Postgres) -> Council of Models Optimization -> System Patch -> Graduation Rule`
- Automatically analyzes missions with low fidelity scores ($F < 0.6$).
- Promotes stable reasoning patterns to the **Fast-Path** cache once they achieve $\ge 95\%$ average fidelity.

### 8.3 Mission Execution Pipeline
`Orchestrator -> DAG Planner -> Reasoning Core -> Wave Executor (Greedy Waves) -> Outcome Collector`
- The system parallelizes task nodes into "waves" based on dependency satisfaction.
- Every mission is idempotent and results are cached across the 3-tier semantic cache.

---

## 9. CI/CD & Production Pipelines

LEVI-AI employs a robust CI/CD strategy to maintain **100% Production Stability**.

### 9.1 GitHub Actions Workflows
The repository includes 13+ specialized workflows for automated testing and deployment:
- **`deploy-backend.yml`**: Triggers on pushes to `main`. Builds and deploys the Sovereign Gateway to **GCP Cloud Run**.
- **`production_readiness.yml`**: Runs the 10-step graduation suite, including stress tests and auth verification.
- **`certification_gate.yml`**: Mandatory security scan and license compliance check before deployment.
- **`sovereign-graduate.yml`**: Automates the tagging and archiving of production-stable releases.

---

## 8. Brain: Core Reasoning & Orchestration

The LEVI-AI Brain is the centralized intelligence tier of the Sovereign OS. It governs the transition from unstructured user intent to deterministic mission execution waves.

### 🧠 Reasoning Algorithm (Master Flow)
The reasoning pipeline follows a strict five-stage transformation:
`User Intent → Perception → Planner → DAG → Reasoning (Gate) → Executor → Output`

### 🎯 Orchestrator State Machine
The mission lifecycle is governed by a strict state machine:

```mermaid
stateDiagram-v2
    [*] --> CREATED: User POST
    CREATED --> QUEUED: Validated
    QUEUED --> RUNNING: Dependency Satisfied
    RUNNING --> COMPLETED: Success
    RUNNING --> FAILED: Critical Node Failure
    FAILED --> RETRY: Compensation Logic
    RETRY --> RUNNING
    COMPLETED --> [*]
```

### ⚡ Confidence Scoring Logic
The **Reasoning Core** calculates a Confidence Score ($S$) before allow any DAG to enter the execution pipeline:

$$S = 1.0 - (0.2 \cdot \text{Issues}) - (0.05 \cdot \text{Warnings}) - \text{Complexity Penalty}$$

- **Threshold**: Missions with $S < 0.55$ are automatically sent back for **Re-Planning (Pass 2)**.

---

### 13.1 Request Flow
```mermaid
sequenceDiagram
    participant U as User
    participant G as Gateway
    participant O as Orchestrator
    participant P as Planner
    participant R as Reasoning
    participant E as Executor
    participant A as Agents
    
    U->>G: Mission Request
    G->>O: Initialize State
    O->>P: Generate Plan
    P->>O: DAG (Task Graph)
    O->>R: Verify & Score
    R->>O: Confidence S > 0.6
    O->>E: Start Waves
    E->>A: Execute Nodes
    A->>E: Node Results
    E->>O: Mission Complete
    O->>G: Final Response
    G->>U: Mission Success
```

### 13.2 DAG Execution Flow (Waves)
```mermaid
graph TD
    Node1[Start Node] --> Wave1[Wave 1]
    Wave1 --> NodeA[Tool Call A]
    Wave1 --> NodeB[Search B]
    NodeA --> Wave2[Wave 2]
    NodeB --> Wave2
    Wave2 --> NodeC[Synthesis C]
    NodeC --> End[Final Output]
```

### 13.3 Memory Flow (MCM Sync)
```mermaid
graph LR
    Runtime[Runtime Event] --> Stream[Redis Stream]
    Stream --> MCM[Consistency Manager]
    MCM --> Redis[Episodic Cache]
    MCM --> PG[Factual DB]
    MCM --> Neo4j[Knowledge Graph]
    MCM --> Vector[Semantic Memory]
```

### 13.4 Agent Execution Flow
```mermaid
graph TD
    In[Input] --> Valid[Validate Contract]
    Valid --> Exec[Execute Agent Logic]
    Exec --> Out[Collect Result]
    Out --> Store[MCM Event Emission]
```

### 13.5 CI/CD Pipeline
```mermaid
graph LR
    Commit --> Build[Build Container]
    Build --> Test[Unit & Integration]
    Test --> Security[Security Scan]
    Security --> Deploy[Cloud Run Deploy]
    Deploy --> Smoke[Graduation Audit]
```

### 13.6 Voice Pipeline
```mermaid
graph LR
    AudioIn[Audio Input] --> STT[Whisper STT]
    STT --> Mission[Mission Flow]
    Mission --> Result[Text Response]
    Result --> TTS[Coqui TTS]
    TTS --> AudioOut[Audio Response]
```

---

## 🚀 Future Roadmap & Alignment

### 🧩 What Data Must Be Updated (Section 14)
- **Status Change**: All claims of "Production Ready" have been updated to **Architecture Complete, Implementation in Progress**.
- **Stability**: Claims of "100% Stable" have been removed in favor of **Graduation Verified Baseline (Audit-Stable)**.

### ❓ Final Reality Check (Section 15-17)

**Is LEVI-AI fully functional?**
**No** — it is NOT functional yet as a consumer-facing OS. 

**Implementation Status**:
- **Architecture**: ✅ 90% (Finalized & Locked)
- **Implementation**: ~35% (Core logic existing, stubs in utility layers)
- **Integration**: ⚠️ Partial (Service-to-service wiring in progress)
- **Execution**: ❌ Not 100% end-to-end reliable in local dev

**What will make it functional?**
1.  Full wiring of the **Frontend to the broadaster SSE stream**.
2.  Physical integration of **Ollama / Local LLM fallback** across the agent swarm.
3.  Transition from **Mocked to Real Mission Audits** in the Graduation Suite.

---

## 🚧 Final Disclaimer

LEVI-AI v14.2 is a high-fidelity system design. While the architecture is production-hardened, the implementation is under active development. This repository is intended for research and engineering contributions toward sovereign, local-first artificial intelligence.
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.

---

## 11.3 Versioning & Upgrade Strategy

- **Backward Compatibility**: v14.1 maintains a **DAG Translation Shim** to execute legacy v14.0 JSON manifests.
- **Model Upgrades**: Embedding shifts are handled via the **JIT Re-embedding** layer in Tier-4.
- **State Migration**: Redis snapshots from v14.0 are 100% compatible with the v14.1 Raft-lite log.

---

## 12. Failure Handling & Recovery

| Failure Category | Detection Mechanism | Recovery Logic | Escalation |
| :--- | :--- | :--- | :--- |
| **DAG Conflict** | Planner Validation | Regenerate linear plan | Abort mission |
| **Tool Failure** | Executor Exception | Node retry (max 2) | Fallback to Chat |
| **Agent Timeout** | TEC Enforcement | Exponential backoff | Compensate node |
| **Memory Desync** | MCM Version or checksum mismatch | Force source-of-truth verification | Log Audit |
| **VRAM Overload** | VRAM Monitor Pulse | Disable Critic loops | Linear execution |
| **Cloud Fallback** | Model Router Pulse | Switch to local Ollama | Service Degraded |
| **Duplicate Mission** | Idempotency claim collision | Return existing mission handle | Suppress duplicate execution |

### Compensation Engine (Rollback Logic)

If a critical task node fails after all retries, the **Compensation Engine** executes rollback actions defined in the TEC (e.g., reverting database changes or emitting a failure pulse to the user). 

- **Failure Type F-3 (System/Infra)**: Triggers an automatic **80% credit refund** to the user and initiates LIFO mission-wide compensation.
- **Failure Type F-1/F-2 (User/Logic)**: Triggers local node compensation; no credit refund.
- **Idempotency Proof**: All compensation actions are idempotent and tracked via the `CompensationCoordinator` to prevent double-reverts.

---

## 13. Observability & Telemetry

### 13.1 Global Tracing

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

### 13.2 Quality Metrics
- **Performance**: P95 Latency tracked per domain.
- **Quality**: Fidelity scores across the last 100 missions.

### 13.3 Auto-Remediation & Alerts
- **SLO Violation (Latency > 2s)**: Triggers an automatic cache-flush and shard-rebalance for the Vector DB.
- **Node Drift (> 0.4 Fragility)**: Triggers an immediate "Deep Reasoning" lock for the affected domain.
- **Memory Inconsistency**: Triggers a forced MCM resync from the Redis Event Log (Source of Truth).

---

## 14. Testing Strategy

LEVI-AI employs a multi-layered testing strategy to ensure reliability across its distributed components.

### 14.1 Unit Testing

- **Agents**: Every agent in the registry is tested for input/output schema adherence.
- **Engines**: The Goal Engine, Planner, and Reasoning Core are tested for DAG validity, simulation behavior, and confidence scoring.
- **Utils**: Security filters and sanitizers are tested against known injection patterns.

### 14.2 Integration Testing

- **End-to-End Missions**: Simulated user requests are routed through the entire pipeline to verify completion.
- **Memory Consistency**: Tests verify that writes to Redis are correctly synchronized to Postgres, Neo4j, and FAISS.
- **DCN Gossip**: Pulses are simulated to ensure nodes correctly process swarm telemetry.
- **Replay & Idempotency**: Tests verify duplicate mission suppression and deterministic replay payload capture.
- **RBAC Negatives**: Protected routes are tested for no token, expired token, and wrong-role token handling.
- **Live Ollama Smoke**: Optional non-mocked tests validate real local inference when `RUN_LIVE_OLLAMA_TESTS=1`.

### 14.3 Chaos & Reliability

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

## 15. Contribution & Development

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

## 16. Limitations & Roadmap

### Current Limitations

- **Hardware**: Strongly dependent on `nvidia-smi` for backpressure logic; non-NVIDIA environments will default to linear execution.
- **Connectivity**: Cloud fallback requires active internet; local mode disables high-cost reasoning but ensures 100% data sovereignty.
- **Latency**: High-complexity DAGs (depth > 6) may incur significant reasoning overhead due to recursive validation steps.
- **Horizontal Scaling**: [GRADUATED] DCN multi-node peering is stable for up to 5 authenticated nodes. Higher counts require multi-cluster ingress (v15 roadmap).

---

## 17. System Manifest

For a complete, auto-generated list of all internal modules, services, and agent registries, see the [SYSTEM_MANIFEST.md](./SYSTEM_MANIFEST.md).

---

*© 2026 Sovereign Engineering. Built for predictability, observability, and absolute autonomy.*

---

## 18. v14.1 Architectural Migration Note

As of version **v14.1.0-Autonomous-SOVEREIGN**, the LEVI-AI OS has simplified its cognitive surface area:

- **Cognitive Collapse**: The separate `Brain` and `GoalEngine` modules have been consolidated into the unified **Sovereign Orchestrator** and **DAG Planner**.
- **Evolutionary Intelligence**: The **Evolution Engine** now governs deterministic rules and fragility tracking ($F \ge 0.4$), enabling the **Deterministic Fast-Path** ($< 200ms$).
- **Hybrid Consensus**: DCN synchronization now utilizes a hybrid **Raft-lite + Gossip** protocol for 100% mission state integrity.
- **Event Sourcing**: Memory moves to a single-write-authority model via **Redis Streams**, with MCM managing asynchronous projections across all tiers.

---

## 19. Configuration Reference

The following environment variables configure the Sovereign OS. Defaults are safe for local development but should be overridden in production.

| Variable                 | Default                           | Description                                                                 |
| :---                     | :---                              | :---                                                                        |
| REDIS_URL                | redis://localhost:6379/0          | Runtime state and rate limiter store (local)                                |
| POSTGRES_URL             | postgresql+asyncpg://…            | SQL fabric for immutable history and profiles                               |
| NEO4J_URI                | bolt://localhost:7687             | Relational knowledge graph                                                  |
| GCP_PROJECT_ID           | none                              | Target Google Cloud Project ID for production deployment                    |
| GCP_REGION               | us-central1                       | Target GCP Region for Cloud Run and managed services                        |
| CLOUD_SQL_CONNECTION_NAME| none                              | Full connection string for Cloud SQL (project:region:instance)              |
| CLOUD_TASKS_QUEUE_NAME   | levi-jobs-queue                   | Target queue name for prioritized mission waves                             |
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

## 20. Connection Wiring & Internal Service Mappings

LEVI-AI components are "wired" through a combination of environment variables and internal discovery pulses.

| Component | Target Wire | Protocol | Wiring Logic |
| :--- | :--- | :--- | :--- |
| **Gateway -> Redis** | `REDIS_URL` | TCP/RESP | Mission locking, wave scheduling, cache. |
| **Gateway -> SQL** | `POSTGRES_URL` | TCP/SQL | Immutable ledge, user profiles, audit. |
| **ORC -> DCN** | `DCN_SECRET` | HMAC-SHA256 | Signed Gossip pulses for state reconciliation. |
| **ORC -> Agents** | `INTERNAL_SERVICE_KEY` | mTLS 1.3 | Trusted service-to-service communication. |
| **ORC -> LLM** | `OLLAMA_HOST` | HTTP/REST | Local-first inference routing. |
| **Memory -> Neo4j**| `NEO4J_URI` | Bolt | Relational knowledge mapping. |
| **Memory -> Vector**| `VECTOR_BACKEND` | gRPC/Local | FAISS/HNSW similarity retrieval. |
| **Pipeline -> GCS** | `GCP_PROJECT_ID` | HTTPS | Managed artifact and backup storage. |

### 20.1 Internal Service Communication
The system utilizes the `InternalServiceClient` to perform zero-trust requests between nodes. Every request is signed ($Sig = Sign_{HMAC}(Payload, Secret)$) and includes a unique `X-Trace-ID` to ensure end-to-end observability across the distributed cognitive network.

---

## 19. Deployment Guides

### 19.1 Docker Compose (Local)

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

## 20. Graduation Verification Matrix (v14.1.0)

The following matrix represents the final audit status for the LEVI-AI Sovereign Graduation:

| Dimension | Proof Mechanism | Verification Status |
| :--- | :--- | :--- |
| **Identity Persistence** | RS256 Signature Cross-check | ✅ 100% |
| **Network Egress** | DNS-Rebinding / SSRF Probe | ✅ 100% |
| **DCN Consistency** | Raft-lite Quorum Heartbeat | ✅ 100% |
| **Memory Privacy** | 5-Tier Absolute GDPR Wipe | ✅ 100% |
| **Resilience Engine** | LIFO Compensation Rollback | ✅ 100% |
| **Financial Integrity** | Global Credit/Refund Logic | ✅ 100% |
| **Health Score** | Metrics Hub `graduation_score` | ✅ 1.0 (Stable) |

---

## 21. System Manifest

For a complete, auto-generated list of all internal modules, services, and agent registries, see the [SYSTEM_MANIFEST.md](./SYSTEM_MANIFEST.md).

Example K8s Deployment Fragment:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: levi-backend
spec:
  replicas: 3
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
```
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

## 21. End-to-End Walkthroughs

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

## 22. Extension Points

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

## 23. Trace & Telemetry Taxonomy

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

## 24. Memory Consistency Rules

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

## 25. Security Hardening Checklist

- Enable RBAC and JWTs on all API routes.
- Enforce sandbox for code execution nodes.
- Use KMS‑managed envelope keys for secrets.
- Activate prompt shield on the gateway.
- Block outbound egress except for whitelisted domains.
- Enforce strict CSP, HSTS, and X-Frame-Options outbound headers globally.
- Activate Redis sliding-window tiered rate limiting to prevent API abuse.
- Rotate `AUDIT_CHAIN_SECRET` with proper key management.

---

## 26. Performance Tuning

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

## 27. Troubleshooting & FAQ

- Symptoms: “Could not establish a connection to backend (MySQL Shell)”
  - Cause: legacy monitors expecting MySQL; LEVI uses Postgres.
  - Resolution: remove outdated MySQL checks; validate `POSTGRES_URL`.

- Symptoms: High latencies during research missions
  - Cause: excessive DAG depth or slow external sites.
  - Resolution: reduce `max_dag_depth`, enable browser_agent only when needed.

- Symptoms: Critic loops cause delays
  - Cause: deep reasoning enabled under resource pressure or high frequency.
  - Resolution: backpressure disables secondary reflection; verify `vram:pressure` and `BrainMode` transitions.

---

## 28. Glossary

- **Sovereign OS**: An AI operating system emphasizing control and predictability.
- **TEC**: Task Execution Contract; per‑node guardrails defining retries, timeout, and allowed tools.
- **Wave Scheduling**: Parallel groups of DAG nodes executed once dependencies are satisfied.
- **MCM**: Memory Consistency Manager; orchestrates versioned runtime writes and fan‑out via Event Sourcing.
- **DCN**: Distributed Cognitive Network; multi-node scale-out architecture (v14.2.0 Hybrid Consensus).

---

## 29. Change Log (v14.2 Highlights)

- Added Central Execution State Machine with explicit transitions.
- Introduced TECs and global execution budgets.
- Implemented Memory Consistency Manager with versioning and dedup.
- Added deterministic Replay Engine harness for post‑mortem analysis.
- Introduced adaptive scheduler with VRAM backpressure signals.
- Hardened agents to be dumb executors under a centralized orchestrator.

---

## 30. SLOs & Error Budgets

- Availability SLO: 99.5% for Gateway and Orchestrator.
- Latency SLO: P95 end-to-end mission **< 2.0s** for FAST mode (Fast-Path Active).
- Error Budget Policy: auto-throttle concurrency and compensate missions when burn rate exceeds thresholds.

---

## 31. Operational Runbooks

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

## 32. Extension Examples

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

---

*© 2026 Sovereign Engineering. Built for predictability, observability, and absolute autonomy.*
