# 🚀 Production Launch Manifest (v13.1.0-Hardened-PROD)

The complete service set for the graduation to the v13.1.0-Hardened-PROD Local-First Distributed Stack.

---

## 🏗️ 1. Service Fabric

| Service | Image/Engine | Role | Status |
| :--- | :--- | :--- | :--- |
| **Brain API** | `levi-backend:v13.1.0-Hardened-PROD` | **The Controller** (FastAPI, Mission Orchestrator) | Active |
| **Task Worker** | `celery:v13.1.0-Hardened-PROD` | **The Swarm** (Agent Execution, Background Tasks) | Active |
| **Episodic Memory** | `postgres:15-alpine` | **Relational Persistence** (Profiles, Mission Logs) | Active |
| **Working Memory** | `redis:7-alpine` | **Task Queue & Cache** (Mission State, Rate Limiting) | Active |
| **Semantic Memory** | `faiss-service` | **Vector Vault** (Semantic facts, Embeddings) | Active |
| **Knowledge Graph** | `neo4j:5-community` | **Relational Knowledge** (Crystallized artifacts) | Active |
| **Inference Layer** | `ollama:latest` | **Local Neuron** (llama3.1:8b, phi3:mini) | Active |

---

## 🛠️ 2. Core Cognition Components

- **Inference Strategy:** Local-First (Ollama) with Managed Cloud Fallback.
- **Mission Planning:** DAG-based topological wave execution.
- **Fidelity Score (S):** 60/40 Weighted (Neural + Deterministic Validator).
- **Security Middleware:** SHA-256 PII Masking and Instruction Guarding.
- **Vault Service:** Role-Based Access Control (RBAC) and AES-256 encryption.

---

© 2026 LEVI-AI SOVEREIGN HUB.
