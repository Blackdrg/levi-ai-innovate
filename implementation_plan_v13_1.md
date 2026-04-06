# Implementation Plan - v1.0.0-RC1 Production Residency

This plan addresses the final stabilization items for the LEVI-AI Distributed Stack. It focuses on concurrency management in the background task loop and the secure implementation of the DCN (Distributed Cognitive Network) pulse protocol.

## User Review Required

> [!IMPORTANT]
> **Task Throttling**: I am implementing a concurrency cap on background tasks. Under extreme load, some low-importance operations may be deferred to preserve system stability.

> [!WARNING]
> **DCN Pulse Signing**: Inter-node telemetry requires a valid 32-byte `DCN_SECRET`. Without this, inter-instance sync will be rejected to prevent pulse injection attacks.

## Proposed Changes

### 1. Task Loop Resilience & Throttling
Prevent system-wide crashes during mission spikes by gating background operations.

#### [NEW] [concurrency.py](file:///d:/LEVI-AI/backend/utils/concurrency.py)
- Implement `AdaptiveThrottler`: A `BoundedSemaphore` based manager for background workers.
- Implement `CircuitBreaker`: To pause tasks if Postgres/Redis latency spikes occur.

#### [MODIFY] [logic.py](file:///d:/LEVI-AI/backend/services/learning/logic.py)
- Integrate `AdaptiveThrottler` into memory crystallization loops.
- Wrap graph updates and trait distillation in throttled execution blocks.

---

### 2. DCN Pulse Protocol (Secure Sync)
Transition the DCN from a skeleton to a functional, HMAC-signed protocol.

#### [MODIFY] [dcn_sync.py](file:///d:/LEVI-AI/backend/services/dcn_sync.py)
- Implement `CognitiveFragment` Pydantic model with HMAC-SHA256 signatures.
- Implement `GossipEngine`: Uses Redis PubSub for secure fragment propagation across the network.
- Add `fragment_scrubber`: Ensures only high-fidelity ($S > 0.95$) verified facts are synchronized.

---

### 3. FAISS Metadata Finality
Ensure vector index consistency during re-indexing operations.

#### [MODIFY] [vector_db.py](file:///d:/LEVI-AI/backend/utils/vector_db.py)
- Update `rebuild_index`: Ensure `tenant_id` and stack versioning are preserved in FAISS metadata for absolute isolation.

## Open Questions

- **Throttler Limit**: Based on system benchmarks, I propose a limit of **15 concurrent tasks** to prevent CPU starvation on standard production nodes.

## Verification Plan

### Automated Tests
- `pytest tests/v1_graduation_suite.py`:
    - Verify that DCN fragments are HMAC-signed before broadcast.
    - Verify that no more than 15 background tasks can execute concurrently.

### Manual Verification
- Monitor Redis memory usage during a stress test to ensure no PubSub backlog accumulation.
