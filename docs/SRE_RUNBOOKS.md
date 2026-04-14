# 🛡️ LEVI-AI SRE Runbooks v16.0-GA
> **Sovereign Monitoring & Incident Response Protocols**

This document outlines the standard operating procedures for maintaining the **LEVI-AI Sovereign Operating System** in production.

---

## 🚨 P0: Critical System Total Blackout
**Symptoms:** 503 errors on `/healthz`, gateway timeout, metrics flatline.
**Threshold:** > 5% failure rate for more than 2 minutes.

### 🛠️ Immediate Response
1.  **Check Redis Connectivity:**
    ```powershell
    # Verify Redis pod/service liveness
    redis-cli -h $REDIS_HOST ping
    ```
    *   If offline: Restart Redis Cluster.
2.  **Verify Postgres HA Pool:**
    *   Check `/readyz` for pool exhaustion.
    *   If exhausted: Increase `pool_size` in `backend/db/postgres.py` or restart the app service to clear leaked connections.
3.  **DCN Leader Re-election:**
    *   If no leader is detected (check logs for `[DCN] No Coordinator Found`), force an election pulse:
    ```powershell
    python scripts/force_election.py
    ```

---

## 🧠 P1: Cognitive Drift / Fidelity Drop
**Symptoms:** `fidelity_prediction` consistently < 0.3, Memory Consensus lag > 5 mins.

### 🛠️ Response
1.  **MCM Reconciliation:**
    ```powershell
    # Manually trigger a consistency pulse
    python backend/scripts/disaster_recovery.py --audit
    ```
2.  **Clear Corrupt Context:**
    *   If a specific user session is "stuck" (hallucinating), clear the Redis Tier-1 buffer:
    ```bash
    redis-cli del "sess_v8_<user_id>"
    ```

---

## ⛓️ P2: DCN Network Partition
**Symptoms:** Secondary regions reporting "Standalone" mode, Gossip traffic drop.

### 🛠️ Response
1.  **Check BFT Signing:** Ensure `DCN_SECRET` is synchronized across all regions.
2.  **Verify gRPC MTU:** If using cross-cloud (GKE/EKS), ensure the MTU supports 1500+ bytes for large mission traces.

---

## 🧹 Maintenance: Automated Hygiene
The following jobs run automatically via `backend/main.py`:
-   **Every 30s:** DCN Heartbeat.
-   **Every 60s:** Memory Reconciliation (MCM).
-   **Every 1h:** Memory Re-indexing / Dreaming Cycle.
-   **Every 2h:** Evolution Shadow Audit.
-   **Every 6h:** System Optimization Gradient Pass.

---

## 📈 Observability Dashboard
Access the **Revolution Engine** UI at `/ui/observability.html` for real-time VRAM, latency, and DCN health metrics.
