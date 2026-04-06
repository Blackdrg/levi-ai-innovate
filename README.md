# 🧠 LEVI-AI: Local-First Distributed AI Stack (v1.0.0-RC1)
### **Technical Graduation: Distributed Sovereignty** 🛡️ 🚀

---

## 📜 PRODUCTION READINESS CHECKLIST (v1.0.0-RC1)
**Date**: 2026-04-06  
**Status**: **INTERNAL COVERAGE ACHIEVED**  
**Readiness Coverage Score**: **28 / 28 (Internal Core Coverage)**  

> [!WARNING]
> **No Third-Party Compliance Statement**: 
> LEVI-AI is designed for alignment with the **NIST AI RMF** and **OWASP LLM Top 10** standards. However, the 28/28 score represents an **internal self-certification** via the `production_readiness_suite.py`. This system has NOT undergone a formal third-party independent audit or government-certified penetration test.

---

> *“Autonomy is not the absence of control, but the presence of a deterministic, audited, and service-oriented architecture.”*

LEVI-AI v1.0.0-RC1 is a high-fidelity, service-oriented multi-agent operating system designed for absolute local sovereignty with managed cloud fallbacks.

---

## ⚡ 0.0 Quick Start
1. `docker-compose up -d`
2. `cd backend && pip install -r requirements.txt && python -m api.main`
3. `cd frontend && npm install && npm run dev`

---

## 🔍 1.0 Current System Reality (Live Status)
| **Brain Core** | ✅ Active | v1.0.0-RC1 Distributed Orchestrator. |
| **Vector Memory**| ✅ Active | HNSW (efSearch: 64 | efConstruction: 200). |
| **Inference** | ✅ Active | Local-First (llama3.1:8b) | GPU Semaphore: 4. |

---

## 🌍 2.0 Distributed Service Architecture
LEVI-AI is composed of five distinct, coordinated services:
- **FastAPI**: Gateway & Orchestration API.
- **Postgres**: Relational Persistence & Tenant Isolation.
- **Redis**: Low-latency Working Memory & Message Queue.
- **Neo4j**: Relational Knowledge Graph.
- **Celery**: Background Task Workers & Memory Pruning.

---

## 📁 3.0 Repository Structure
```text
/backend
  /api          <- Gateway Entry Points
  /core         <- Orchestration Logic
  /agents       <- Specialized Swarm Modules
/infrastructure <- Docker/K8s configurations
```

---

## 🗺️ 4.0 Architecture: Master System Topology (v1.0.0-RC1)
LEVI-AI is built on a 5-service modular architecture optimized for local-first cognitive autonomy. The following **Master Topology** visualizes the 50+ technical nodes that orchestrate the stack.

```mermaid
graph TD
    User((User/Client)) --- Gateway[API Gateway: FastAPIGateway]
    
    subgraph "Sovereign Shield Cluster (Security)"
        Gateway --> RBAC[RBACMiddleware: G/P/C]
        RBAC --> KMS[SovereignKMS: AES-256-GCM]
        KMS --> Boundary[InstructionBoundary]
        Boundary --> Auth[AuthRegistry]
        Auth --> Secrets[SecretManager: Vaulted]
        Secrets --> JWT[JWTRotator]
    end
    
    subgraph "Cognitive Core (Orchestration)"
        JWT --> Brain[BrainController]
        Brain --> Goal[GoalEngine]
        Goal --> Planner[MissionPlanner]
        Planner --> Executor[GraphExecutor: Wave]
        Executor --> Wave[WaveScheduler]
        Wave --> Blackboard[(Redis: MissionBlackboard)]
        Brain --> Circuit[CircuitBreaker: Resilient]
    end
    
    subgraph "Swarm Layer (14 Specialized Agents)"
        Executor --> Artisan[Artisan: CodeGen]
        Executor --> Scout[Scout: Research]
        Executor --> Critic[Critic: Adjudicator]
        Executor --> Consensus[Consensus: Validator]
        Executor --> Coder[Coder: Logic]
        Executor --> Researcher[Researcher: Web]
        Executor --> Analyst[Analyst: Data]
        Executor --> SwarmAPI[SwarmControl: API]
    end
    
    subgraph "Local-First Inference Stack"
        Artisan --- Ollama[Ollama: Local Engine]
        Ollama --- L31[Llama 3.1: 8b - Primary]
        Ollama --- L33[Llama 3.3: 70b - Reasoning]
        Ollama --- P3[Phi-3: Mini - Logic]
        Ollama --- Nomic[Nomic-Embed: Vector]
        Ollama --- Proxy[CloudFallbackProxy: Gated]
    end
    
    subgraph "Tooling & Execution Environment"
        Artisan --> Docker[DockerSandbox: Isolated]
        Scout --> WebProxy[EgressProxy: Filtered]
        Scout --> LocalFS[Local FileSystem]
        Scout --> Search[SearchAPI: Tavily]
        Scout --> Browser[BrowserSubagent: Playwright]
        Artisan --> Shell[SecureShell: Restricted]
    end
    
    subgraph "Fidelity Cluster (Validation & Audit)"
        Artisan --> HardRule[HardRuleValidator: AST]
        HardRule --> Syntax[SyntaxChecker: PyLint]
        HardRule --> Logic[LogicVerifier: JSON]
        Logic --> Score[FidelityScore S > 50/50]
        Score --> Pulse[TelemetryBroadcaster: zLib]
    end
    
    subgraph "Memory Vault (Quad-Persistence Layer)"
        Brain --> MM[MemoryManager]
        MM --> Redis[(Redis: Working State)]
        MM --> Postgres[(Postgres: Episodic Ledger)]
        MM --> Neo4j[(Neo4j: Relational Graph)]
        MM --> FAISS[(FAISS: Semantic Index)]
        
        Redis --- State[MissionContext]
        Postgres --- Profiles[UserProfile]
        Neo4j --- Triplets[Knowledge Triplets]
        FAISS --- HNSW[HNSW: efSearch 64]
        Postgres --- Ledger[UserBillingLedger]
        MM --> Snap[SnapshotOrchestrator: Backup]
    end
    
    Score --> Commit[CommitToMemory]
    Commit --> MM
    
    Gateway --> SSE[SSETelemetryHub]
    SSE --> Zlib[zlibCompressor]
    Zlib --> User
    
    %% Color Coding
    style User fill:#ce93d8,stroke:#333
    style Gateway fill:#ce93d8,stroke:#333
    style SSE fill:#ce93d8,stroke:#333
    
    style Sovereign Shield Cluster (Security) fill:#fffde7,stroke:#fbc02d
    style Fidelity Cluster (Validation & Audit) fill:#fffde7,stroke:#fbc02d
    style RBAC fill:#fff176,stroke:#fbc02d
    style KMS fill:#fff176,stroke:#fbc02d
    style Score fill:#fff176,stroke:#fbc02d
    
    style Swarm Layer (14 Specialized Agents) fill:#e8f5e9,stroke:#4caf50
    style Local-First Inference Stack fill:#ffffff,stroke:#333
    
    style Memory Vault (Quad-Persistence Layer) fill:#e3f2fd,stroke:#1e88e5
    style Redis fill:#64b5f6,stroke:#1e88e5
    style Postgres fill:#64b5f6,stroke:#1e88e5
    style Neo4j fill:#64b5f6,stroke:#1e88e5
    style FAISS fill:#64b5f6,stroke:#1e88e5
```

### 4.0.1 Diagram Legend
| Color | Cluster Type | Purpose |
| :--- | :--- | :--- |
| **Purple** | **User / Ingress** | Primary entry, SSE telemetry, and client-side real-time pulses. |
| **Yellow** | **Security / Validation** | Auth, RBAC, AES-256-GCM encryption, and hard-rule fidelity gates. |
| **Green** | **Execution / Swarm** | Specialized multi-agent orchestration and sandboxed runtime execution. |
| **Blue** | **Persistence / Memory** | Quad-Persistence layer (Episodic, Relational, Semantic, Working states). |
| **White** | **Inference** | Local GGUF model hosting and gated cloud-residency proxies. |

### 4.0.2 Service Interaction Matrix (Core-5)
| Source | Target | Protocol | Port (Internal) | Logic / Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Gateway** | **Redis** | RESP | 6379 | Working memory, pub/sub telemetry, and mission blackboard. |
| **Gateway** | **Postgres** | binary | 5432 | ACID-compliant episodic ledger and tenant-isolated RBAC. |
| **Gateway** | **Neo4j** | Bolt | 7687 | Relational knowledge graph for entity-triplet extraction. |
| **Worker** | **Ollama** | REST/JSON | 11434 | Local GGUF inference (Llama 3.1, Phi-3) and Nomic embeddings. |
| **Artisan** | **Docker** | HTTP/Socket | 2375 | Sandboxed code execution and isolated tool runtimes. |

### 4.1 Master Node Mapping (50+ Detailed Components)
#### 🔒 Security & Ingress Layer
1.  **FastAPIGateway**: Central entry point for REST and SSE telemetry streams.
2.  **RBACMiddleware**: Grade-based (G/P/C) access control for multi-tenant isolation.
3.  **SovereignKMS**: AES-256-GCM encryption engine for PII pseudonymisation.
4.  **InstructionBoundary**: Injects `<MISSION_CONTEXT>` walls to prevent prompt leakage.
5.  **AuthRegistry**: Master store for identity-mission binding.
6.  **SecretManager**: Vaulted storage for DCN secrets and external API keys.
7.  **JWTRotator**: Logic for session-bound token refreshing and rotation.
8.  **EgressProxy**: Gated HTTP client for agents to prevent internal SSRF attacks.

#### 🧠 Cognitive Orchestration Layer
9.  **BrainController**: The cognitive hub managing mission lifecycles and state loops.
10. **GoalEngine**: Decomposes natural language queries into executable goal trees.
11. **MissionPlanner**: Generates a Directed Acyclic Graph (DAG) for swarm execution.
12. **GraphExecutor**: Orchestrates topological parallel execution of task waves.
13. **WaveScheduler**: Logic for managing recursion depth and task dependencies.
14. **MissionBlackboard**: Redis-backed shared memory for inter-agent context.
15. **CircuitBreaker**: Adaptive gating that pauses tasks if DB latency is too high.
16. **LearningThrottler**: Limits background self-evolution tasks to preserve VRAM.

#### 🤖 Swarm Agent Layer (Specialized Modules)
17. **Artisan (CodeGen)**: Specialized in building and testing logic/scripts.
18. **Scout (Research)**: Multi-threaded web exploration and data scraping.
19. **Critic (Adjudicator)**: High-fidelity reflection and failure analysis module.
20. **HardRuleValidator**: Non-probabilistic AST/JSON/Regex verification suite.
21. **Coder (Logic)**: Core reasoning agent for structural/algorithmic tasks.
22. **Researcher (Discovery)**: Synthesizes knowledge from multiple information pools.
23. **Analyst (Quant)**: Processes structured datasets and generates mission insights.
24. **SwarmControl**: Gateway for agents to trigger sub-missions recursively.

#### 🛠️ Tooling & Sandbox Layer
25. **DockerSandbox**: Isolated runtime for OCI-compliant code execution.
26. **SecureShell**: Restricted bash shell for local system interaction (Unix/Git).
27. **BrowserSubagent**: Playwright-based headless browser for complex navigation.
28. **SearchAPI**: Tavily/Serp integration for real-time web grounding.
29. **LocalFS**: Managed interaction with the local host filesystem (Project Drive).
30. **SyntaxChecker**: PyLint-based static analysis for model-generated code.
31. **LogicVerifier**: JSON integrity and schema enforcement module.

#### 💾 Memory & Resonance Layer
32. **MemoryManager**: Master IO orchestrator for the quad-persistence layer.
33. **EpisodicLedger**: Postgres-backed store for historical mission logs.
34. **SemanticIndex**: FAISS HNSW store for high-recall RAG operations.
35. **KnowledgeGraph**: Neo4j hub for relational entity-relationship mapping.
36. **WorkingState**: Redis transient store for real-time mission variables.
37. **SnapshotOrchestrator**: Unified backup and disaster recovery logic.
38. **HNSW Index (efSearch 64)**: Optimized vector search for <100ms recall.
39. **FidelityScore (S)**: The 50/50 weighted metric for output quality.
40. **TelemetryBroadcaster**: zLib-compressed SSE stream for the Sovereign UI.

#### 📡 Inference & Flux Layer
41. **OllamaEngine**: Local interface for GGUF model management.
42. **Llama 3.1 (8B)**: The primary general-purpose inference model.
43. **Llama 3.3 (70B)**: The reasoning-heavy "Brain" for complex adjudication.
44. **Phi-3 (Mini)**: Optimized logic engine for structural validation.
45. **Nomic-Embed**: Local 768-dim vector model for RAG embeddings.
46. **CloudFallbackProxy**: Gated redirection to external APIs (Disabled by Default).

#### 🌀 Evolution & Telemetry Layer
47. **LearningLoop**: Background module for self-refining agent weights.
48. **TelemetryHub**: Real-time observability for cognitive unit (CU) costs.
49. **PulseCompressor**: zLib-logic to minimize network overhead for SSE.
50. **UserBillingLedger**: Permanent ACID records of CU consumption and drift.

---

### 4.2 Quad-Persistence Performance (v1.0.0-RC1)
| Data Store | Purpose | Access Latency | Durability |
| :--- | :--- | :--- | :--- |
| **Redis** | Working Memory & Blackboard | < 5ms | Transient (RAM) |
| **Postgres** | Episodic Ledger & RBAC | < 20ms | Permanent (ACID) |
| **Neo4j** | Relational Knowledge Graph | < 50ms | Permanent (Local) |
| **FAISS** | Semantic Vector Memory | < 100ms | Persistent (Index) |

### 4.3 Resource & Flow Control
- **GPU Guard**: `asyncio.Semaphore(4)` manages neural activity to prevent CUDA Out-Of-Memory (OOM) on 24GB hardware.
- **Circuit Breaker**: If Redis or Postgres latency exceeds 500ms, the system automatically pauses the learning loop (`LearningCircuitBreaker`).
- **Pulse Broadcast**: Telemetry is streamed via **zlib-compressed SSE**, ensuring real-time UI updates.

### 4.4 The Mission Heartbeat (DCN Sync)
The **Distributed Cognitive Network (DCN)** synchronizes inter-node intelligence via HMAC-signed pulses.
> [!IMPORTANT]
> **Single-Node Isolation Mode**: In RC1, DCN is configured for local-mesh synchronization within a single host. P2P multi-node expansion and HMAC-pulse broadcasting are in "Preview" status.

### 4.5 Security Middleware Pipeline
1.  **PII Reduction**: Deterministic masking of emails, keys, and credentials.
2.  **Boundary Enforcement**: Injects `<MISSION_CONTEXT>` walls to prevent prompt leakage.
3.  **Egress Proxy**: Gated HTTP client for agents, preventing SSRF attacks on the local network.

---

## 🏗️ 5.0 Execution Lifecycle
`UNFORMED` → `FORMULATED` → `PLANNED` → `EXECUTING` → `AUDITED` → `FINALIZED`.

---

## 🛡️ 6.0 Security & Sanitization Middleware
### 6.1 PII Encryption & De-identification
- **AES-256 GCM**: Sensitive variables are encrypted via `SovereignKMS` before model handoff, ensuring GDPR-compliant pseudonymisation.
- **Managed Fallback**: `CLOUD_FALLBACK_ENABLED=false` (Default).

---

## 🧠 7.0 Core Execution Engines
| Engine | Responsibility |
| :--- | :--- |
| **Perception** | Intent Detection & Parameter Extraction. |
| **Planner** | Task Graph (DAG) Generation. |
| **Executor** | Distributed Wave Execution. |

---

## 🤖 8.0 The Agent Swarm (14 Specialized Modules)
### 8.1 Agent Implementation Gallery
#### [Artisan] Code Agent
```python
async def write_logic(self, goal: str):
    code = await self.generate_completion(f"Build {goal}")
    return self.tools.write_file("main.py", code)
```
#### [Scout] Research Agent
```python
async def explore(self, topic: str):
    urls = await self.tools.search(topic)
    return [await self.tools.scrape(u) for u in urls]
```

---

## 🗄️ 9.0 Persistent Memory & Durability
| Tier | Backend | Persistence Policy |
| :--- | :--- | :--- |
| **T1: Working** | Redis | `appendfsync everysec` |
| **T2: Episodic** | Postgres | Mission & Message Ledger |
| **T3: Semantic** | FAISS | HNSW (efSearch: 64) |

### 9.1 Backup & Disaster Recovery
- **Hard-Snap Backups**: Coordinated via `backend/scripts/backup.py` (`SnapshotOrchestrator`).
- **Policy**: Periodic crystallization of FAISS indices to `/vault/backups`.

---

## 🏆 10.0 Production Readiness Checklist (28/28 Points)
| Audit Point | Implementation Detail | Status |
| :--- | :--- | :--- |
| **01. Prompt Injection** | NER Boundaries + `<SYSTEM_OVERRIDE>` Protection | ✅ |
| **02. Code Sandboxing** | `DockerSandbox` Resource Isolation | ✅ |
| **03. Embedding Model** | Local Nomic-Embed-Text (efSearch: 64) | ✅ |
| **04. Multi-Tenancy** | `tenant_id` RLS Enforcement | ✅ |
| **05. Output Scrubbing** | Result Sanitization (Markdown/XSS) | ✅ |
| **06. SSRF Protection** | Tool-Level Egress Allowlist (Egress Proxy) | ✅ |
| **07. DAG Execution** | Semaphore(4) Guard | ✅ |
| **08. Fidelity Score S** | 50/50 Neural/Literal Weighting | ✅ |
| **09. Grounding** | Neo4j Relationship Cross-Reference | ✅ |
| **10. Hallucination** | Swarm Consensus Validation (Deterministic 40%) | ✅ |
| **11. Isolation** | Session-Keyed Blackboard Memory | ✅ |
| **12. Sync Integrity** | HMAC-Signed Inter-Agent Messaging (v1 RC1) | ✅ |
| **13. RBAC Matrix** | Three-Tier Permission Shield (G/P/C) | ✅ |
| **14. GDPR / Erasure** | 5-Tier Memory Wipe (Zero Semantic Residue) | ✅ |
| **15. PII Masking** | SHA-256 Deterministic De-identification | ✅ |
| **16. Pattern Approval** | HITL Review for Logic Promotion | ✅ |
| **17. Vault Security** | AES-256 Envelope Encryption | ✅ |
| **18. Residency** | Multi-Store Local Backup | ✅ |
| **19. Versioning** | `PromptRegistry` v1.0 templates | ✅ |
| **20. CU Billing** | SQL Unit Cost Recording (Postgres) | ✅ |
| **21. Observability** | SSE Telemetry (Compressed zlib) | ✅ |
| **22. Flow Control** | Adaptive Request Throttling (Circuit Breaker) | ✅ |
| **23. Rate Limiting** | Sliding Window (Redis-backed) | ✅ |
| **24. API Resilience** | `X-Sovereign-Version` Header Check | ✅ |
| **25. Security Headers** | Hardened CSP/HSTS Policy | ✅ |
| **26. Identity Cycle** | JWT JTI Blacklisting & Rotation | ✅ |
| **27. DCN Gossip** | HMAC-SHA256 Inter-node Heartbeat | ✅ |
| **28. Health Pulse** | Service-Level Connectivity Heartbeats | ✅ |

---

## 🔐 11.0 Permissions Hierarchy (RBAC Matrix)
| Role | Access | Missions | Logic Control |
| :--- | :--- | :--- | :--- |
| **Guest** | Read-Only | 0 Missions | No Vault Access |
| **Pro** | Exec Missions | 100/day | Read Vault Access |
| **Creator** | Full Control | Unlimited | Full Vault + System Override |

---

## 📊 12.0 Performance Reality Matrix (Measured v1.0.0-RC1)
| Mission Tier | Hardware (RTX 3090/4090) | Concurrency |
| :--- | :--- | :--- |
| **L1: Static Logic** | CPU / Shared Hosting | **Unlimited** |
| **L2: DB Operations**| Local SSD / NVMe | **Unlimited** |
| **L3: Swarm Tools** | Multi-core CPU / Net | **Unlimited** |
| **L4: Neural Tasks** | NVIDIA GPU (24GB VRAM) | **4–16 Missions** |

---

## 🌐 13.0 Network Topology & Service Ports
The LEVI-AI stack operates as a coordinated set of containerized services. For production stability, ensure the following ports are mapped and accessible within the internal bridge network.

| Service | Protocol | Internal Port | External Port (Default) | Role |
| :--- | :--- | :--- | :--- | :--- |
| **API Gateway** | HTTP | 8000 | 8000 | FastAPI Gateway & Orchestrator |
| **Relational DB**| TCP | 5432 | 5432 | Postgres (Episodic & Ledger) |
| **Working Mem** | TCP | 6379 | 6379 | Redis (State & Message Queue) |
| **Graph Mem** | Bolt | 7687 | 7687 | Neo4j (Semantic Knowledge Graph) |
| **Inference** | HTTP | 11434 | 11434 | Ollama (Local Inference Engine) |

---

## 📡 14.0 Telemetry Specification (The Pulse)
All system events are broadcast via Server-Sent Events (SSE) and WebSocket conduits using the following telemetry schema.

### 14.1 Telemetry Pulse Schema
```json
{
  "type": "TELEMETRY_PULSE",
  "path": "/api/v1/orchestrator/mission",
  "latency_ms": 142.5,
  "status": 200,
  "version": "v1.0.0-RC1",
  "ts": "2026-04-06T14:15:00Z"
}
```
- **zlib Compression**: SSE streams are automatically zlib-compressed when client headers accept `deflate`.
- **Privacy Policy**: All PII is SHA-256 masked *before* telemetry emission.

---

## 🧪 15.0 Programmatic Audit Methodology
The graduation of LEVI-AI is not merely a documentation claim; it is programmatically verified by the `v1_graduation_suite.py`.

### 15.1 Verification Engine
- **Deterministic Validation**: Uses the `DeterministicValidator` to perform non-probabilistic checks (syntax, regex, JSON integrity).
- **Rule Weighting**: Fidelity score $S$ is calculated as $S = (LLM_{Appraisal} \times 0.6) + (Rule_{Truth} \times 0.4)$.
- **Execution**: Run `pytest tests/v1_graduation_suite.py -v` to repeat the 28-point audit certification.

---

## ⚙️ 16.0 Environment Hardening Guide
To reach v1.0.0-RC1 compliance, the following variables must be configured in your `.env` file.

### 16.1 Critical Security Keys
- `DCN_SECRET`: Must be a **64-character hex string** (32-byte). Used for HMAC-SHA256 inter-node pulse signing.
- `INTERNAL_SERVICE_KEY`: Used for authentication between the Gateway and custom Agent Workers.
- `CLOUD_FALLBACK_ENABLED`: Must be `false` for air-gapped or high-privacy deployments.

---

## 🏁 🛡️ 🚀 GRADUATION COMPLETE.
🎓 **STATUS**: v1.0.0-RC1 Local-First AI Stack Stabilized.
© 2026 LEVI-AI SOVEREIGN HUB. Engineered for Technical Autonomy.
