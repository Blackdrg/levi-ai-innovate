# Sovereign DCN: Network Peering Specifications (v13.1.0)

This document defines the connectivity and security requirements for a multi-node Distributed Cognitive Network (DCN). Adherence to these specifications is mandatory for Sovereign Graduation certification.

## 🌐 1. Topology & Subnet Isolation
Nodes must reside within a **Private Layer-2 Subnet** with no direct ingress from the public internet. 

*   **Ingress Control**: Only the `coordinator` node should expose port `8000` (FastAPI) to the external load balancer.
*   **Inter-node Visibility**: All nodes must have mutual visibility on the following ports.

---

## 🔌 2. Port Requirements

| Port | Service | Protocol | Requirement |
| :--- | :--- | :--- | :--- |
| **6379** | Redis (Sovereign Pulse) | TCP / **TLS REQUIRED** | Mutual access for all nodes in the swarm. |
| **7687** | Neo4j (Cognitive Graph) | Bolt / **TLS REQUIRED** | Intra-cluster sync for graph consistency. |
| **8000** | FastAPI (Inter-node API) | HTTP/S | Used for direct task stealing and artifact fetching. |
| **11434** | Ollama (Inference) | HTTP | **Localhost only.** External access is strictly prohibited. |

---

## 🛡️ 3. Security Hardening
### TLS Encryption
As of v13.1.0-Hardened, all inter-node Redis and Neo4j communication **MUST** use TLS (`rediss://`).
1.  Generate node-specific certificates.
2.  Enable `ssl_cert_reqs=None` or provide CA certificates in `DCNGossip.__init__`.

### HMAC Signatures
All cognitive pulses on the Redis stream are signed with **HMAC-SHA256**.
-   The `DCN_SECRET` must be at least 32 characters.
-   Nodes with invalid or missing signatures are automatically dropped by the [Secure Listener](file:///d:/LEVI-AI/backend/core/dcn_protocol.py).

---

## 🛠️ 4. Peering Checklist
1.  [ ] **Node ID**: Assign unique `DCN_NODE_ID` (e.g., `node-alpha`, `node-beta`).
2.  [ ] **Shared Secret**: Sync `DCN_SECRET` across all nodes.
3.  [ ] **Redis URL**: Set `REDIS_URL` to the centralized, TLS-enabled Redis instance.
4.  [ ] **Connectivity**: Verify `ping <redis_host>` and `telnet <redis_host> 6379`.
5.  [ ] **Role Assignment**: Designate one node with `NODE_ROLE=coordinator` for preferred leadership.
