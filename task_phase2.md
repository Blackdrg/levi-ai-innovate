# Task List: Local-First Distributed Stack Graduation

- [x] **1. Identity & Access (RBAC & Versioning)**
    - [x] Update `backend/models/user.py` with `role` field (GUEST, PRO, CREATOR)
    - [x] Implement `@require_role` decorator inauth/logic.py`
    - [x] Create `backend/middleware/versioning.py` for X-Sovereign-Version headers
- [x] **2. Privacy & Compliance (GDPR & Lineage)**
    - [x] Expand `MemoryManager.clear_all_user_data` to perform 5-tier wipe
    - [x] Add `mission_id` lineage to `KnowledgeTriplet` in `ontology.py`
- [x] **3. Intelligence & Operations (Seed, Drift, HITL)**
    - [x] Create `backend/scripts/seed.py` for production initialization
    - [x] Create `backend/api/audit.py` for Human-in-the-Loop review queue
- [x] **4. Advanced Memory (FAISS Migration & DCN)**
    - [x] Implement `rebuild_index` in `vector_db.py` with dimension fail-safe
    - [x] Create `backend/services/dcn_sync.py` for HMAC-signed pulse gossiping
- [x] **5. Dependency & Supply Chain**
    - [x] Create `backend/scripts/generate_sbom.py` for technical auditability
