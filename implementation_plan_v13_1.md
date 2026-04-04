# Implementation Plan - Phase 4 (v13.1 Stabilization)

This plan addresses the "v13.1 Stabilization" roadmap items identified in the graduation manual. It focuses on backpressure management in the learning loop and the functional implementation of the DCN (Decentralized Cognitive Network) protocol.

## User Review Required

> [!IMPORTANT]
> **Learning Throttling**: I am implementing a concurrency cap on background learning tasks. Under extreme load, some low-importance facts (Resonance < 0.6) may be dropped to preserve system stability.

> [!WARNING]
> **DCN Sync**: The Gossip Protocol will initially be configured for "Local Discoverability". Cross-network sync requires a valid Peer-CA certificate which is out of scope for this monolith.

## Proposed Changes

### 1. Learning Loop Resilience & Throttling
Prevent system-wide crashes during mission spikes by gating background learning tasks.

#### [NEW] [concurrency.py](file:///d:/LEVI-AI/backend/utils/concurrency.py)
- Implement `SovereignThrottler`: A `BoundedSemaphore` based manager for background tasks.
- Implement `CircuitBreaker`: To pause learning if Postgres/Redis latency spikes.

#### [MODIFY] [logic.py](file:///d:/LEVI-AI/backend/services/learning/logic.py)
- Integrate `SovereignThrottler` into `collect_training_sample`. 
- Wrap `_augment_knowledge_base` and `update_memory_graph` in throttled execution.

---

### 2. DCN Gossip Protocol (Swarm Sync)
Transition the DCN from a skeleton to a functional (mock-ready) protocol.

#### [MODIFY] [dcn_sync.py](file:///d:/LEVI-AI/backend/services/dcn_sync.py)
- Implement `CognitiveFragment` Pydantic model with HMAC signatures.
- Implement `GossipEngine`: Uses Redis PubSub `swarm:sync` channel for fragment propagation.
- Add `fragment_scrubber`: Ensures $S < 0.95$ facts are never gossiped (High-fidelity ONLY).

---

### 3. HNSW Metadata Finality
Ensure the vector index remain consistent during re-indexing.

#### [MODIFY] [vector_db.py](file:///d:/LEVI-AI/backend/utils/vector_db.py)
- Update `rebuild_index`: Ensure `tenant_id` is correctly mapped from metadata back into the new index structure for absolute isolation.

## Open Questions

- **Throttler Limit**: What is the recommended concurrent learning task limit for an 8-core host? I propose **10 concurrent tasks** to prevent CPU starvation.

## Verification Plan

### Automated Tests
- `pytest tests/test_stabilization_v13_1.py`:
    - Simulate 100 concurrent learning calls and verify that no more than 10 are active.
    - Verify that DCN fragments are HMAC-signed before "broadcast".

### Manual Verification
- Monitor Redis memory usage during a stress test to ensure no PubSub backlog accumulation.
