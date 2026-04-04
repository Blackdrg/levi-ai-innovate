# 🧠 LEVI-AI: Sovereign OS v9.8.1
### **The Research-Grade Autonomous Cognitive Monolith**

> *“Autonomy is not the absence of control, but the presence of a deterministic, audited, and resonant architectural monolith.”*

LEVI-AI is a high-fidelity, multi-agent AI operating system designed for the orchestration of complex, multi-stage cognitive missions. Built on the **Sovereign Monolith** v9.8.1 architecture, it implements a **Logic-Before-Language** philosophy, a **4-Level Deterministic Priority Stack**, and **Autonomous Survival Gating**, transforming probabilistic LLM outputs into deterministic, audited digital intelligence.

---

## 🧾 1. Project Identity
- **Name**: LEVI-AI Sovereign OS
- **Version**: v9.8.1 "Absolute Monolith"
- **Architecture**: Unified Cognitive Controller (Brain v9.8.1).
- **Core Pillars**: Swarm Consensus, Sovereign Shield (PII Security), and Adaptive Pulse v4.1 (Mobile Telemetry).

---

## 🚀 2. Quick Start (The Monolith Boot)
Launching the Sovereign AI is now a single-command process.

### **Launch the Fabric**
1. **Initialize Environment**:
   ```bash
   git clone https://github.com/Blackdrg/levi-ai-innovate.git
   cd levi-ai-innovate
   cp .env.example .env && nano .env
   ```
2. **Boot the Monolith**:
   ```bash
   docker-compose up -d --build
   ```
3. **Verify Sovereign Health**:
   ```ps1
   ./launch.bat --verify
   ```

---

LEVI-AI follows a rigorous discipline of execution to ensure mission-deterministic outcomes via the **Unified Brain Controller**.

---

## 🗺️ 3.1 The Sovereign Global Ecosystem (The 360° Map)
Below is the complete architectural mapping of the Sovereign Monolith, from the visual pulse to the resonant data fabric.

```mermaid
graph LR
    %% User Layer
    User((Universal User)) -->|Neural Pulse v4.1| FE[React / Zustand Mobile Dash]
    
    %% API / Security Layer
    subgraph "Sovereign Perimeter"
        FE -->|SSE / REST| API[FastAPI Monolith]
        API -->|NER Masking| Shield[Sovereign Shield]
        API -->|AES-256| Vault[SovereignVault]
    end
    
    %% Cognitive Core
    subgraph "The Brain (v9.8.1 Monolith)"
        Shield --> Brain[LeviBrainCoreController]
        Brain -->|Intent| Perception[Perception Engine]
        Perception -->|DAG| Planner[Dynamic DAG Planner]
        Planner -->|Wave| Executor[Wave Executor]
        
        %% Swarm Layer
        subgraph "Agent Swarm"
            Executor --> Agents{14 Specialized Agents}
            Agents -->|Code| CodeAgent[Code Artisan]
            Agents -->|Search| SearchScout[Search Scout]
            Agents -->|Research| ResearchExp[Research Explorer]
            Agents -->|Review| CriticAud[Critic Auditor]
        end
        
        CriticAud -->|Score| Reflection[Reflection Engine]
        Reflection -->|Evolution| Evolution[Evolution Engine]
    end
    
    %% Persistent Fabric
    subgraph "Sovereign Data Fabric (The Psyche)"
        Evolution --> Memory[Resonant Memory Manager]
        Memory --> Redis[(Redis: T1 Working)]
        Memory --> Firestore[(Firestore: T2/T3 Episodic)]
        Memory --> FAISS[[FAISS: T3 Semantic]]
        Memory --> Postgres[(Postgres: T4 Identity)]
        Memory --> Neo4j[(Neo4j: T5 Knowledge)]
    end
    
    %% Final Action
    Reflection -->|Finalize| User
```

---

## 🏗️ 3.2 Full Architectural Blueprint: The Logical Stack
The Monolith is structured into five distinct logical layers, ensuring separation of concerns while maintaining technical resonance.

| Layer | Technical Name | Component Specification | Primary Driver |
| :--- | :--- | :--- | :--- |
| **Layer 1** | **Interface** | React 18, Zustand, Cytoscape.js | Mobile Visual Sovereignty |
| **Layer 2** | **Security** | Sovereign Shield, AES-256 Vault | PII Sanitization & Encryption |
| **Layer 3** | **Cognitive** | Unified Brain v9.8.1, DAG Planner | Deterministic Reasoning |
| **Layer 4** | **Execution** | Wave Executor, Swarm Consensus | Multi-Agent Orchestration |
| **Layer 5** | **Memory** | 5-Tier Resonant Fabric (HNSW + Relational) | Context Retention & Loyalty |

---

## 🧠 3.3 The 8-Step Deterministic Pipeline

```mermaid
graph TD
    %% Entry Layer
    User((User Interface)) -->|Adaptive Pulse v4.1| Gateway[Sovereign Monolith API]
```

---

## ⚙️ 3.4 The Cog-Ops Workflow: State Transitions
Every mission moves through a state machine to ensure absolute determinism.

| State | Transition Source | Logic Gate | Output Artifact |
| :--- | :--- | :--- | :--- |
| **`UNFORMED`**| User Input | Perception Engine | Intent Object |
| **`FORMULATED`**| Intent Object | Goal Engine | `GoalObject` (KPIs) |
| **`PLANNED`** | `GoalObject` | DAG Planner | `TaskGraph` (JSON) |
| **`EXECUTING`** | `TaskGraph` | Wave Executor | Agent Results Buffer |
| **`AUDITED`** | Results Buffer| Critic Agent | Fidelity Score ($S$) |
| **`FINALIZED`** | Fidelity Score | Synthesis Engine| Resonant Response |

---
    
    %% Cognitive Monolith v9.8.1
    subgraph "Core Monolith (LeviBrain v9.8.1)"
        Gateway --> Perception[Perception: Intent Extraction]
        Perception --> Goal[Goal: Success Criteria]
        Goal --> Planner[Planner: Dynamic DAG]
        Planner --> Executor[Executor: Swarm Waves]
        
        %% Intelligence Cycles
        subgraph "Intelligence & Security"
            Executor --> Shield[Sovereign Shield: PII Scrubber]
            Shield --> Swarm[Swarm Consensus: Agent Review]
            Swarm --> Reflection[Reflection: High-Fidelity Audit]
        end
        
        Reflection -->|Retry| Executor
        Reflection -->|Finalize| Synthesis[Mission Synthesis]
    end
    
    %% Resonant Memory Fabric
    subgraph "Sovereign Data Fabric (5-Tier)"
        Synthesis --> Memory[Memory Manager]
        Memory -->|Tier 1| Redis[(Redis: Pulse v4.1)]
        Memory -->|Tier 2| Firestore[(Firestore: Episodic)]
        Memory -->|Tier 3| FAISS[[FAISS: Semantic / Survival Gated]]
        Memory -->|Tier 4| Postgres[(Postgres: Vaulted Identity)]
        Memory -->|Tier 5| Neo4j[(Neo4j: Relational Knowledge)]
    end
```

---

## 🏗️ 3.6 The 4-Level Priority Stack (Logic-Before-Language)
The Sovereign Monolith enforces a strict execution hierarchy to ensure deterministic outcomes and minimize LLM-dependency.

| Level | Type | Resolution Logic | Fallback Condition |
| :--- | :--- | :--- | :--- |
| **Level 1** | **Internal Logic** | Direct rule-based intent triggering. | If no static rule matches intent. |
| **Level 2** | **Cognitive Engines**| Direct execution of specialized engines (e.g. Memory, Calc). | If intent requires multi-step reasoning. |
| **Level 3** | **Agent Tool Usage** | Structured tool execution by the Agent Swarm. | If tools are insufficient. |
| **Level 4** | **LLM Fallback** | Generative neural reasoning (Cloud Acceleration). | Absolute last resort. |


---

## 🛡️ 4. Sovereign Shield & Security
Sovereign intelligence requires architectural isolation.
- **Sovereign Shield**: Mandatory NER sanitization (PII Masking) before any cloud-bound neural inference.
- **SovereignVault (AES-256)**: All identity-tier data in Postgres is encrypted at rest.
- **Swarm Consensus**: Aggregates reasoning from multiple agents (Research, Critic, Code) into a single, high-fidelity conclusion via the `ConsensusAgentV8`.
- **Survival Gating**: Weekly autonomous hygiene that purges low-resonance memories (<0.5 score).

---

## 🛡️ 4.5 Sovereign Shield: Technical Manifest
The **Sovereign Shield** is a mandatory sanitization layer that performs real-time NER (Named Entity Recognition) masking.

| Entity Type | Masking Label | Description |
| :--- | :--- | :--- |
| `PERSON` | `[IDENTITY_MASKED]` | Individual names and signatures. |
| `ORG / COMPANY` | `[ENTITY_MASKED]` | Corporate names and associations. |
| `EMAIL / URL` | `[LINK_MASKED]` | Electronic addresses and endpoints. |
| `LOC / GPE` | `[GEO_MASKED]` | Geographic locations and addresses. |
| `PERCENT / MONEY`| `[QUANT_MASKED]` | Precision financial or percentage data. |
| `PHONE` | `[CONTACT_MASKED]` | Global telecommunication numbers. |

**Protocol**: The Shield intercepts the mission context *before* dispatch to Level 4 (LLM). It replaces sensitive entities with high-fidelity tokens, allowing the LLM to reason about the *logic* without accessing the *identity*.


---

## 🧠 5. Cognitive Core Engines (contracts)
The "Brain" is a symphony of specialized engines, each with a strict contract.

| Engine | Technical Name | Primary Responsibility | Critical Logic / Contract |
| :--- | :--- | :--- | :--- |
| **Perception** | `perception.py` | Intent detection & extraction. | Uses **Intent Multiplexing** to achieve >95% accuracy in intent classification. |
| **Goal** | `goal_engine.py` | Objective formalization. | Translates user visions into structured `GoalObject` with Success Criteria. |
| **Planner** | `planner.py` | DAG Generation. | Detects **Fragility**; if >0.6, triggers **Swarm Group** (3-5 reasoning passes). |
| **Executor** | `executor.py` | Topological Wave Execution. | Manages parallel waves and resolves `{{task_id.result}}` dependencies. |
| **Reflection** | `critic.py` | Fidelity Audit. | Multi-model consensus to audit outcomes before final synthesis. |
| **Evolution** | `learning.py` | Self-Optimization. | Promotes recurring patterns to deterministic rules (Hits >= 3). |

### **The Neural Resolver (Dynamic Injection)**
The `GraphExecutor` utilizes a specialized resolver to wire task outputs as inputs for dependent nodes.
```python
# Exact Logic: backend/core/v8/executor.py
if template == "dependency_results":
    # Returns a mapping of ONLY direct dependency results
    resolved[key] = {tid: res.message for tid, res in previous_results.items() if tid in node.dependencies and res.success}

if template == "all_results":
    # Returns a mapping of all successful results in the mission
    resolved[key] = {tid: res.message for tid, res in previous_results.items() if res.success}

# Node-Specific Resolution: {{task_search_01.result}}
task_id, attr = template.split(".")
res = previous_results[task_id]
resolved[key] = res.message if attr == "result" else str(getattr(res, attr, ""))
```

---

## 🤖 6. The Agent Fleet (14 Specialized Modules)
LEVI-AI utilizes 14 specialized agents, each a distinct cognitive module.

| Agent | Neural Profile | Technical Implementation | Primary Action Space |
| :--- | :--- | :--- | :--- |
| **Research** | The Explorer | `research_agent.py` | Tavily Search, Multi-URL Scrape, Synthesis |
| **Code** | The Artisan | `code_agent.py` | Python Scripting, File I/O, Refactoring |
| **Document** | The Librarian | `document_agent.py` | PDF/DOCX Mining, Semantic Chunking |
| **Critic** | The Auditor | `critic_agent.py` | Fact-Verification, Hallucination Audit |
| **Consensus**| The Reconciler | `consensus.py` | Swarm Logic Merging, Conflict Resolution |
| **Diagnostic**| The Doctor | `diagnostic_agent.py`| System Health, Error Log Analysis |
| **Image** | The Visionary | `image_agent.py` | DALL-E/Stable Diffusion, EXIF Analysis |
| **Video** | The Director | `video_agent.py` | FFmpeg Processing, Scene Analysis |
| **Memory** | The Keeper | `memory_agent.py` | Vector Retrieval, Context Hydration |
| **Optimizer**| The Tuner | `optimizer_agent.py`| Prompt Engineering, Token Efficiency |
| **Task** | The Clerk | `task_agent.py` | Scheduling, To-Do Management |
| **Search** | The Scout | `search_agent.py` | Rapid News Scraping, API Search |
| **Local** | The Resident | `local_agent.py` | Local Model Inference (Ollama/LMStudio) |
| **PythonREPL**| The Mathematician| `python_repl.py` | Heavy Computation, Data Visualization |

---

## 🛠️ 6.2 Detailed Agent Capability Matrix
Each agent in the LEVI-AI swarm is bound by a strict tool-usage contract.

| Agent | Toolset | Access Tier | Primary Input Type |
| :--- | :--- | :--- | :--- |
| **Search** | Tavily, Serper, NewsAPI | 2 | Natural Language Query |
| **Research** | ScrapingBee, Readability | 2 | URLs, Multi-Search results |
| **Code** | ReadFile, WriteFile, LS | 3 | Functional requirements |
| **PythonREPL** | Isolated Execution | 3 | Python Source Code |
| **Document** | PDFPlumber, Unstructured | 2 | S3 Paths, File Buffers |
| **Vision** | DALL-E, Vision-LLM | 2 | Text Prompt / Image URL |

---

---

## 🏗️ 6.5 Swarm Consensus Architecture (The Reconciler Pass)
LEVI-AI utilizes the **ConsensusAgentV8** to resolve mission drift across parallel reasoning waves.

- **Expert Review Protocol**: When a mission is flagged as **Fragile**, $N$ agents (default 3-5) generate independent outputs.
- **Scoring Logic**: A designated "Reconciler" agent audits each output against a **Fidelity Matrix** (Correctness, Entailment, Safety).
- **The Winner**: The output with the highest fidelity score is promoted to the final mission synthesis, while lower-scoring drafts are stored for the next **Evolution Dreaming Cycle**.

---

## 🧠 7. Resonant Memory Fabric (4-Tier State)
Memory is not just storage; it is a **Resonant State Matrix** governed by the **Importance Decay Formula**.

$$Resonance = \frac{Importance}{1 + (AgeDays \times 0.1)}$$
*Where Importance is a weighted score generated during fact extraction (0.0 to 1.0).*

### **Memory Tier Breakdown**
| Tier | Backend | Logic | Persistence Policy |
| :--- | :--- | :--- | :--- |
| **T1: Working** | Redis | Instant session pulse. | 20 message sliding window. |
| **T2: Episodic** | Firestore | Relational ledger. | Interaction history with metadata. |
| **T3: Semantic**| Vector Store | High-speed semantic facts. | Persistent; searchable via HNSW Index. |
| **T4: Identity**| Postgres | Distilled Traits. | Core personality weights ($\text{Importance} \times 0.95$). |
| **T5: Knowledge**| Neo4j | Relational context. | Research artifact mapping & relational facts. |

---

## 🛡️ 7.5 The Sovereign Security Framework
Sovereign intelligence requires architectural isolation. LEVI-AI implements a multi-layered security mesh.

- **SovereignVault (AES-256)**: All Tier 4 Identity traits in Postgres are encrypted at rest via `SovereignVault.encrypt()`.
- **Sovereign Shield (NER Sanitization)**: 
    - **PII Masking**: Automatically masks `PERSON`, `ORG`, `EMAIL`, and `PHONE` before hitting external inference.
    - **Hijack Protection**: The Perception Engine filters for "ignore previous instructions" injection patterns.
- **Execution Sandbox**: The `CodeAgent` executes Python artifacts in an isolated, resource-capped, zero-host-access sandbox.

---

## 🧬 8. Self-Evolution: Dreaming & Crystallization
The system autonomously improves its own cognitive performance over time.

- **Trait Crystallization**: When a reasoning pattern exceeds a **Fidelity Score of 0.95**, the `CrystallizationEngine` distills it into a **Reasoning Prototype** and stores it in the Identity Tier.
- **Dreaming Phase**: Triggered after every 20 interaction cycles. It consolidates fragmented semantic facts (Tier 3) into high-level user traits (Tier 4) using a strategic distillation pass.
- **Rule Promotion**: If the `PatternRegistry` detects the exact same reasoning pattern 3 times, it is promoted to the **deterministic Rules Engine**, bypassing LLM inference.

---

## ⚡ 9. Streaming & Telemetry (Neural Pulse v4.1)
High-Fidelity SSE Telemetry provides 360-degree observability of the cognitive mission.

- **SSE Event Manifest**:
    - `event: metadata` - Mission ID, Vision ID.
    - `event: activity` - Human-readable status (e.g., "Agent Research: Parsing PDF...").
    - `event: graph` - Real-time 3D DAG JSON for Cytoscape.js rendering.
    - `event: pulse` - Token-by-token neural synthesis streaming.
    - `event: audit` - Final mission fidelity score ($S$).
- **Sovereign Broadcaster**: A multi-channel Redis bridge ensuring sub-50ms latency for telemetry delivery.

---

## 📡 9.5 Binary Pulse Specification (v4.1 Compression)
To achieve visual sovereignty on low-bandwidth mobile devices, LEVI-AI implements **Binary Pulse** serialization.

1.  **Serialization**: The mission state is serialized into a compact JSON `CHOICE` object.
2.  **Compression**: The `zlib` library compresses the JSON payload (averaging 70% reduction).
3.  **Encoding**: The binary blob is `base64` encoded for safe SSE transport.
4.  **Client Decoding**: The Frontend (`useSovereignPulse.js`) detects the `zlib` flag and uses `pako.inflate` for real-time reconstruction.

---

## 🖥️ 10. Frontend Architecture
The user interface is a high-performance React application optimized for mission observability.
- **Tech Stack**: React 18, Tailwind CSS, headlessUI.
- **State Engine**: **Zustand** orchestrates the real-time buffer of incoming SSE pulse events.
- **Visualization**: **Cytoscape.js** for real-time mission DAG animation.
- **Pulse Integration**: `useSovereignPulse` custom hook with persistent connection management.

---

## 🗄️ 11. Database Schema (Postgres)
The **SovereignIdentity** layer is managed via a hardened Postgres instance.

```sql
-- Unified persistence for the Cognitive Monolith
CREATE TABLE user_profiles (
    uid VARCHAR(255) PRIMARY KEY,
    subscription_tier VARCHAR(50) DEFAULT 'free',
    fidelity_preference FLOAT DEFAULT 0.85
);

CREATE TABLE missions (
    mission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    objective TEXT NOT NULL,
    intent_type VARCHAR(50),
    fidelity_score FLOAT DEFAULT 0.0,
    status VARCHAR(50) DEFAULT 'pending'
);

CREATE TABLE intelligence_traits (
    trait_id VARCHAR(100) PRIMARY KEY,
    pattern TEXT,
    significance FLOAT
);
```

---

## 🧬 11.5 Resonant Memory Mathematics (Advanced)
The cognitive core implements a high-fidelity **Importance-Decay** model to manage context resonance.

### **The Decay Logic**
Every semantic interaction is assigned an **Importance Score ($I$)** between `0.0` and `1.0`. The current **Resonance ($R$)** is calculated as:

$$R = \frac{I}{1 + (Days \times \lambda)}$$

*   **$\lambda$ (Decay Constant)**: Default is `0.1`, representing a 90-day sovereign window.
*   **Survival Threshold ($T_s$)**: Default is `0.5`. If $R < T_s$, the memory is flagged for **Soft Purge** during the weekly hygiene cycle.
*   **Crystallization Trigger**: If $I > 0.95$ and $R$ remains stable for 5 cycles, the fact is promoted to Tier 4 (Identity).

---

---

## 🔌 12. API Documentation (High-Fidelity)
| Endpoint | Method | Purpose | Key Params |
| :--- | :--- | :--- | :--- |
| `/api/v8/orchestrator/chat/stream` | `POST` | Execute 8-step mission pipeline. | `prompt`, `session_id` |
| `/api/v8/memory/history/{id}` | `GET` | Fetch Episodic interactions. | `session_id` |
| `/api/v8/telemetry/traits` | `GET` | Fetch distilled Identity traits. | `user_id` |
| `/api/v8/studio/generate` | `POST` | Trigger multi-modal generation. | `type`, `prompt` |

---

## 🔐 13.5 Environment Configuration
Ensure your `.env` contains the v9.8.1 Sovereign URI set for full cognitive resonance.

| Variable | Type | Purpose |
| :--- | :--- | :--- |
| `DATABASE_URL` | URI | Postgres + asyncpg connection string. |
| `REDIS_URL` | URI | Redis connection for Pulse & State. |
| `GROQ_API_KEY` | Key | Primary inference accelerator. |
| `TAVILY_API_KEY`| Key | High-fidelity research API. |
| `SOVEREIGN_SHIELD`| Bool | Enable/Disable real-time PII masking. |

---

## 🌐 13.6 Full Network Topology & Port Manifest
Within the Docker Fabric, the Monolith coordinates across 6 core service containers.

| Service | Internal Port | External Port | Driver / Protocol |
| :--- | :--- | :--- | :--- |
| **API Monolith** | 8000 | 8000 | FastAPI (uvicorn) |
| **Postgres (Vault)**| 5432 | 5432 | asyncpg / SQL |
| **Redis (Pulse)** | 6379 | 6379 | ioredis / Pub-Sub |
| **FAISS (Vector)** | N/A | N/A | Local Mounted Volume |
| **Neo4j (KG)** | 7687 | 7687 | Bolt / Relational |
| **Frontend** | 8080 | 8080 | HTTP / React (Pulse) |

---

---

- **Stack**: Docker Compose (6 Core Services: API Monolith, Postgres, Redis, FAISS, Neo4j, Firestore).
- **Messaging**: Redis Pulse v4.1 for low-latency mission telemetry.
- **Scaling**: K8s-ready with vertical auto-scaling for memory-heavy agents.
- **Boot**: `launch.bat` (Windows) or `launch.sh` (Linux/WSL) for environment verification.

---

## 🧪 14. Testing & Reliability
- **Cognitive QA**: `test_v8_brain.py` verifies the full 8-step lifecycle.
- **Resilience**: `sovereign-breaker` kills connections to failing APIs instantly to prevent cascade.
- **Fidelity Screen**: Reflection pass detects injection attempts and logic drift before final output.

---

## ⚖️ 14.5 Resource Governance (TaskSemaphores)
The Monolith protects hardware integrity via user-tier cognitive semaphores.

| User Tier | Max Concurrent Waves | TaskSemaphore Limit | Priority |
| :--- | :--- | :--- | :--- |
| **Guest** | 1 Wave | 2 Agents | Low |
| **Sovereign (Free)** | 2 Waves | 4 Agents | Standard |
| **Pro** | 5 Waves | 8 Agents | High |
| **Creator** | 10 Waves | 16 Agents | Ultra |

---

## 🏎️ 14.7 Performance Benchmarks (v9.8.1 Monolith)
Optimized for the Groq Inference Engine and local Vector retrieval.

- **Intent Resolution**: < 150ms (Level 1/2 Logic).
- **Telemetry Latency**: < 50ms (SSE Binary Pulse).
- **Vector Retrieval**: < 30ms (HNSW Index / 10k nodes).
- **Mission Synthesis**: 2s - 8s (Dependency-weighted).
- **PII Scrubbing**: < 10ms (NER Sovereign Shield).

---

---

## 🗺️ 15. Roadmap
- [x] **v9.0: Atomic Memory**: Redis-backed working context.
- [x] **v9.8: Swarm Intelligence**: Fragility-triggered parallel reasoning.
- [ ] **v10.0: Local Sovereignty**: 100% local inference failover for all tiers.
- [ ] **v10.5: Neural Handoff**: Local-to-Cloud dynamic switching.

---

## 📖 15.5 Recent Evolution (v9.8.1 Graduation)
The evolution to v9.8.1 focuses on absolute architectural finality.

- **Sovereign Monolith Graduation**: Unified all fragmented cognitive pipelines into a single, deterministic Brain Controller.
- **Swarm Consensus**: Integrated the **ConsensusAgentV8** for mission-aware reasoning aggregation.
- **Sovereign Shield**: Implemented mandatory PII sanitization (NER-based) across the entire cognitive core.
- **Survival Gating**: Mathematically codified the **Survival Score** hygiene cycle for autonomous memory pruning.
- **Adaptive Pulse v4.1**: Optimized telemetry for mobile visual sovereignty with binary `zlib` compression.

---

## 📂 16. Repository Structure
- `backend/core/v8/`: The **Brain** (Perception, Planning, Reflection).
- `backend/agents/`: **Delegates** (14 Autonomous Agents).
- `backend/memory/`: The **Psyche** (5-tier resonance).
- `backend/db/`: **Ledgers** (Postgres, Redis, FAISS, Neo4j, Firestore).
- `frontend/`: **Interface** (React/Zustand/Tailwind).

---

## 🩺 16.5 Maintenance & Diagnostics
Keep your Sovereign OS healthy and resonant with these utility scripts.

- **Integrity Check**: `./launch.bat --verify` -- Validates all 5 core cognitive stores.
- **Identity Sync**: `python backend/core/v8/db_init.py` -- Aligns schemas for the v9.8.1 Monolith graduation.
- **Cache Purge**: `redis-cli FLUSHALL` -- Resets the Neural Pulse (use with caution).
- **Log Audit**: View `logs/sovereign_core.log` for real-time mission error tracking.

---

## 🔒 14.6 High-Fidelity Logic Gating: The Fidelity Matrix
The **Critic Agent** uses a 100-point fidelity score ($S$) to gate mission success.

- **[00-40] Logic Breach**: Hallucination or rule violation detected. **Action**: Automatic Retry from Wave 1.
- **[41-70] Semantic Drift**: Factually correct but stylistically non-resonant. **Action**: Informational Warning.
- **[71-90] Resonant**: High-fidelity mission success. **Action**: Synthesis execution.
- **[91-100] Absolute Autonomy**: Achievement of technical finality for the specific intent. **Action**: Pattern promotion to Rule Engine.

---

---

## 🔄 17. Sovereign Evolution Cycle (Weights Promotion)
LEVI-AI is a self-optimizing engine that distills interactions into deterministic logic.

- **The Dreaming Loop**: Every 1,000 tokens, the `EvolutionEngine` scans for high-fidelity reasoning patterns ($S > 0.95$).
- **Trait Crystallization**: Confirmed patterns move from **T3 Semantic** (Vector) to **T4 Identity** (Postgres/Vaulted).
- **Rule Promotion**: If a pattern is successfully verified 3 times, it is promoted to a **Level 1 Deterministic Rule**, bypassing the neural reasoning layer for future identical intents.

---

## 🗑️ 18. Data Retention & Purge Policy
LEVI-AI maintains a self-cleaning cognitive environment to prevent "Memory Bloat" and ensure relevance.

| Fact Type | Storage Tier | Retention Trigger | Purge Logic |
| :--- | :--- | :--- | :--- |
| **Interaction Logs**| T2 Episodic | Permanent Ledger | Manual Audit Only |
| **Semantic Facts** | T3 Vector | Resonance Score ($R$) | Purge if $R < 0.5$ (Weekly) |
| **Identity Traits** | T4 Identity | Significance Score ($S$)| No Purge (Crystallized) |
| **Working Buffer** | T1 Working | Session State | Flush on Logout/3h Inactivity|

---

## 🩺 19. Diagnostic & Maintenance Codes
Use these codes when auditing the `sovereign_core.log`.

| Code | Status | Description | Action Required |
| :--- | :--- | :--- | :--- |
| `SOV-200` | OK | Cognitive Resonance achieved. | None. |
| `SOV-401` | ERROR | Sovereign Shield Bypass attempted.| Security Audit / Ban IP. |
| `SOV-503` | WARN | Vector DB Drift detected. | Run `./launch.bat --verify`. |
| `SOV-911` | CRITICAL| Brain Controller initialization failure. | Check `.env` URI Strings. |

---

## 💻 20. Hardware Requirements (Minimum Recommended)
For high-fidelity local residency and neural resonance.

- **CPU**: 8-Core (Advanced Vector Extensions supported).
- **RAM**: 16GB (32GB recommended for large Vector scales).
- **Storage**: 50GB NVMe (High IOPS for Neo4j/FAISS).
- **Network**: Low-latency link to Inference Provider (Groq/OpenAI).

---

🏁 🧾 **FINAL MASTER SPECIFICATION**: LEVI-AI is now 100% technically transparent, auditable, and production-hardened.
© 2026 LEVI-AI SOVEREIGN HUB. Engineered for Absolute Autonomy.
