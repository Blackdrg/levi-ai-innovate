# ⚖️ Core Architecture Specification (v1.0.0-RC1)

Technical specifications for the LEVI-AI v1.0.0-RC1 Local-First Distributed Stack.

---

## 🏗️ 1. Core Service Architecture

LEVI-AI is orchestrated by a central **Brain Controller** that manages a distributed service fabric.
- **The Philosophy:** **Logic-Before-Language**. LLMs are treated as a Last Resort Fallback (Level 4).
- **The Stack:** 4-Level Deterministic Priority Stack (Logic -> Engine -> Tool -> LLM).
- **The Swarm:** 14 specialized agents commissioned into parallel "Waves" via a topological `GraphExecutor`.
- **The Quad-Persistence:** High-performance service fabric: **Postgres (Episodic), Redis (Working), FAISS/FAISS (Semantic), and Neo4j (Knowledge Graph)**.

---

## 🔄 2. The Deterministic Priority Pipeline

Every mission follows a strict **4-Level Priority Stack**:
1.  **LEVEL 1: Internal Logic**: Rule-based intent detection and local memory retrieval.
2.  **LEVEL 2: Deterministic Engines**: Direct execution via specialized rule-based engines (e.g., calculation, regex).
3.  **LEVEL 3: Agent Tool Usage**: Structured tool executions by the agent swarm within Docker sandboxes.
4.  **LEVEL 4: Local LLM Fallback**: Generative reasoning via local-first Ollama (only when Levels 1-3 are insufficient).

---

## 🧬 3. Memory Evolution & Pruning

The system implements automated long-term memory management via:
- **Crystallization Phase:** Periodic distillation of episodic mission logs into permanent relational knowledge triplets.
- **Memory Pruning:** Importance-based archival and decay logic (Importance vs TTL) to manage local storage footprint.

---

## 🏁 🛡️ 🚀 GRADUATION COMPLETE.
© 2026 LEVI-AI SOVEREIGN HUB.
