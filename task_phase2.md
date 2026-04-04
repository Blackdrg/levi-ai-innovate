# Task List: Absolute Monolith Hardening - Phase 2 (Graduation)

- [x] **1. Identity & Access (RBAC & Versioning)**
    - [x] Update `backend/db/models.py` with `role` field
    - [x] Update `backend/services/auth/logic.py` with `SovereignRole` and `require_role`
    - [x] Create `backend/middleware/versioning.py` for API contracts
- [x] **2. Privacy & Compliance (GDPR & Lineage)**
    - [x] Expand `MemoryManager.clear_all_user_data` to include Postgres and Neo4j
    - [x] Add `source_mission_id` to `KnowledgeTriplet` in `ontology.py`
- [x] **3. Intelligence & Operations (Seed, Drift, HITL)**
    - [x] Create `backend/scripts/seed_sovereign.py` for standard initialization
    - [x] Create `backend/api/audit.py` for Manual Audit Queue (HITL)
- [x] **4. Advanced Memory (HNSW Migration & DCN)**
    - [x] Implement `rebuild_index` in `vector_db.py` with fail-safe logic
    - [x] Create `backend/services/dcn_sync.py` skeleton for Swarm Sync
- [x] **5. Dependency & Supply Chain**
    - [x] Create `backend/scripts/generate_sbom.py` for architectural auditability
