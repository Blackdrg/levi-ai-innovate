# Task List - LEVI-AI v13 Graduation (10 Steps)

- [x] **Step 1: Wire Ollama into all Agents**
    - [x] Update `backend/utils/llm_utils.py` for Ollama-only inference
    - [x] Update `backend/engines/chat/generation.py` for local routing
- [x] **Step 2: Fix Postgres Migrations**
    - [x] Add `user_facts` to `backend/migrations/v13_migration.sql`
    - [x] Ensure `start.bat` applies SQL
- [x] **Step 3: Connect Neo4j (Bolt Driver)**
    - [x] Implement `Neo4jStore` with Bolt connection
- [x] **Step 4: Fix Learning Loop**
    - [x] Implement/Update `BrainCoreController` refine logic
- [x] **Step 5: Build FastAPI Auth**
    - [x] Create `app/routes/auth.py` (/register, /login)
    - [x] Mount Auth router in `backend/api/main.py`
- [x] **Step 6: Connect SSE Streaming End-to-End**
    - [x] Finalize `app/routes/chat.py` stream logic
    - [x] Verify Nginx Proxy Buffering
- [x] **Step 7: Build the Frontend (React + Zustand)**
    - [x] Finalize `levi-frontend` components
- [x] **x] Step 8: Wire all 5 Memory Tiers**
    - [x] Finalize `app/memory/manager.py` (Redis, PG, HNSW, JSONL, Neo4j)
- [x] **Step 9: Test Full Mission Flow**
    - [x] Run end-to-end cognitive mission test
- [x] **Step 10: Docker Compose everything and run start.sh**
    - [x] Finalize `docker-compose.yml` and `start.sh`

## ✅ ALL STEPS GRADUATED (Pulse v13.0.0 Global)
