# LEVI-AI v4.5 Omnipresent — Master Diagnostic Manual 🛰️🌌

This document is the definitive technical source for **Analyzing, Diagnosing, and Maintaining** the LEVI-AI production stack. It synthesizes the results of 45 phases of architectural hardening into a single maintenance blueprint.

---

## 🏗️ 1. Architectural Anatomy (v4.5)

### 1.1 The Global API Gateway
The entry point ([gateway.py](file:///c:/Users/mehta/Desktop/New%20folder/LEVI-AI/backend/gateway.py)) is no longer a simple proxy; it is a high-concurrency orchestration layer.

```mermaid
graph TD
    Client((Client)) -->|HTTPS| G[Gateway]
    
    subgraph Middleware Chain
        G --> M1[Strip /api/v1 Prefix]
        M1 --> M2[X-Trace-ID Injection]
        M2 --> M3[CORS Strict Enforcement]
        M3 --> M4[Redis-Backed Rate Limiting]
        M4 --> M5[Live Metrics Accumulator]
    end
    
    subgraph Service Mesh (Routers)
        M5 --> R1[Auth: Identity Normalization]
        M5 --> R2[Chat: Council of Models]
        M5 --> R3[Gallery: Like/Feed Aggregate]
        M5 --> R4[Studio: Celery Job Orchestration]
        M5 --> R5[Analytics: Redis Aggregation]
    end
```

### 1.2 The Intelligence Core (Phase 43)
- **Council of Models**: Parallel requests to **Groq (Llama-3.1)** and **Together AI (Mixtral/Gemma)**.
- **The Judge**: A synthesis engine selects the highest-fidelity output for Pro/Creator subscriptions.
- **Resiliency**: Mutual Circuit Breakers ensure that if Groq fails, Together AI automatically scales into primary status.

---

## 📊 2. Operational Diagnostics

### 2.1 Live Performance Management (Phase 45)
- **High-Fidelity Telemetry**: Middleware pushes 100% of request metrics to Redis.
- **Aggregation Logic**: The `/analytics/v2/performance` endpoint calculates:
    - **p95 Latency**: Using `numpy.percentile` on the last 100 Redis list entries.
    - **Total RPS**: Aggregated via incremental Redis counters.
- **Admin Control Plane**: [admin.html](file:///c:/Users/mehta/Desktop/New%20folder/LEVI-AI/frontend/admin.html) features live gauges and manual **Circuit Breaker Trip/Reset** overrides.

### 2.2 Global Heartbeat (Phase 44)
- **SSE Stream Engine**: A persistent Server-Sent Events (SSE) broadcaster handles real-time pulses.
- **Cosmic Ticker**: The homepage [index.js](file:///c:/Users/mehta/Desktop/New%20folder/LEVI-AI/frontend/js/index.js) connects to `/api/v1/activity/stream` to visualize global community interactions.

---

## 🛠️ 3. Maintenance & Troubleshooting

### 3.1 Cloud Run Startup Failures (v4.5.2 Hostfix)
If the container fails with a "failed to listen on port 8080" error:
- **Root Cause**: Python namespace flattening or hardcoded port binding.
- **Fix**: The [Dockerfile.prod](file:///c:/Users/mehta/Desktop/New%20folder/LEVI-AI/backend/Dockerfile.prod) must use `COPY backend/ backend/` and a shell-form `CMD` to interpolate the `$PORT` environment variable.

### 3.2 Identity & Auth Synchronization
- **Standardization**: All frontend calls must use the unified `apiFetch` in [api.js](file:///c:/Users/mehta/Desktop/New%20folder/LEVI-AI/frontend/js/api.js).
- **Security Check**: Verify the `X-Firebase-AppCheck` and `X-Trace-ID` headers are propagated for every production request.

### 3.3 Database & Storage Diagnostics
- **Firestore-Native**: Check the `health_check` collection for a heartbeat.
- **S3 Security**: Pre-signed URLs expire after 1 hour (controlled by `backend/s3_utils.py`).

---

## 🚀 4. Final Deployment Blueprint

### 4.1 CI/CD Workflow ([deploy-backend.yml](file:///c:/Users/mehta/Desktop/New%20folder/LEVI-AI/.github/workflows/deploy-backend.yml))
1.  **Build**: Docker builds the environment using `Dockerfile.prod`.
2.  **Push**: Image is pushed to Google Artifact Registry.
3.  **Deploy**: Revision is created on Cloud Run (0% traffic, --tag canary).
4.  **Verify**: Post-deploy health check probes the `/health` endpoint.
5.  **Swap**: Traffic is swapped to 100% once verified.

---
> [!IMPORTANT]
> **LEVI-AI is officially architected for global scale and surgical observability.** 📡🛡️🌌
