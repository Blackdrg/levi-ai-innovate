# EXTERNAL PENETRATION TEST SCOPE: LEVI-AI

**Status**: COMMISSIONED (In parallel with Phase 2)
**Target Turnaround**: 2–3 weeks
**Certification Requirement**: CREST or OSCP-certified firm

## Scope of Work

### 1. API Gateway & Infrastructure
- **OWASP Top 10**: Comprehensive testing of the primary API gateway.
- **JWT Forgery**: Validation of JWT implementation, including RS256/HS256 transitions, key leakage, and token theft.
- **Docker Attack Surface**: Probing for Docker socket exposure, container breakout, and insecure volume mounts on the Absolute Monolith.
- **EgressProxy**: Testing for SSRF via allowlist bypass (e.g., DNS rebinding, URL encoding).

### 2. Agent Ecosystem & LLM Injection
- **14 Agent Endpoints**: Focused prompt injection testing via all 14 specialized agent endpoints.
- **Prompt Injection Defense**: Testing the efficacy of the NER-boundary and deterministic shield layers.
- **System Prompt Extraction**: Targeted attempts to retrieve hidden system instructions from the core orchestrator.

### 3. Data & Persistence Layers
- **Neo4j Cypher Injection**: Testing for injection via LLM-extracted triplets into the memory graph.
- **Redis RESP Injection**: Probing the task queue and caching layer for command injection via user-controlled input.
- **Postgres SQL Injection**: Validation of parameterized query implementation and audit log integrity.
- **GDPR Deletion Protocol**: Testing for data leakage of "erased" FAISS vectors.

## Budget & Remediation
- **Remediation Buffer**: 1 week allocated in Phase 4 Graduation.
- **Integrity**: Any critical (CVSS 9.0+) findings will trigger an immediate architectural freeze.
