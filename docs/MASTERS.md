# LEVI-AI v7: The Sovereign Mind OS

Welcome to the **Sovereign Mind**, a modular, high-fidelity AI operating system designed for autonomy, privacy, and parallelized intelligence.

## 🏛️ Project Architecture
LEVI-AI is built on a layered, engine-driven architecture:

*   **`frontend/`**: Modern React/Vite interface with real-time streaming and specialized agent tracking.
*   **`backend/core/`**: The Intelligence Core (Brain, Planner, Executor).
*   **`backend/engines/`**: Independent AI specialists (Chat, Memory, Document, Search).
*   **`backend/api/`**: High-performance FastAPI gateway.
*   **`backend/services/`**: Supporting business logic (Payments, Media, Email).

## 🚀 Quick Start
To migrate your existing repository to the Sovereign structure:
1. Run the migration script: `powershell ./MIGRATE_SOVEREIGN.ps1`
2. Install dependencies: `pip install -r backend/requirements.txt`
3. Launch the OS: `python backend/api/main.py`

---

# ARCHITECTURE.md: Sovereign OS Deep-Dive

### 1. The Pulse Protocol (Data Flow)
**User → Frontend → API → Brain → Specialist → Response**

The **Sovereign Brain** analyzes user intent and complexity. It then generates a "Pulse Plan"—a series of independent agent tasks. These tasks are executed in **Parallel Pulses** to minimize latency and maximize reasoning depth.

### 2. The Specialist Engines
*   **Chat Heart**: Handles evocative, philosophical generation.
*   **Memory Vault**: Manages encrypted traits and semantic history.
*   **Document Matrix**: Performs high-fidelity RAG via FAISS.
*   **Search Pulse**: Executes recursive deep research across the global web.

---

# CONTRIBUTING.md: Building for the Sovereign Mind

We welcome contributions that expand the "AI OS" ecosystem.

### Standards
- **Backend**: Use `snake_case`. Document every module with a clear docstring.
- **Frontend**: Use `camelCase`. Prefer domain-driven component organization.
- **Engines**: New engines must inherit from a common `BaseEngine` (to be implemented in v7.1).

### The Sovereign Guard
Never commit PII, secret keys, or unencrypted user data. Always test via `verify_production.py` before proposing a PR.
