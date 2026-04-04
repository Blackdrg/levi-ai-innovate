# Implementation Plan - LEVI-AI v13 Frontend & Backend Synchronized Upgrade

The objective is to overhaul the LEVI-AI frontend using React + Vite and synchronize the backend with an SSE-powered (Server-Sent Events) mission architecture. This provides a real-time, premium dashboard experience for autonomous mission execution.

## Proposed Changes

### [Frontend] `levi-frontend`

#### [NEW] [levi-frontend/](file:///d:/LEVI-AI/levi-frontend)
- Initialize with Vite + React.
- Install: `zustand`, `axios`, `react-router-dom`, `@tanstack/react-query`, `tailwindcss`.
- **API Client**: `src/api/client.js` with JWT interceptors.
- **Stores**: `src/stores/authStore.js` (persisted) and `src/stores/missionStore.js`.
- **Hooks**: `src/hooks/useSSEMission.js` for real-time mission updates.
- **Dashboard**: `src/pages/Dashboard.jsx` featuring dynamic `MissionPanel` and `StreamEventLog`.
- **Premium UI**: Modern dark theme with Tailwind, glassmorphism, and smooth transitions.

---

### [Backend] Cognition & Streaming

#### [NEW] [app/routes/chat.py](file:///d:/LEVI-AI/app/routes/chat.py)
- Implementation of `/api/v13/chat/stream` SSE endpoint.
- Handles real-time event generation from the Brain Controller.

#### [NEW] [app/brain/controller.py](file:///d:/LEVI-AI/app/brain/controller.py)
- Unified orchestrator for Perception, Planning, Execution, and Audit.
- Yields granular events for the frontend stream.

#### [NEW] [app/memory/manager.py](file:///d:/LEVI-AI/app/memory/manager.py)
- Integration of 5-tier memory (Redis, Postgres, HNSW, Neo4j).

#### [NEW] [app/auth.py](file:///d:/LEVI-AI/app/auth.py)
- JWT verification logic supporting SSE query parameter authentication.

---

### [Infrastructure] Deployment & Environment

#### [MODIFY] [docker-compose.yml](file:///d:/LEVI-AI/docker-compose.yml)
- Update Nginx to serve the new `levi-frontend/dist` build.
- Ensure all environment variables match the plan.

#### [NEW] [build-and-run.sh](file:///d:/LEVI-AI/build-and-run.sh)
- Automated script to build the frontend and launch the stack.

## Open Questions

1. **Backend Path**: Do you want me to keep the `app/` folder structure exactly as provided, or should I integrate these into the existing `backend/api/`, `backend/core/` folders? The provided snippets use `from app....` imports.
2. **Existing Data**: The v13 migration mentions `knowledge_seeds`. Should I assume the databases are already initialized or include a migration step in the `build-and-run.sh`?

## Verification Plan

### Automated Tests
- `npm run build` in `levi-frontend` to verify React/Vite builds.
- Python import checks for the new `app` module.

### Manual Verification
- Launch the stack using `./build-and-run.sh`.
- Navigate to `https://localhost` (via Nginx).
- Test Login -> Submit Mission -> Observe real-time SSE stream.
