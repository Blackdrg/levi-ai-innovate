# LEVI-AI SYSTEM MANIFEST (v14.0.0)
This manifest serves as the authoritative source of truth for all components within the LEVI-AI Sovereign OS.

## 1. Core Services
| Service | Path | Description |
| :--- | :--- | :--- |
| **FastAPI Gateway** | `backend/api/main.py` | Entry point for all external requests, handling routing and security. |
| **Orchestrator** | `backend/core/orchestrator.py` | Manages mission lifecycles and high-level routing. |
| **Goal Engine** | `backend/core/goal_engine.py` | Translates user intent into structured mission objectives. |
| **Planner** | `backend/core/planner.py` | Generates execution DAGs (Task Graphs) based on mission goals. |
| **Executor** | `backend/core/executor/__init__.py` | Executes DAG nodes, handling wave scheduling and agent coordination. |
| **Memory Manager** | `backend/memory/manager.py` | Orchestrates the 4-tier memory system (Short, Mid, Long, Relational). |

## 2. Autonomous Agents (Registry)
| Agent | Role | Specialized Function |
| :--- | :--- | :--- |
| **CodeAgent** | Artisan | High-fidelity code generation and architectural design. |
| **SearchAgent** | Scout | Real-time web discovery and information retrieval. |
| **CriticAgent** | Critic | Qualitative validation and self-correction loops. |
| **PythonReplAgent** | Coder | Secure code execution and iterative debugging in sandboxes. |
| **ResearchAgent** | Researcher | Multi-source synthesis and citation bundle generation. |
| **DocumentAgent** | Analyst | Document parsing, matrix analysis, and knowledge extraction. |
| **TaskAgent** | HardRule | Recursive task decomposition and intent logic enforcement. |
| **ConsensusAgent** | SwarmCtrl | Adjudication across parallel agent outputs for collective resonance. |
| **OptimizerAgent** | Optimizer | Performance tuning and token-efficient reasoning. |
| **MemoryAgent** | Memory | Relational triplet extraction and Neo4j graph population. |
| **DiagnosticAgent** | Diagnostic | System health analysis and troubleshooting. |
| **ImageAgent** | Imaging | Generative visual content creation. |
| **VideoAgent** | Video | Frame-consistent video generation. |
| **RelayAgent** | Relay | Cross-service communication and DCN pulse management. |

## 3. Infrastructure & Persistence
| Component | Implementation | Role |
| :--- | :--- | :--- |
| **Redis** | `backend/db/redis.py` | Source of truth for runtime state, caching, and rate limiting. |
| **PostgreSQL** | `backend/db/postgres.py` | Persistent store for immutable history, user profiles, and audit logs. |
| **Neo4j** | `backend/db/neo4j_client.py` | Graph database for relational memory and entity mapping. |
| **Vector DB** | `backend/db/vector_store.py` | HNSW/FAISS for semantic memory and long-term retrieval. |
| **Docker Sandbox** | `backend/utils/sandbox.py` | Bounded isolation for secure code execution. |
| **Celery** | `backend/celery_app.py` | Distributed task queue for long-running asynchronous jobs. |
| **Kafka** | `backend/utils/kafka.py` | Event streaming for cross-module telemetry and pulse emission. |
| **MongoDB** | `backend/db/mongo.py` | Flexible document store for raw mission data and cache backups. |

## 4. Runtime & Orchestration Systems
| System | Description |
| :--- | :--- |
| **DAG Engine** | `backend/core/task_graph.py` - Manages task dependencies and execution flow. |
| **Wave Scheduler** | `backend/core/executor/__init__.py` - Groups DAG nodes for parallel execution. |
| **Retry Engine** | `backend/core/executor/__init__.py` - Handles node-level failures with backoff logic. |
| **Compensation Engine**| `backend/core/failure_engine.py` - Executes rollback or recovery tasks on failure. |
| **Circuit Breaker** | `backend/circuit_breaker.py` - Prevents cascading failures across services. |
| **State Machine** | `backend/core/execution_state.py` - Central authoritative state tracking for missions. |
| **Consistency Manager**| `backend/memory/consistency.py` - Enforces write ordering and deduplication across stores. |

## 5. Security & Protection
| System | Implementation |
| :--- | :--- |
| **RBAC** | `backend/auth/logic.py` - Role-based access control for API and resources. |
| **KMS Encryption** | `backend/utils/kms.py` - Key management for sensitive data and model keys. |
| **Prompt Shield** | `backend/utils/shield.py` - Prevents prompt injection and jailbreak attempts. |
| **Egress Filter** | `backend/utils/egress.py` - Monitors and restricts external network requests. |

## 6. Inference & Cognitive Layer
| Component | Description |
| :--- | :--- |
| **Ollama Local** | `backend/services/local_llm.py` - Local inference engine for privacy and low-cost tasks. |
| **Model Router** | `backend/core/model_router.py` - Adaptive routing between local and cloud LLMs. |
| **Embedding Pipeline**| `backend/embeddings.py` - Vectorizes data for semantic memory indexing. |

## 7. Observability & Telemetry
| System | Implementation |
| :--- | :--- |
| **Logging** | `backend/utils/logger.py` - Standardized system-wide logging. |
| **Telemetry** | `backend/broadcast_utils.py` - Publishes live system pulses (DCN). |
| **SSE Stream** | `backend/services/chat/router.py` - Real-time event streaming to the frontend. |
| **Tracing** | `backend/evaluation/tracing.py` - Global trace ID tracking across request lifecycles. |
