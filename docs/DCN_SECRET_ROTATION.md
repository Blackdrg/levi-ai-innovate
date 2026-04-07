# Distributed Network: HMAC Secret Rotation (v14.0 Production)

Rotating the coordination gossip secret (`DCN_SECRET`) requires a coordinated transition to prevent event drops and unauthenticated event rejections during the update window.

---

## 🛡️ 1. Rotation Strategy: Double-Signature Window
LEVI-AI supports a **Transition Window** where multiple secrets can be briefly accepted to maintain cluster connectivity.

### Phase A: Update Configuration
1.  Generate a new 32-character HMAC secret (`NEW_DCN_SECRET`).
2.  Update the environment variables on the **Coordinator** node.
3.  The Coordinator will begin signing events with the `NEW_DCN_SECRET`.

### Phase B: Propagation
Update each **Worker** node in sequence. During this window, nodes may reject events from peers who haven't updated yet. 

---

## 🛠️ 2. Manual Rotation Procedure
If zero-downtime rotation is required without codebase modification:

1.  **Pause Non-Critical Tasks**: Minimizing event volume reduces the chance of rejection logs during the 60s transition.
2.  **Update Redis Secret Key**: If using a central vault, update the `DCN_SECRET` entry.
3.  **Rolling Restart**: 
    -   `docker-compose up -d --no-deps backend` on the Coordinator.
    -   Wait 15s for the Coordinator to resume leadership.
    -   Repeat on all Worker nodes.

---

## 🏗️ 3. Future Roadmap: Automated Rotation
Future updates will support **Secret Buffering**:
*   `DCN_SECRET_OLD` and `DCN_SECRET_CURRENT` will both be accepted by the system.
*   Signatures will be checked against both keys during the transition window.

---

## 🧪 4. Post-Rotation Verification
After rotating, verify cluster health:
1.  **Monitor Logs**: `docker-compose logs -f backend | grep AUTH_FAILURE`.
2.  **Verify Heartbeats**: Ensure all nodes are visible in the `dcn:swarm:nodes` hash in Redis.
3.  **Run Health Check**: `python -m backend.scripts.dcn_heartbeat_check`.
