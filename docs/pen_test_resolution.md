# Internal Penetration Testing & Resolution Tracker

This document records the closed loop of formal pen-test cycles. It ensures that previously identified security gaps trace back to an explicit resolution and are actively suppressed from regression.

## P0 / P1 Findings Tracker

### Finding 1: SSRF via EgressProxy (DNS Rebinding)
**Severity:** P0  
**Status:** **RESOLVED** (v14.1 Graduation)  
**Description:** Mission orchestrator resolved domains only at request time, allowing for DNS-rebinding attacks that could bypass IP block-lists once the TTL expired.  
**Resolution:**
- Implemented **Pre-Request DNS Resolution** in `EgressProxy`.
- Hard-validated resolved IPs against forbidden subnets (Local, Private, Cloud Metadata) **before** emission.
- Deny-by-Default allowlist enforcement.

### Finding 2: JWT Symmetric Secret Forgery (HS256)
**Severity:** P0  
**Status:** **RESOLVED** (v14.1 Graduation)  
**Description:** Shared secrets for HS256 tokens were vulnerable to leakage at edge nodes, allowing for total identity forgery if the single key was compromised.  
**Resolution:**
- Migrated to **RS256 Asymmetric JWT** signatures.
- Private keys are restricted to the central `auth-service`.
- Edge nodes leverage public-key only verification.

### Finding 3: Neo4j Cypher Injection
**Severity:** P1  
**Status:** **RESOLVED** (v14.1 Graduation)  
**Description:** LLM-generated graph queries could be manipulated to execute administrative commands (e.g., `DETACH DELETE`) via malicious prompt injection.  
**Resolution:**
- Integrated **CypherProtector** middleware.
- Mandatory keyword blocking and interpolation sanitization on all graph queries.

### Finding 4: Data Residue after GDPR Deletion
**Severity:** P1  
**Status:** **RESOLVED** (v14.1 Graduation)  
**Description:** Soft-deletion of user records left vector embeddings in the FAISS index, allowing for semantic reconstruction of "deleted" data.  
**Resolution:**
- Implemented **Hard-Delete** (GDPR Art 17) logic.
- Atomic SQL scrub combined with a mandatory FAISS index rebuild (Filtering: `deleted=False`).

## Current Audit State: GRADUATED - AUDIT STABLE

All identified P0/P1 gaps from the initial discovery and v14.1 hardening phase have been remediated, verified by integration tests, and structurally mitigated. No unresolved high-severity vulnerabilities remain in the graduation pipeline.
